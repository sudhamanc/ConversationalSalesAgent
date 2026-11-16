# Sales database (PostgreSQL 16)

One PostgreSQL database is the system of record for every service. Schema is
managed only by versioned SQL files here; services never create tables at
runtime (except ADK's session tables and a2a-sdk's `a2a_tasks`, which those
libraries create themselves).

## Apply

```bash
python -m sales_common.migrate            # migrations only
python -m sales_common.migrate --seed     # migrations + demo seed (each file applied once)
scripts/db.sh up | down | migrate | seed | reset --yes   # up: local PostgreSQL (Docker, Homebrew fallback)
```

Applied files are recorded in `schema_migrations` and `seed_versions`; re-runs are no-ops.
A PostgreSQL advisory lock serialises concurrent runners.

## Files

| File | Contents |
|---|---|
| `migrations/001_sales_schema.sql` | 19 sales tables |
| `migrations/002_catalog.sql` | `products` (catalog service) |
| `migrations/003_platform.sql` | `adk_memories` (long-term memory), `revoked_sessions` (gateway tokens) |
| `migrations/004_coverage.sql` | `coverage_zones` (serviceability service) |
| `migrations/005_notifications_seq.sql` | `notifications.seq` insertion-order column for the outbox dispatcher |
| `seed/001_sales_data.sql` | demo prospects/accounts, contacts, quotes, orders, fulfillments and related rows (edited by hand) |
| `seed/002_catalog.sql` | 16 SKUs with price/family (`scripts/export_catalog_seed.py`) |
| `seed/003_coverage.sql` | 38 coverage ZIPs (`scripts/export_coverage_seed.py`) |

## Table ownership (writer services)

| Tables | Owner | Other writers (intentional; `mcp-remaining-domains` was decided against) |
|---|---|---|
| accounts, contacts, spend, opportunities, insights, actions | discovery_agent | service_fulfillment_agent (accounts) |
| quotes | offer_management_agent | order_agent (status), gateway maintenance (expiry) |
| carts, cart_items, orders, order_items | order_agent | payment_agent, service_fulfillment_agent (orders.status), gateway maintenance |
| payments, payment_events, payment_rate_limit, customer_payment_methods | payment_agent | — |
| fulfillments, customer_master | service_fulfillment_agent | — |
| notifications, dedup_cache | customer_communication_agent (dispatcher) | all producers insert `pending` rows (outbox) |
| products | catalog service | — |
| coverage_zones | serviceability service | — |
| adk_memories, revoked_sessions | gateway | — |
| sessions, events, app_states, user_states (ADK), a2a_tasks (a2a-sdk) | every agent service + gateway | keyed by app name |
