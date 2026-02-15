from __future__ import annotations

from typing import Any

from oci.pagination import list_call_get_all_results


class PlacementCollector:
    def __init__(self, compute_client: Any, network_client: Any) -> None:
        self.compute_client = compute_client
        self.network_client = network_client

    def collect_compartment_data(self, compartment_ocid: str) -> dict[str, Any]:
        instances = list_call_get_all_results(
            self.compute_client.list_instances,
            compartment_id=compartment_ocid,
        ).data

        instance_by_id = {instance.id: instance for instance in instances}

        vnic_attachments = list_call_get_all_results(
            self.compute_client.list_vnic_attachments,
            compartment_id=compartment_ocid,
        ).data

        subnet_cache: dict[str, Any] = {}
        vcn_cache: dict[str, Any] = {}
        network_rows: list[dict[str, Any]] = []

        for attachment in vnic_attachments:
            vnic_id = getattr(attachment, "vnic_id", None)
            instance_id = getattr(attachment, "instance_id", None)
            if not vnic_id:
                continue

            vnic = self.network_client.get_vnic(vnic_id=vnic_id).data

            subnet_id = getattr(vnic, "subnet_id", "")
            if subnet_id and subnet_id not in subnet_cache:
                subnet_cache[subnet_id] = self.network_client.get_subnet(subnet_id=subnet_id).data

            vcn_id = getattr(vnic, "vcn_id", "")
            if vcn_id and vcn_id not in vcn_cache:
                vcn_cache[vcn_id] = self.network_client.get_vcn(vcn_id=vcn_id).data

            instance = instance_by_id.get(instance_id)
            ad = instance.availability_domain if instance else "UNKNOWN_AD"
            shape = instance.shape if instance else "UNKNOWN_SHAPE"

            subnet = subnet_cache.get(subnet_id)
            vcn = vcn_cache.get(vcn_id)

            network_rows.append(
                {
                    "instance_id": instance_id,
                    "instance_name": instance.display_name if instance else "UNKNOWN_INSTANCE",
                    "instance_state": instance.lifecycle_state if instance else "UNKNOWN",
                    "availability_domain": ad,
                    "shape": shape,
                    "vnic_id": vnic_id,
                    "private_ip": getattr(vnic, "private_ip", None),
                    "public_ip": getattr(vnic, "public_ip", None),
                    "subnet_id": subnet_id,
                    "subnet_name": subnet.display_name if subnet else "UNKNOWN_SUBNET",
                    "subnet_cidr": getattr(subnet, "cidr_block", ""),
                    "vcn_id": vcn_id,
                    "vcn_name": vcn.display_name if vcn else "UNKNOWN_VCN",
                }
            )

        instance_rows = [
            {
                "instance_id": instance.id,
                "instance_name": instance.display_name,
                "availability_domain": instance.availability_domain,
                "shape": instance.shape,
                "state": instance.lifecycle_state,
                "fault_domain": getattr(instance, "fault_domain", None),
            }
            for instance in instances
        ]

        return {
            "instances": instance_rows,
            "vnics": network_rows,
        }
