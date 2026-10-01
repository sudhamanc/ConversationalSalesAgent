# Tasks: Multi-Service Scripts and Deployment

## 1. Manifest and images

- [x] 1.1 Create `scripts/services.conf` listing all 13 services; verify `bash -c 'source scripts/lib.sh; list_services'` prints 13 rows
- [x] 1.2 Write Dockerfiles for gateway, 2 tool services, 10 agents and update `.dockerignore`; verify each `Dockerfile` references existing paths (static COPY-path check passed; images not built: no Docker daemon in the build sandbox)
- [x] 1.3 Write `docker-compose.yml` with postgres, db-init, all services; verify YAML parses and every service's env references are defined in `.env.example`

## 2. Local scripts

- [x] 2.1 Write `scripts/setup_local.sh` (no `.env` overwrite); verify with `bash -n` and a run in the sandbox
- [x] 2.2 Write `scripts/db.sh` (migrate/seed/reset guards); verify reset refuses without `--yes`
- [x] 2.3 Write `scripts/start_local.sh` / `stop_local.sh` (PID files, health waits, log tail on failure); verify a full local start against PostgreSQL 16 with all health checks green, then stop
- [x] 2.4 Update `scripts/e2e_test.py` with assertions; verify against the local stack — verified live on 2026-09-30: `python scripts/e2e_test.py --base-url http://127.0.0.1:8000` passed all 5 steps against real Gemini (client helpers now in `scripts/e2e_client.py`, see `agent-eval-suite`)

## 3. Cloud scripts

- [x] 3.1 Write `scripts/setup_gcp.sh` (idempotent, `--dry-run`); verify `bash -n` and dry-run output lists every resource
- [x] 3.2 Write `scripts/deploy_cloud.sh` (`--only`, `--dry-run`, ordered deploy, URL wiring, IAM); verify dry-run prints commands for all 13 services in order
- [x] 3.3 Write `scripts/start_cloud.sh` / `shutdown_cloud.sh` (gateway IAM + Cloud SQL activation policy, `--dry-run`); verify dry-run output

## 4. Cleanup and docs

- [x] 4.1 Remove root `Dockerfile`, `entrypoint.sh`, and `SuperAgent/*.sh` (`git mv` where rewritten); verify no doc references remain (`grep`)
- [x] 4.2 Rewrite `GCP_DEPLOY.md`, update `README.md` quick start and `SuperAgent/README.md`; verify every command in the docs exists in `scripts/`
