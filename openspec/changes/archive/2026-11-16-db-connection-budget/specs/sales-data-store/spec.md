## ADDED Requirements

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
