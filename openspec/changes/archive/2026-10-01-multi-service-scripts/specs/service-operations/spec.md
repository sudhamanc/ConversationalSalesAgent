# Spec Delta: service-operations

## Purpose

Defines the operator-facing scripts and their observable behavior for setting up, running locally, deploying to Google Cloud, pausing, and verifying the multi-service sales agent system.

## ADDED Requirements

### Requirement: Local setup

`scripts/setup_local.sh` SHALL:
- create or reuse a Python 3.12 virtual environment at `./venv`
- install the shared library and every service in editable mode
- install client dependencies
- copy `.env.example` to `.env` only when `.env` does not exist

It SHALL NOT overwrite an existing `.env`.

#### Scenario: Existing env preserved
- **WHEN** `.env` already exists and setup runs
- **THEN** `.env` is unchanged and the script reports it was kept

### Requirement: Local start and stop

`scripts/start_local.sh` SHALL:
- require `DATABASE_URL` and `GEMINI_MODEL`
- apply migrations and seed
- start the 2 tool services, the 10 agent services, the gateway and the Vite dev server
- write per-service logs under `logs/`
- wait for each `/healthz` (or `/health`)
- print a URL table

`scripts/stop_local.sh` SHALL stop only the processes started by `start_local.sh`, using recorded PIDs.

#### Scenario: Missing database URL
- **WHEN** `start_local.sh` runs without `DATABASE_URL`
- **THEN** it exits non-zero, printing how to set it, and starts nothing

#### Scenario: Service fails health check
- **WHEN** an agent service fails to become healthy within 60 seconds
- **THEN** the script prints the last 20 lines of that service's log and exits non-zero

### Requirement: Docker Compose stack

`docker compose up` SHALL start PostgreSQL, run migrations and seed once, then start every service with dependency ordering. Only the gateway SHALL be published on host port 8000.

#### Scenario: Fresh machine
- **WHEN** a developer with Docker runs `docker compose up --build` after setting `GOOGLE_API_KEY` and `GEMINI_MODEL` in `.env`
- **THEN** `http://localhost:8000` serves the UI, and a chat reaches the agents

### Requirement: Database operations

`scripts/db.sh` SHALL support `migrate`, `seed` and `reset`. `reset` SHALL refuse to run without `--yes`, and SHALL refuse any database whose host is not local unless `--allow-remote` is also given.

#### Scenario: Accidental reset
- **WHEN** `scripts/db.sh reset` runs without `--yes`
- **THEN** nothing is dropped and the script exits non-zero

### Requirement: One-time GCP setup

`scripts/setup_gcp.sh` SHALL idempotently:
- enable required APIs
- create the Artifact Registry repository, Cloud SQL PostgreSQL instance, database and user
- create secrets (prompting for values not already present, never echoing them)
- create service accounts with least-privilege roles

#### Scenario: Re-run setup
- **WHEN** `setup_gcp.sh` runs a second time
- **THEN** existing resources are reported as present and not recreated

### Requirement: Cloud deployment

`scripts/deploy_cloud.sh` SHALL:
- build and push all 13 images
- run the migration/seed job
- deploy tool services, then agent services (injecting tool service URLs), then the gateway (injecting agent card URLs)
- keep tool and agent services private, granting only the gateway and agent service accounts `roles/run.invoker`

It SHALL support deploying a subset via `--only <service>[,<service>]`.

#### Scenario: Deploy one agent
- **WHEN** `deploy_cloud.sh --only payment` runs
- **THEN** only the payment agent image is built and deployed, and other services are untouched

### Requirement: Pause and resume cloud

`scripts/shutdown_cloud.sh` SHALL remove public access from the gateway and set the Cloud SQL activation policy to `NEVER`. `scripts/start_cloud.sh` SHALL reverse both and print the gateway URL.

#### Scenario: Pause
- **WHEN** `shutdown_cloud.sh` completes
- **THEN** anonymous requests to the gateway return HTTP 403, and the Cloud SQL instance is stopped

### Requirement: End-to-end check

`scripts/e2e_test.py --base-url <url>` SHALL run a scripted conversation and assert the expected responding agent (and key fields) at each step: greeting, discovery with serviceability handoff, product, quote, order. It SHALL exit non-zero on the first failed assertion.

#### Scenario: Handoff verified
- **WHEN** the e2e script sends a company registration with an address
- **THEN** it asserts that tokens from both `discovery_agent` and `serviceability_agent` were streamed in that turn
