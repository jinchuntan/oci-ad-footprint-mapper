# OCI Availability Domain Footprint Mapper

Standalone OCI automation tool that maps Compute placement and network footprint by Availability Domain, then exports JSON + Markdown reports and uploads them to OCI Object Storage.

## Purpose

This tool helps platform and operations teams understand workload distribution across ADs and subnets.

OCI services used:

- OCI Identity
- OCI Compute
- OCI Virtual Network
- OCI Object Storage

No destructive actions are executed.

## What It Produces

- AD-level instance distribution
- AD-level private/public IP distribution
- compartment-level footprint summary
- subnet occupancy summary
- top shape usage
- placement skew indicator and recommendation text

## Quick Start (Windows PowerShell)

```powershell
cd <path-to-repo>\oci-ad-footprint-mapper
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Local-only mode (no Object Storage upload):

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1 -SkipUpload
```

## Manual Setup

```powershell
cd <path-to-repo>\oci-ad-footprint-mapper
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe run_mapper.py
```

## Environment Variables

See `.env.example`.

Common values:

- `OCI_CONFIG_PROFILE`
- `OCI_REGION`
- `OCI_ROOT_COMPARTMENT_OCID`
- `OCI_INCLUDE_SUBCOMPARTMENTS`
- `OCI_OBJECT_STORAGE_NAMESPACE` (optional)
- `OCI_OBJECT_STORAGE_BUCKET` (optional; auto-discovered if omitted)
- `OCI_OBJECT_STORAGE_PREFIX`

## Output

Local files (default `output/`):

- `ad_footprint_report_<timestamp>.json`
- `ad_footprint_report_<timestamp>.md`

Object Storage URI pattern:

- `oci://<bucket>@<namespace>/<prefix>/ad_footprint_report_<timestamp>.json`
- `oci://<bucket>@<namespace>/<prefix>/ad_footprint_report_<timestamp>.md`

## Evidence Steps

### Terminal Evidence

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Capture these lines:

- discovered compartment count
- compartment collection progress
- generated local report paths
- uploaded `oci://...` URIs

### Object Storage Evidence

Use namespace + bucket from uploaded URI:

```powershell
oci os object list `
  --namespace-name <namespace> `
  --bucket-name <bucket> `
  --prefix ad-footprint-report
```

Optional metadata verification:

```powershell
oci os object head `
  --namespace-name <namespace> `
  --bucket-name <bucket> `
  --name "ad-footprint-report/<artifact-file-name>"
```

### Output
<img width="781" height="154" alt="image" src="https://github.com/user-attachments/assets/2b7d1b4d-99f7-42b0-bac4-860065d5960d" />
<img width="1919" height="915" alt="image" src="https://github.com/user-attachments/assets/cd127ee9-a93f-4c6c-b3d1-f98c881ad3c1" />


## Safety

- Read-only calls to Identity/Compute/VCN APIs
- only write operation is Object Storage upload
- no create/update/delete OCI resource operations

