# sales-data-store Specification

## Purpose
TBD - created by archiving change a2a-agent-services. Update Purpose after archive.
## Requirements
### Requirement: PostgreSQL system of record

All transactional sales data SHALL be stored in one PostgreSQL 16 database: accounts, contacts, opportunities, insights, actions, spend, quotes, carts, cart items, orders, order items, payments, payment events, payment rate limits, payment methods, fulfillments, customer master, notifications, notification dedup, products, and coverage. No service SHALL use a local database file at runtime.

#### Scenario: Two gateway instances
- **WHEN** two gateway instances and multiple agent services write orders concurrently
- **THEN** all writes are visible to every service without file synchronization

### Requirement: Versioned migrations

Schema changes SHALL be applied by ordered, idempotent SQL migration files. The migration runner SHALL record applied versions and skip them on re-run.

#### Scenario: Re-running migrations
- **WHEN** the migration runner is executed twice against the same database
- **THEN** the second run applies nothing and exits 0

### Requirement: Seed data

A seed step SHALL load the demo dataset (the prospect accounts and related tables in `db/seed/001_sales_data.sql`, the 16-SKU product catalog, and the coverage data). It SHALL be safe to run repeatedly without duplicating rows.

#### Scenario: Seed twice
- **WHEN** the seed step runs twice
- **THEN** row counts equal those after the first run

### Requirement: Notification outbox

Services other than customer communication SHALL request customer notifications by inserting a `notifications` row with status `pending`, in the same transaction as the business change that triggers it. The customer communication service SHALL deliver pending notifications:
- at least once
- after de-duplication
- marking each row `sent` or `failed` with an error message

Delivery SHALL run both in the service's background loop and on demand in `POST /dispatch`, so that a service that only has CPU while serving requests (Cloud Run scaled to zero) still delivers notifications.

#### Scenario: Order confirmation
- **WHEN** `order_agent` creates order `ORD-1` for a contact with an email address
- **THEN** a `notifications` row of type `order_confirmation` with status `pending` exists in the same commit, and is later marked `sent` (or `simulated` when SMTP is disabled)

#### Scenario: Communication service down
- **WHEN** the customer communication service is not running while an order is created
- **THEN** order creation still succeeds, and the notification is delivered after the service starts

#### Scenario: Communication service scaled to zero
- **WHEN** a quote confirmation is queued and the customer communication service has no running instance
- **THEN** the next `POST /dispatch` starts the service and the row is marked `sent` within that request

### Requirement: Credentials never in source

Database credentials SHALL be supplied only through environment variables or Secret Manager, and SHALL NOT be logged.

#### Scenario: Startup logging
- **WHEN** a service logs its database target at startup
- **THEN** the password component of the URL is masked

### Requirement: Database connection budget

Each service process SHALL use one SQLAlchemy async engine for ADK sessions, the A2A task store and gateway memory. By default that engine SHALL NOT hold idle connections (`NullPool`). `DB_ASYNC_POOL_SIZE` greater than 0 SHALL select a bounded QueuePool with `DB_ASYNC_MAX_OVERFLOW` overflow. The psycopg tool pool SHALL default to `min_size` 0, `max_size` 2 and idle connections closed after 60 s (`DB_POOL_MIN`, `DB_POOL_MAX`, `DB_POOL_MAX_IDLE_S`).

#### Scenario: Agent service shares one engine
- **WHEN** `create_a2a_app` builds an agent service
- **THEN** its `DatabaseSessionService` and A2A task store use the same engine, created by `sales_common.db.create_session_engine`

#### Scenario: Default engine holds no idle connections
- **WHEN** `DB_ASYNC_POOL_SIZE` is unset
- **THEN** `create_session_engine()` returns an engine whose pool is a `NullPool`

#### Scenario: Pooling opt-in
- **WHEN** `DB_ASYNC_POOL_SIZE=3` and `DB_ASYNC_MAX_OVERFLOW=1`
- **THEN** the engine pool has size 3 and overflow 1

#### Scenario: Idle tool pool
- **WHEN** no `DB_POOL_*` variables are set
- **THEN** the psycopg pool has `min_size` 0, `max_size` 2 and `max_idle` 60

### Requirement: Serviceability checks are stored

Migration `006_serviceability_checks.sql` SHALL create `serviceability_checks`. `serviceability_agent` SHALL insert one row per successful `check_service_availability`: the customer (when known), the address, `is_serviceable`, the recorded `serviceability_context` JSON and `checked_at`. An insert failure SHALL be logged and SHALL NOT fail the check. `sales_common.repositories.customer_state` SHALL return the latest check for the customer.

#### Scenario: Check recorded
- **WHEN** `check_service_availability` succeeds for a known customer
- **THEN** a `serviceability_checks` row exists with that customer id and ZIP

