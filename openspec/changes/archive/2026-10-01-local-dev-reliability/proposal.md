# Proposal: Local Development Reliability

## Why

The first local run on a fresh machine surfaced three problems:

- **No uniform way to get PostgreSQL.** The README asked each developer to hand-type a `docker run`. When the Docker engine could not pull `postgres:16` (a corporate proxy, or the engine VM's network still starting), there was no defined fallback, so machines diverged (Docker on one, ad-hoc Homebrew on another).
- **Nothing told the developer to start the container engine.** With Rancher Desktop / Docker Desktop closed, the `docker` command failed with a raw socket error, and `start_local.sh` started 14 processes against a database that did not exist.
- **The router failed on Gemini 3.** `route_intent` capped output at 256 tokens. Gemini 3 thinks by default and thinking tokens count toward `max_output_tokens`, so the router used ~250-700 thinking tokens and returned truncated text ("Here is the JSON requested:"), which failed `RouteDecision` validation and surfaced as "The assistant service is temporarily unavailable" on most LLM-routed turns.

Two leftovers also confused configuration: a stale `SuperAgent/server/.env.example` (pre-rewrite variables) and a second `.env` lookup path in the gateway.

## What Changes

- **`scripts/db.sh up` / `down`** own the local PostgreSQL lifecycle: reuse a reachable `DATABASE_URL`, else Docker (`csa-postgres`, volume `csa-pgdata`), else Homebrew `postgresql@16` when the image cannot be pulled or Docker is not installed; then migrate + seed. `--native` skips Docker; `PG_IMAGE` overrides the image (registry mirror).
- **Container engine detection:** if Docker is installed but its engine is down, `up` names the desktop app to start (Rancher Desktop, Docker Desktop, OrbStack, Podman Desktop, colima), waits up to 2 minutes when the app is already booting, and never silently falls back to Homebrew.
- **`start_local.sh` preflight:** refuses to start when `DATABASE_URL` is unreachable and points to `scripts/db.sh up`.
- **`scripts/lib.sh`:** new `db_url_parts` and `db_check` helpers.
- **Router:** `route_intent` uses `thinking_level=MINIMAL` on `gemini-3*` models and `max_output_tokens=1024`.
- **Config cleanup:** delete `SuperAgent/server/.env.example`; the gateway loads only the repo-root `.env`.
- **Repo cleanup:** delete legacy root documents from the ADK 1.x era (`ADKSessionStateImplementation.md`, `GameDayDemoScript.md`, `MilestonePlan.md`, `Plan- UnifiedDatabaseArchitectureforMulti-AgentSystem.md`, `SalesOutreach.md`, `architecture-diagram.png`, `architecture.html`).
- **Process:** `CLAUDE.md` and `AGENTS.md` require every new change to start with an OpenSpec change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `service-operations`: adds the local database lifecycle and the start preflight.
- `conversation-orchestration`: adds the router output-budget requirement.

## Non-goals

- Configuring proxies inside Docker/Rancher VMs (documented, not automated).
- Raising Gemini quotas or handling free-tier `429` errors differently (tracked separately).
- Changing the containerized path (`docker compose up`), whose `postgres` service is unchanged.
- Linux package-manager automation for the native fallback (the script prints instructions).

## Impact

- **Agents / MCP services / data:** none. Schema, migrations and seed are unchanged.
- **Gateway:** `super_agent/workflow.py` (router config), `super_agent/config.py` (single `.env` path).
- **Scripts:** `db.sh`, `lib.sh`, `start_local.sh`, `setup_local.sh` (next-step text).
- **Docs:** `README.md`, `db/README.md`, `SuperAgent/README.md`, `AGENTS.md`, `CLAUDE.md`.
