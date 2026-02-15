from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from oci.exceptions import ServiceError

from .analyzers import FootprintAnalyzer
from .clients import create_clients, create_oci_config
from .collectors import IdentityCollector, PlacementCollector
from .config import AppConfig
from .helpers import ObjectStorageUploader, write_json_report, write_markdown_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate OCI Availability Domain footprint report.")
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Generate local reports only, do not upload to Object Storage.",
    )
    return parser.parse_args()


def discover_candidate_buckets(
    object_storage_client: Any,
    namespace: str,
    compartment_ids: list[str],
) -> list[str]:
    seen: set[str] = set()
    buckets: list[str] = []

    for compartment_id in compartment_ids:
        try:
            response = object_storage_client.list_buckets(
                namespace_name=namespace,
                compartment_id=compartment_id,
            )
        except ServiceError:
            continue

        for bucket in response.data:
            name = getattr(bucket, "name", None)
            if not name or name in seen:
                continue
            seen.add(name)
            buckets.append(name)

    return sorted(buckets)


def main() -> int:
    args = parse_args()

    try:
        app_config = AppConfig.from_env()
        oci_config = create_oci_config(app_config)
        clients = create_clients(oci_config)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Initialization failed: {exc}")
        return 1

    identity_collector = IdentityCollector(clients["identity"])
    placement_collector = PlacementCollector(clients["compute"], clients["network"])

    tenancy_ocid = oci_config["tenancy"]
    region = oci_config["region"]

    try:
        compartments = identity_collector.list_compartments(
            tenancy_ocid=tenancy_ocid,
            root_compartment_ocid=app_config.root_compartment_ocid,
            include_subcompartments=app_config.include_subcompartments,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to list compartments: {exc}")
        return 1

    print(f"[INFO] Discovered {len(compartments)} accessible compartments.")

    scanned_compartments: list[dict[str, Any]] = []
    skipped_compartments: list[dict[str, str]] = []

    for index, compartment in enumerate(compartments, start=1):
        print(f"[INFO] [{index}/{len(compartments)}] Collecting compartment: {compartment.name}")
        try:
            data = placement_collector.collect_compartment_data(compartment.id)
            scanned_compartments.append(
                {
                    "compartment": compartment,
                    "data": data,
                }
            )
        except Exception as exc:  # noqa: BLE001
            skipped_compartments.append(
                {
                    "compartment_id": compartment.id,
                    "reason": str(exc),
                }
            )
            print(f"[WARN] Skipping compartment {compartment.name}: {exc}")

    analyzer = FootprintAnalyzer()
    generated_at = datetime.now(timezone.utc)

    report = analyzer.analyze(
        generated_at=generated_at,
        region=region,
        tenancy_ocid=tenancy_ocid,
        scanned_compartments=scanned_compartments,
        skipped_compartments=skipped_compartments,
    )

    timestamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(app_config.output_dir)
    json_path = output_dir / f"ad_footprint_report_{timestamp}.json"
    markdown_path = output_dir / f"ad_footprint_report_{timestamp}.md"

    write_json_report(report, json_path)
    write_markdown_report(report, markdown_path)

    print(f"[INFO] JSON report written: {json_path}")
    print(f"[INFO] Markdown report written: {markdown_path}")

    if args.skip_upload:
        print("[INFO] Upload skipped (--skip-upload).")
        return 0

    try:
        namespace = app_config.object_storage_namespace or clients["object_storage"].get_namespace().data
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to resolve Object Storage namespace: {exc}")
        return 2 if app_config.fail_on_upload_error else 0

    bucket_candidates: list[str] = []
    if app_config.object_storage_bucket:
        bucket_candidates.append(app_config.object_storage_bucket)

    if app_config.auto_discover_bucket:
        discovered = discover_candidate_buckets(
            object_storage_client=clients["object_storage"],
            namespace=namespace,
            compartment_ids=[item.id for item in compartments],
        )
        for bucket in discovered:
            if bucket not in bucket_candidates:
                bucket_candidates.append(bucket)

    if not bucket_candidates:
        print("[ERROR] No accessible Object Storage bucket found.")
        return 2 if app_config.fail_on_upload_error else 0

    upload_success = False
    last_error: str | None = None

    for bucket in bucket_candidates:
        uploader = ObjectStorageUploader(
            object_storage_client=clients["object_storage"],
            namespace=namespace,
            bucket=bucket,
            prefix=app_config.object_storage_prefix,
        )

        print(f"[INFO] Attempting upload using bucket: {bucket}")

        try:
            json_result = uploader.upload_file(json_path, "application/json")
            md_result = uploader.upload_file(markdown_path, "text/markdown")
            print(f"[INFO] Uploaded: {json_result.uri}")
            print(f"[INFO] Uploaded: {md_result.uri}")
            upload_success = True
            break
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            print(f"[WARN] Upload failed in bucket {bucket}: {exc}")

    if not upload_success:
        print("[ERROR] Upload failed for all bucket candidates.")
        if last_error:
            print(f"[ERROR] Last upload error: {last_error}")
        if app_config.fail_on_upload_error:
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
