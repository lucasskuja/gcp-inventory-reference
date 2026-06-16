# GCP Inventory Reference

Reference implementation for generating Markdown-based inventory documentation for Google Cloud projects across core infrastructure and data services.

## What This Repository Is

This repository provides a reusable pattern for documenting Google Cloud environments through a single inventory generation script. The current implementation focuses on practical infrastructure discovery and structured Markdown output rather than package abstractions or framework scaffolding.

It is intended to be useful as:

- a reference implementation for GCP inventory documentation
- a starting point for environment discovery and architecture reviews
- a reusable baseline for extending service coverage and documentation standards

## What It Currently Does

The repository centers on [`gcp_inventory.py`](./gcp_inventory.py), a Python script that uses the `gcloud` and `bq` CLIs to inspect a target GCP project and generate a Markdown inventory report.

The generated report includes:

- project metadata
- enabled APIs and services
- discovered resources grouped by service
- operational metadata such as region, runtime, status, networking details, and basic configuration attributes

By default, output is written to `docs/<project>/inventario.md`.

## Current Scope

The current implementation collects inventory data for the following resource domains:

- enabled Google Cloud APIs and services
- Compute Engine instances
- GKE clusters
- Cloud Run services
- Cloud Functions
- Cloud Storage buckets
- BigQuery datasets and tables
- Cloud SQL instances
- Pub/Sub topics and subscriptions
- Secret Manager secrets
- VPC networks and subnets
- firewall rules
- forwarding rules / load balancer endpoints
- Cloud Scheduler jobs
- Cloud Tasks queues
- Artifact Registry repositories and packages or images
- IAM service accounts

The exact set of collectors is defined in [`gcp_inventory.py`](./gcp_inventory.py).

## Execution Model

This is currently a script-first repository.

- Python is used as the orchestration layer.
- The implementation relies primarily on `gcloud` and `bq` command execution.
- Markdown is used as the delivery format for human-readable environment documentation.
- Output is optimized for documentation, review, and handover rather than machine-oriented export formats.

This design makes the repository easy to extend without requiring a larger application structure.

## Repository Structure

```text
gcp-inventory-reference/
|-- gcp_inventory.py
|-- requirements.txt
|-- README.md
```

## Usage

### Prerequisites

- Python 3.10+
- Google Cloud SDK with `gcloud`
- `bq` CLI available in the environment
- access to the target GCP project through Application Default Credentials or an authenticated local `gcloud` session

Install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Authentication

The script expects Google Cloud credentials to be available in the local environment. In practice, the most common local setup is:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

For automation contexts, `GOOGLE_APPLICATION_CREDENTIALS` can be used with a service account that has read access to the required resource domains.

### Command Interface

The current CLI arguments are implemented in Portuguese and should be used exactly as defined by the script:

```bash
python gcp_inventory.py --projeto YOUR_PROJECT_ID
```

Optional custom output path:

```bash
python gcp_inventory.py --projeto YOUR_PROJECT_ID --saida docs/custom-inventory.md
```

Available arguments:

| Argument | Short | Required | Description |
| --- | --- | --- | --- |
| `--projeto` | `-p` | Yes | Target GCP project ID |
| `--saida` | `-o` | No | Output file path. Default: `docs/<project>/inventario.md` |

## Output

The script generates a Markdown report organized by service sections and tabular summaries.

Typical output characteristics:

- one inventory file per target project
- service-by-service sections
- human-readable tables
- explicit handling of empty or unavailable services

Default output path:

```text
docs/<project>/inventario.md
```

## Access Requirements

The script is designed for read-only discovery. In most environments, broad viewer access plus service-specific metadata permissions are sufficient.

Minimum practical roles will vary by environment, but the current README baseline is:

- `roles/viewer`
- `roles/bigquery.metadataViewer`
- `roles/secretmanager.viewer`
- `roles/iam.serviceAccountViewer`

For production usage, a narrower custom role with only the required `list` and `get` permissions is preferable.

## Extending The Inventory

The repository is intentionally straightforward to extend.

Typical extension points include:

- adding new collector functions for additional services
- refining table schemas for existing services
- adjusting output conventions for internal documentation standards
- integrating execution into CI/CD or scheduled operational workflows

When extending the script, prefer changes that preserve:

- read-only behavior
- deterministic Markdown output
- graceful handling of unavailable services or insufficient permissions
- a consistent section and table structure across collectors

## Current Limitations

This repository should be positioned according to its current implementation boundaries:

- it is a standalone script, not a packaged library
- it depends primarily on local CLI availability and authenticated environment state
- it generates Markdown output only
- service coverage is broad but not exhaustive across all GCP products
- there is no native test suite in the current repository
- there is no built-in multi-project orchestration beyond external shell looping

## Contribution Model

Contributions should strengthen the repository as a reusable reference asset.

Priority areas:

- new collectors for additional GCP services
- stronger output consistency
- safer edge-case handling
- better maintainability without over-engineering the repository

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for contribution guidelines.

## Positioning Summary

This repository is best understood as a reusable reference implementation for GCP environment inventory documentation. It is already useful as a practical baseline today, and it can be extended into project-specific governance, audit, architecture review, or operational documentation workflows as needed.
