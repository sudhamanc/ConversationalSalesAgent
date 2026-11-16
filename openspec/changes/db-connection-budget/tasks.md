# Tasks: Database Connection Budget

## 1. Shared library (`libs/sales_common`)

- [x] 1.1 Add `db.create_session_engine()` (NullPool by default; QueuePool through `DB_ASYNC_POOL_SIZE`/`DB_ASYNC_MAX_OVERFLOW`). Verify: `pytest libs/sales_common/tests -q`, with new tests for both modes.
- [x] 1.2 psycopg pool defaults min 0 / max 2 / max_idle 60 (`DB_POOL_MIN`, `DB_POOL_MAX`, `DB_POOL_MAX_IDLE_S`). Verify: a unit test reads the pool settings.
- [x] 1.3 `create_a2a_app`: one engine shared by `DatabaseSessionService(db_engine=…)` and the task store, disposed once. Verify: `pytest libs/sales_common/tests -q`; a test asserts that the session service and task store share the engine.

## 2. Gateway

- [x] 2.1 `server/runtime.py`: sessions and memory share `create_session_engine()`. Verify: `pytest SuperAgent/tests -q`.

## 3. Docs

- [x] 3.1 `.env.example`, BASELINE (env vars). Verify: `pytest tests/test_baseline_doc.py -q`.

## 4. Deploy

- [ ] 4.1 Redeploy all services (`scripts/deploy_cloud.sh --skip-migrate`). Verify: services healthy; no new "remaining connection slots" log entries after a journey.
