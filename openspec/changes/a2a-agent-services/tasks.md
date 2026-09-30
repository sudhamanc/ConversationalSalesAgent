# Tasks: A2A Agent Services

## 1. Data store

- [x] 1.1 Write `db/migrations/001_sales_schema.sql` (all 19 tables in PostgreSQL dialect, with indexes and FKs); verify it applies on an empty PostgreSQL 16 database
- [x] 1.2 Implement `sales_common.migrate` runner with a `schema_migrations` table; test verifies a second run applies nothing
- [x] 1.3 Implement `scripts/export_sqlite_seed.py` and generate `db/seed/001_sales_data.sql` from `SuperAgent/data/sales_agent.db`; verify seeding twice yields identical row counts
- [x] 1.4 Implement `sales_common.db` (pool, dict rows, transaction, masked URL logging); unit tests against local PostgreSQL
- [x] 1.5 Document table ownership in `db/README.md`

## 2. Shared service plumbing

- [x] 2.1 Implement `sales_common.a2a_server.create_a2a_app` (App + DB sessions + DatabaseTaskStore + `/healthz`); test serves a fake-model agent and fetches its card
- [x] 2.2 Implement `sales_common.auth.service_headers` (none / gcp_id_token); unit test for `none` mode and a token-cache test with a stubbed fetcher
- [x] 2.3 Implement `sales_common.notifications.enqueue`, `sales_common.repositories` (quotes, customer_state), `sales_common.maintenance.cleanup_stale_records`; tests against local PostgreSQL

## 3. Agent services (one group per agent; each: port tools to PostgreSQL, remove sys.modules calls, add server.py, Dockerfile, tests)

- [x] 3.1 Discovery: move to `DiscoveryAgent/discovery_agent/`, port 13 tools; tests for search/add company and `customer_context` export
- [x] 3.2 Offer management: port quote persistence and notifications to outbox; tests for quote creation and `_context_update.offer_context`
- [x] 3.3 Order: port cart/order tools, `mark_quote_ordered` via repository, outbox notification; tests for cart → order flow
- [x] 3.4 Payment: port to PostgreSQL (remove silent in-memory fallback), outbox notification; tests for process_payment and `payment_context` export
- [x] 3.5 Service fulfillment: port scheduling/installation/activation, remove silent fallback, outbox notifications; tests for schedule_installation
- [x] 3.6 Customer communication: port to PostgreSQL, add outbox dispatcher; tests for enqueue → dispatch (SMTP disabled → simulated)
- [x] 3.7 Greeting and FAQ: extract into `GreetingAgent/` and `FAQAgent/` with servers; construction tests
- [x] 3.8 Serviceability and Product agents: servers only here (tools move to MCP in `catalog-serviceability-mcp`); construction tests

## 4. Gateway cutover

- [x] 4.1 Delete `SuperAgent/super_agent/sub_agents/*` wrappers and `super_agent/utils/database.py`; verify `grep -rn "spec_from_file_location\|sys.modules\[" --include=*.py` finds no agent-loading code
- [x] 4.2 Local multi-process integration test: start PostgreSQL, 2 tool services, 10 agent services, and the gateway with scripted fake models; drive discovery → serviceability handoff over real A2A and assert SSE output
- [x] 4.3 Update `AGENTS.md` (Golden Rule, registry, communication), `CLAUDE.md`, per-agent `AGENTS.md`/`README.md`; verify docs reference `server.py`/A2A instead of importlib
