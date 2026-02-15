from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def write_markdown_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_to_markdown(report), encoding="utf-8")


def _to_markdown(report: dict[str, Any]) -> str:
    metadata = report["metadata"]
    summary = report["summary"]
    compartments = report["compartments"]
    subnets = report["subnet_footprint"]
    skew = summary["placement_skew"]

    lines: list[str] = []
    lines.append("# OCI Availability Domain Footprint Report")
    lines.append("")
    lines.append(f"- Generated (UTC): `{metadata['generated_at_utc']}`")
    lines.append(f"- Region: `{metadata['region']}`")
    lines.append(f"- Tenancy: `{metadata['tenancy_ocid']}`")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Scanned Compartments | {summary['scanned_compartment_count']} |")
    lines.append(f"| Skipped Compartments | {summary['skipped_compartment_count']} |")
    lines.append(f"| Total Instances | {summary['total_instances']} |")
    lines.append(f"| Total VNICs | {summary['total_vnics']} |")
    lines.append(f"| Total Public IPs | {summary['total_public_ips']} |")
    lines.append("")

    lines.append("## AD Instance Distribution")
    lines.append("")
    lines.append("| Availability Domain | Instance Count | Private IP Count | Public IP Count |")
    lines.append("|---|---:|---:|---:|")

    ad_keys = sorted(set(summary["ad_instance_distribution"].keys()) | set(summary["ad_private_ip_distribution"].keys()) | set(summary["ad_public_ip_distribution"].keys()))
    for ad in ad_keys:
        lines.append(
            f"| {ad} | {summary['ad_instance_distribution'].get(ad, 0)} | "
            f"{summary['ad_private_ip_distribution'].get(ad, 0)} | {summary['ad_public_ip_distribution'].get(ad, 0)} |"
        )
    if not ad_keys:
        lines.append("| - | 0 | 0 | 0 |")

    lines.append("")
    lines.append("## Placement Skew")
    lines.append("")
    lines.append(f"- Status: `{skew['status']}`")
    lines.append(f"- Max AD: `{skew['max_ad']}`")
    lines.append(f"- Max AD Ratio: `{skew['max_ad_ratio']}%`")
    lines.append(f"- Recommendation: {skew['recommendation']}")

    lines.append("")
    lines.append("## Compartment Footprint")
    lines.append("")
    lines.append("| Compartment | Instances | VNICs | Public IPs |")
    lines.append("|---|---:|---:|---:|")
    for item in compartments:
        lines.append(
            f"| {item['compartment_name']} | {item['instance_count']} | {item['vnic_count']} | {item['public_ip_count']} |"
        )
    if not compartments:
        lines.append("| - | 0 | 0 | 0 |")

    lines.append("")
    lines.append("## Top Subnets by Occupancy (Top 30)")
    lines.append("")
    lines.append("| Subnet | VCN | VNIC Rows | Private IPs | Public IPs |")
    lines.append("|---|---|---:|---:|---:|")
    for item in subnets[:30]:
        lines.append(
            f"| {item['subnet_name']} | {item['vcn_name']} | {item['instance_count']} | "
            f"{item['private_ip_count']} | {item['public_ip_count']} |"
        )
    if not subnets:
        lines.append("| - | - | 0 | 0 | 0 |")

    lines.append("")
    lines.append("## Full Data")
    lines.append("")
    lines.append("- Full machine-readable details are in the JSON artifact.")

    return "\n".join(lines)
