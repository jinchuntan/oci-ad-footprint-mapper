from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any


class FootprintAnalyzer:
    def analyze(
        self,
        generated_at: datetime,
        region: str,
        tenancy_ocid: str,
        scanned_compartments: list[dict[str, Any]],
        skipped_compartments: list[dict[str, str]],
    ) -> dict[str, Any]:
        all_instances: list[dict[str, Any]] = []
        all_vnics: list[dict[str, Any]] = []

        for compartment_data in scanned_compartments:
            compartment = compartment_data["compartment"]
            data = compartment_data["data"]

            for item in data["instances"]:
                all_instances.append(
                    {
                        "compartment_id": compartment.id,
                        "compartment_name": compartment.name,
                        **item,
                    }
                )

            for item in data["vnics"]:
                all_vnics.append(
                    {
                        "compartment_id": compartment.id,
                        "compartment_name": compartment.name,
                        **item,
                    }
                )

        ad_instance_counts = Counter(row["availability_domain"] for row in all_instances)
        ad_private_ip_counts = Counter(row["availability_domain"] for row in all_vnics if row.get("private_ip"))
        ad_public_ip_counts = Counter(row["availability_domain"] for row in all_vnics if row.get("public_ip"))
        shape_counts = Counter(row["shape"] for row in all_instances)

        subnet_counts: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "subnet_name": "",
                "subnet_id": "",
                "vcn_name": "",
                "vcn_id": "",
                "instance_count": 0,
                "public_ip_count": 0,
                "private_ip_count": 0,
            }
        )

        for row in all_vnics:
            subnet_key = row.get("subnet_id") or "UNKNOWN_SUBNET"
            entry = subnet_counts[subnet_key]
            entry["subnet_name"] = row.get("subnet_name") or "UNKNOWN_SUBNET"
            entry["subnet_id"] = row.get("subnet_id") or "UNKNOWN_SUBNET"
            entry["vcn_name"] = row.get("vcn_name") or "UNKNOWN_VCN"
            entry["vcn_id"] = row.get("vcn_id") or "UNKNOWN_VCN"
            entry["instance_count"] += 1
            if row.get("private_ip"):
                entry["private_ip_count"] += 1
            if row.get("public_ip"):
                entry["public_ip_count"] += 1

        compartment_summary = []
        for comp in scanned_compartments:
            compartment = comp["compartment"]
            data = comp["data"]
            instance_count = len(data["instances"])
            public_ip_count = sum(1 for row in data["vnics"] if row.get("public_ip"))
            compartment_summary.append(
                {
                    "compartment_id": compartment.id,
                    "compartment_name": compartment.name,
                    "instance_count": instance_count,
                    "vnic_count": len(data["vnics"]),
                    "public_ip_count": public_ip_count,
                }
            )

        skew = self._compute_skew(ad_instance_counts)

        return {
            "metadata": {
                "report_name": "availability_domain_footprint",
                "generated_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
                "region": region,
                "tenancy_ocid": tenancy_ocid,
            },
            "summary": {
                "scanned_compartment_count": len(scanned_compartments),
                "skipped_compartment_count": len(skipped_compartments),
                "total_instances": len(all_instances),
                "total_vnics": len(all_vnics),
                "total_public_ips": sum(1 for row in all_vnics if row.get("public_ip")),
                "ad_instance_distribution": dict(ad_instance_counts),
                "ad_private_ip_distribution": dict(ad_private_ip_counts),
                "ad_public_ip_distribution": dict(ad_public_ip_counts),
                "top_shapes": shape_counts.most_common(10),
                "placement_skew": skew,
            },
            "compartments": sorted(compartment_summary, key=lambda item: item["compartment_name"].lower()),
            "subnet_footprint": sorted(subnet_counts.values(), key=lambda item: item["instance_count"], reverse=True),
            "skipped_compartments": skipped_compartments,
            "instances": all_instances,
            "vnic_mappings": all_vnics,
        }

    def _compute_skew(self, ad_counts: Counter[str]) -> dict[str, Any]:
        if not ad_counts:
            return {
                "status": "NO_DATA",
                "max_ad": None,
                "max_ad_ratio": 0,
                "recommendation": "No instances found in scope.",
            }

        total = sum(ad_counts.values())
        max_ad, max_count = ad_counts.most_common(1)[0]
        ratio = round((max_count / total) * 100, 2)

        if ratio >= 80:
            status = "HIGH_SKEW"
            recommendation = f"{ratio}% of instances are in {max_ad}; consider balancing across ADs."
        elif ratio >= 60:
            status = "MODERATE_SKEW"
            recommendation = f"{ratio}% of instances are in {max_ad}; review AD spread for resilience."
        else:
            status = "BALANCED"
            recommendation = "Instance placement across ADs looks reasonably balanced."

        return {
            "status": status,
            "max_ad": max_ad,
            "max_ad_ratio": ratio,
            "recommendation": recommendation,
        }
