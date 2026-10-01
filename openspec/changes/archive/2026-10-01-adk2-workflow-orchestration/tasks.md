# Tasks: ADK 2.x Workflow Orchestration

## 1. Dependencies and shared library

- [x] 1.1 Pin `google-adk[a2a,mcp,db]==2.10.0`, `asyncpg`, `greenlet`, `psycopg[binary]`, `itsdangerous` in the new `libs/sales_common/pyproject.toml` and every service `pyproject.toml`; verify `pip install -e libs/sales_common` succeeds and `python -c "import google.adk; print(google.adk.__version__)"` prints 2.10.0
- [x] 1.2 Implement `sales_common.config` (fail-fast `require_env`, model settings, App context settings) with unit tests for missing `GEMINI_MODEL`
- [x] 1.3 Implement `sales_common.adk_app.build_app()` returning an `App` with `EventsCompactionConfig` and `ContextCacheConfig` from env; unit test asserts both configs and defaults

## 2. Context bridge and memory

- [x] 2.1 Implement `sales_common.context` (`JOURNEY_KEYS`, `import_forwarded_context` before_agent_callback, `export_context_delta` after_tool_callback, `build_forwarded_metadata`); unit tests with a scripted fake LLM verify import into state and `_context_update` export
- [x] 2.2 Implement `sales_common.memory.PostgresMemoryService`; integration test against local PostgreSQL verifies add/search and per-user isolation
- [x] 2.3 Add `db/migrations` SQL for `adk_memories` and `revoked_sessions`; verify migration applies cleanly on an empty database

## 3. Gateway workflow

- [x] 3.1 Implement `super_agent/registry.py` (agent names, A2A card URLs from env, `RemoteA2aAgent` factory with metadata provider); unit test builds all 10 remote agents
- [x] 3.2 Implement workflow nodes `prepare_turn`, `route_intent`, `dispatch`, `HandoffPolicyNode`, `finish_turn` and assemble `sales_journey` Workflow + App; unit tests with in-process fake agents verify routing, greeting fast path, fallback, both handoffs, and the 2-hop cap
- [x] 3.3 Implement `ContextBridgePlugin`; unit test verifies `_context_update` from a function_response lands in persisted session state
- [x] 3.4 Port routing rules from `prompts.py` to the router `static_instruction` (remove transfer mechanics); verify prompt contains all 10 agent names

## 4. Server

- [x] 4.1 Replace `InMemorySessionService` with `DatabaseSessionService` and `Runner(app=...)` in `server/main.py`; verify `/health` and session creation against local PostgreSQL
- [x] 4.2 Rewrite `middleware/auth.py` with `itsdangerous` signed tokens + revocation table; unit tests for valid, expired, tampered, revoked tokens
- [x] 4.3 Rewrite `api/chat.py` event mapping (author filter, dedupe, fixed tool tables, remove synthetic payment re-run and greeting runner); unit tests feed recorded events and assert the SSE sequence
- [x] 4.4 Save session to memory after each turn and pass `csa_uid` from the client (`utils/api.js`); verify with an end-to-end local run
- [x] 4.5 Update `AGENTS.md`, `CLAUDE.md`, `SuperAgent/README.md`, `SuperAgent/super_agent/sub_agents/{AGENTS,CLAUDE}.md` to describe the workflow, context bridge, and removed importlib pattern; verify no remaining references to `importlib` isolation as a requirement
