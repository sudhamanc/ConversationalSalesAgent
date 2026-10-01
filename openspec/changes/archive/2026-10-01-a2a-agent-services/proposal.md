# Proposal: A2A Agent Services

## Why

All ten sub-agents are loaded into one Python process through `importlib` isolation wrappers, stub packages and `sys.modules` lookups. They share one SQLite file. This forces one monolithic image, a single Cloud Run instance, and silent failures when a module is absent. It also prevents teams from deploying or scaling an agent independently.

## What Changes

- **BREAKING:** Remove the importlib isolation pattern.
  - `SuperAgent/super_agent/sub_agents/*` wrappers are deleted.
  - The "Importlib Isolation" rule in `AGENTS.md` / `CLAUDE.md` is replaced by "A2A service per agent".
- Each domain agent becomes an independently deployable **A2A service** (its own container) exposed with ADK `to_a2a(...)`:
  - discovery, serviceability, product, offer management, order, payment, service fulfillment, customer communication, greeting, faq
  - Greeting and FAQ move out of SuperAgent into `GreetingAgent/` and `FAQAgent/`
- Each service publishes an **Agent Card** at `/.well-known/agent-card.json`, keeps its own ADK sessions and A2A task store in PostgreSQL, and applies the shared context-forwarding callbacks from change `adk2-workflow-orchestration`.
- The SuperAgent becomes the **gateway**: FastAPI + React UI + orchestration workflow, calling agents only via `RemoteA2aAgent`.
- **BREAKING:** Replace the shared SQLite file with **PostgreSQL**:
  - Cloud SQL in GCP; a `postgres:16` container locally
  - schema in versioned SQL migrations under `db/migrations/`, seed data under `db/seed/`
  - agent tools use a shared `sales_common.db` psycopg connection pool
- Replace the seven `sys.modules` cross-agent calls:
  - **notifications:** a transactional outbox in the `notifications` table (status `pending`), dispatched by the customer-communication service
  - **quote status updates and customer-state lookups:** plain SQL through `sales_common.repositories`
- Service-to-service calls on Cloud Run are authenticated with Google-signed ID tokens (services are not public). Locally, calls are unauthenticated on a private compose network.

## Capabilities

### New Capabilities

- `agent-services`: each agent runs as an independent A2A service with discoverable cards, durable sessions, context forwarding, health checks and authentication.
- `sales-data-store`: PostgreSQL as the single system of record, with versioned schema migrations, seed data, and transactional notification outbox semantics.

### Modified Capabilities

None.

## Non-goals

- Converting domain tools (other than catalog and serviceability) to MCP. See change `mcp-remaining-domains`.
- Per-service databases or schema-per-service ownership. One PostgreSQL database with table ownership documented per service.
- Kubernetes/GKE. Cloud Run is the target.

## Impact

- **Code:**
  - every agent project gains `server.py` + `Dockerfile`
  - new `libs/sales_common/`
  - new `GreetingAgent/`, `FAQAgent/`
  - SuperAgent loses `sub_agents/` wrappers and `utils/database.py`
- **Data:**
  - SQLite `sales_agent.db` is migrated once to PostgreSQL seed SQL
  - GCS DB sync (`entrypoint.sh`) is removed
- **Infra:** 10 agent services + gateway + 2 tool services + Cloud SQL (see `multi-service-scripts`).
- **Docs:** `AGENTS.md`, `CLAUDE.md`, per-agent `AGENTS.md`/`README.md`, `GCP_DEPLOY.md`, architecture brief.
