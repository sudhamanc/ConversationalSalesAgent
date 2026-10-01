# Proposal: Multi-Service Scripts and Deployment

## Why

The existing scripts all assume one process and one container:
- `SuperAgent/start_servers.sh`
- `deploy_cloud.sh`
- `start_cloud.sh`
- `shutdown_cloud.sh`
- the root `Dockerfile` / `entrypoint.sh` with GCS SQLite sync
- `GCP_DEPLOY.md`

After the rewrite there are 13 application services plus PostgreSQL:
- gateway
- 10 A2A agents
- 2 REST/MCP tool services

The scripts must set up, start, deploy, and pause that topology.

## What Changes

- **New `scripts/` directory** (existing scripts moved with `git mv` and rewritten):

  | Script | Purpose |
  |---|---|
  | `setup_local.sh` | venv, editable installs of `libs/sales_common` and all services, client `npm ci`, `.env` template copy |
  | `start_local.sh` / `stop_local.sh` | native processes against a PostgreSQL URL; per-service logs in `logs/`; health checks |
  | `db.sh` | `migrate`, `seed`, `reset` (reset requires `--yes`) |
  | `setup_gcp.sh` | one-time: APIs, Artifact Registry, Cloud SQL, secrets, service accounts, IAM |
  | `deploy_cloud.sh` | build and push all images with Cloud Build, run migrations/seed as a Cloud Run job, deploy services in dependency order, wire URLs, set IAM invoker bindings |
  | `start_cloud.sh` / `shutdown_cloud.sh` | toggle public gateway access and Cloud SQL activation policy |
  | `e2e_test.py` | scripted conversation with assertions |

- **New `docker-compose.yml`:** postgres 16, a one-shot `db-init` (migrate + seed), 2 tool services, 10 agents, and the gateway on a private network. Only the gateway port is published.
- **New per-service Dockerfiles.** Build context is the repo root.
- **BREAKING:** remove the root `Dockerfile` and `entrypoint.sh`. `SuperAgent/*.sh` are replaced by `scripts/*.sh`.
- Rewrite `GCP_DEPLOY.md` for the multi-service deployment and update `README.md` quick start.
- Add `.env.example` files: root (shared), and per service where extra vars are needed.

## Capabilities

### New Capabilities

- `service-operations`: developer and operator workflows to set up, run, deploy, pause and verify the multi-service system.

### Modified Capabilities

None.

## Non-goals

- Terraform/IaC (the scripts use `gcloud`; IaC can follow).
- CI/CD pipelines.
- Kubernetes manifests.

## Impact

- **Files:**
  - `scripts/`, `docker-compose.yml`, `*/Dockerfile`, `.dockerignore`
  - removal of the root `Dockerfile`, `entrypoint.sh`, `SuperAgent/*.sh`
- **GCP:**
  - Cloud SQL instance, 13 Cloud Run services, 1 Cloud Run job
  - service accounts `csa-gateway`, `csa-agents`, `csa-tools`
  - retired GCS sync bucket usage
- **Cost:** Cloud SQL `db-f1-micro` (~$10/mo if left running; `shutdown_cloud.sh` stops it). Cloud Run services scale to zero.
- **Docs:** `README.md`, `GCP_DEPLOY.md`, `SuperAgent/README.md`, architecture brief deployment section.
