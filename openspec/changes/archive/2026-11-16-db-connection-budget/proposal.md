# Proposal: Database Connection Budget

## Why

On GCP, the offer and order agents fail with `remaining connection slots are reserved for roles with the SUPERUSER attribute` (14 and 5 log entries in one day). Cloud SQL `csa-db` is `db-f1-micro`, which has about 25 connections, 3 of them reserved for superusers. Thirteen Cloud Run services can each scale to 3 instances, and every agent instance opens three independent pools:
- the psycopg tool pool: `min_size=1`, `max_size=5`
- ADK `DatabaseSessionService`'s own SQLAlchemy engine: QueuePool defaults 5 + 10 overflow
- a second engine for the A2A task store: also 5 + 10

The gateway also opens a third engine for memory. One busy instance can therefore ask for about 35 connections, and idle pooled connections are held until the instance scales to zero.

## What Changes

- **`sales_common.db.create_session_engine()`:** one SQLAlchemy async engine per process, shared by ADK sessions, the A2A task store and gateway memory.
  - Default: `NullPool`. A connection is held only while a query runs; nothing is held while idle.
  - `DB_ASYNC_POOL_SIZE` > 0 switches to a QueuePool of that size, with `DB_ASYNC_MAX_OVERFLOW` (default 0), `pool_pre_ping` and `pool_recycle=300`.
- **psycopg tool pool:**
  - `min_size` defaults to 0 (`DB_POOL_MIN`), so no connection is held while idle
  - `max_size` defaults to 2 (`DB_POOL_MAX`)
  - idle connections close after `DB_POOL_MAX_IDLE_S` (default 60 s)
- **`create_a2a_app`:** passes the shared engine to `DatabaseSessionService(db_engine=…)` and the task store, and disposes it once.
- **Gateway `runtime.py`:** sessions and memory share the engine.
- **Docs:** `.env.example` and BASELINE list the new variables.

## Capabilities

### Modified Capabilities

- `sales-data-store`: adds a connection-budget requirement.

## Non-goals

- No Cloud SQL tier change and no added cost.
- No PgBouncer or connection proxy.
- No change to Cloud Run `MAX_INSTANCES`.

## Impact

- **BASELINE.md sections:** §5 Gateway config / §6 Data (the new env vars).
- **Agents:** none directly; all agents get the change through `create_a2a_app`.
- **APIs/MCP:** none.
- **Data:** no schema change.
- **Scripts:** none.
- **Shared lib:** `sales_common/db.py`, `sales_common/a2a_server.py`.
- **Gateway:** `server/runtime.py`.
- **Deploy:** every service is redeployed to pick up the library change.
