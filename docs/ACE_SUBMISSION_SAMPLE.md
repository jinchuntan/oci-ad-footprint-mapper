# ACE Contribution Sample

## Title
OCI Availability Domain Footprint Mapper for Compute Placement and Network Density

## Description
This OCI Python SDK automation maps Compute instance placement and network footprint across availability domains and subnets. It correlates instance metadata with VNIC details to report AD-level private/public IP distribution, subnet occupancy, and shape concentration. The tool outputs JSON and Markdown artifacts and uploads them to OCI Object Storage for evidence and capacity planning workflows. The workflow is non-destructive and uses read-only OCI APIs except Object Storage uploads.

## Suggested Product Tags
- Oracle Cloud Infrastructure
- OCI Python SDK
- Compute
- Virtual Cloud Network (VCN)
- Object Storage
- Capacity Planning
- Operations
- Automation
- Reliability
