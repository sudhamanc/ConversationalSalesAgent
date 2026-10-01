# SuperAgent Gateway: B2B Sales Chat with SSE Streaming

The SuperAgent is the **gateway** of the Conversational Sales Agent. It hosts:

- the React chat UI (`client/`, served from `client/dist` in the container image);
- the FastAPI API (`server/`): session tokens, SSE chat, rate limiting;
- the ADK 2.x orchestration **workflow** `sales_journey` (`super_agent/`): a router LLM, deterministic handoffs, durable sessions and long-term memory.

Domain agents are **not** part of this process. Each one is a separate A2A service (ports 8201-8210) that the workflow calls through `RemoteA2aAgent`. See [../AGENTS.md](../AGENTS.md) for the whole system and [../docs/agent-service-guide.md](../docs/agent-service-guide.md) for agent services.

## Layout

```text
SuperAgent/
├── Dockerfile               # Node 20 build of the UI + Python runtime (build context = repo root)
├── pyproject.toml           # package super-sales-agent (super_agent/)
├── super_agent/
│   ├── workflow.py          # sales_journey graph: nodes, RouteDecision, handoff rules
│   ├── agent.py             # build_gateway_app(): RemoteA2aAgent nodes + App + ContextBridgePlugin
│   ├── registry.py          # the 10 domain agents: name, routing description, AGENT_URL_* default
│   ├── prompts.py           # ROUTER_INSTRUCTION (routing rules)
│   ├── plugins.py           # ContextBridgePlugin (journey context merge + delegation audit log)
│   └── config.py            # gateway settings from env (loads repo-root .env for local dev)
├── server/
│   ├── main.py              # FastAPI app, lifespan (fail-fast checks, migrations, cleanup), SPA
│   ├── runtime.py           # Runner + DatabaseSessionService + PostgresMemoryService
│   ├── api/chat.py          # POST /api/chat (SSE)
│   ├── api/sse.py           # ADK events -> UI SSE payloads
│   ├── api/session.py       # POST/DELETE /api/session
│   ├── api/suggestions.py   # follow-up suggestion chips (google-genai)
│   ├── api/debug.py         # GET /api/debug/session (DEBUG=true only)
│   ├── api/client_log.py    # POST /api/client-log (browser console forwarding, Bearer token)
│   ├── run_scenarios.py     # smoke-run chat scenarios against a running gateway
│   └── middleware/          # auth.py (signed tokens), rate_limiter.py
├── client/                  # React 19 + Vite + Tailwind (see client/AGENTS.md)
└── tests/                   # gateway tests
```

## The `sales_journey` Workflow

```mermaid
graph TD
    START(["START"]) --> PREP["prepare_turn"]
    PREP -->|fast: pure greeting| DISPATCH["dispatch"]
    PREP -->|llm| ROUTER["route_intent<br/>RouteDecision"]
    ROUTER --> DISPATCH
    DISPATCH -->|agent name| AGENTS["10 RemoteA2aAgent nodes"]
    AGENTS --> HANDOFF["handoff_policy<br/>HandoffPolicyNode"]
    HANDOFF -->|serviceability_agent or payment_agent| AGENTS
    HANDOFF -->|end| FINISH["finish_turn"]
```

1. **`prepare_turn`** records the user message (`turn_user_message`, `transcript`) and resets `handoff_hops`. A pure greeting ("hi", "good morning", or a `[GREETING]` prefix) goes straight to `greeting_agent` with no router call. Otherwise it searches memory and builds the router input: message, `last_agent`, last reply excerpt, journey flags, company name, memories.
2. **`route_intent`** is an `LlmAgent` (`mode="single_turn"`, `include_contents="none"`, temperature 0, `output_schema=RouteDecision{target, reason}`, `max_output_tokens=1024`, `thinking_level=MINIMAL` on `gemini-3*` models because thinking tokens count toward the output limit) with `ROUTER_INSTRUCTION` as its static instruction.
3. **`dispatch`** validates the target (an unknown target falls back to `faq_agent`), sets `last_agent`, and writes the user message to `a2a_outbound_message`, which is the only text sent to the remote agent.
4. **Agent node:** a `RemoteA2aAgent` (from `sales_common.a2a_client.remote_agent`) sends the message plus forwarded metadata (journey context, transcript, user profile). The gateway session id is used as the remote context id.
5. **`handoff_policy`** (`HandoffPolicyNode`, a custom `google.adk.workflow.Node`) applies `evaluate_handoff()`:
   - `discovery_agent` → `serviceability_agent` when the customer has an address ZIP and serviceability was not yet checked for it;
   - `service_fulfillment_agent` → `payment_agent` when a `schedule_installation` succeeded and the order is still unpaid;
   - at most `MAX_HANDOFF_HOPS = 2` per turn.
6. **`finish_turn`** stores `user:customer_id` / `user:company_name` for returning visitors.

The workflow is wrapped in an ADK `App` (`sales_common.adk_app.build_app`) with events compaction (every 8 invocations, overlap 2, or above 60k tokens keeping 10 events), context caching (TTL 1800 s, 10 intervals, min 4096 tokens) and **`ContextBridgePlugin`**. The plugin merges `_context_update` from remote tool responses into the gateway session's `state_delta`, sets `appointment_confirmed_order` after a successful `schedule_installation`, and logs one `delegation author=... tool=... success=...` line per remote tool call.

### Sessions and Memory

- `DatabaseSessionService` on PostgreSQL (`postgresql+asyncpg://`, derived from `DATABASE_URL` unless `SESSION_DB_URL` is set).
- `sales_common.memory.PostgresMemoryService` (`adk_memories` table). The session is added to memory in the background after each completed turn.
- ADK user id: `web:<uuid4>` from the browser's `csa_uid`; ADK session id: the server-generated session id inside the token.

## API Reference

### `POST /api/session`

Body (optional): `{"client_id": "<uuid4>"}`. Returns `{"session_id": "...", "token": "..."}`. The token is an itsdangerous signature over `{sid, uid}` using `SESSION_SECRET_KEY`, valid for `SESSION_TOKEN_EXPIRY_MIN` minutes. Any gateway instance can verify it.

### `POST /api/chat`

Headers: `Authorization: Bearer <token>`. Body: `{"message": "..."}` (1-4000 characters). Conversation history is kept server-side in the ADK session; the client sends only the current message.

SSE events (`data: {...}` lines):

| `type` | Meaning |
|---|---|
| `token` | Agent text, with `author` = domain agent name. Only domain agents produce text; repeated final texts from A2A are de-duplicated per author. |
| `activity_update` | A remote tool ran (category, tool name, data). Drives the activity panel. |
| `cart_update` | Cart/order tool results. |
| `structured_card` | Typed card, e.g. `card_type: "quote"` from `generate_offer_quote` / `find_best_bundle_offer` / `get_quote_details`. |
| `suggestions` | Follow-up suggestion chips (when `SUGGESTIONS_ENABLED=true`). |
| `error` | User-friendly error naming the unavailable service. |
| `done` | End of turn. |

Errors before streaming: 401 invalid/expired token, 429 rate limit, 400 invalid body. Retryable model errors (503/429) are retried up to 3 times if no domain event was produced yet.

### `DELETE /api/session`

Revokes the current token (`revoked_sessions` table). Returns `{"status": "revoked"}` or `{"status": "not_found"}`.

### `GET /api/debug/session`

Only when `DEBUG=true` (otherwise 403). Requires the Bearer token and returns the caller's own ADK session state (`session_id`, `user_id`, `state`). For development only.

### Health

- `GET /health` and `GET /healthz`: `{"status": "ok", "agent": "<AGENT_NAME>", "model": "<GEMINI_MODEL>"}`; 503 with `"degraded"` when PostgreSQL is unreachable.
- `GET /api/session/health`: liveness.

### Other

- `POST /api/client-log`: forwards browser console lines (development aid). Requires `Authorization: Bearer <token>` (401 otherwise) and has its own per-session rate limit (`RATE_LIMIT_*` values, separate buckets from chat; 429). Body `{"level", "message", "timestamp"}`; control characters and newlines are replaced with spaces (no forged log lines) and the message is capped at 4000 characters. Lines are appended to `<repo>/logs/frontend.log` (`LOG_DIR` overrides the directory, as in `scripts/lib.sh`). The UI shim (`client/src/utils/remoteLog.js`) posts to the same-origin `/api/client-log` and sends nothing until a session token exists.

## Environment Variables

The shared template is the repo-root [`.env.example`](../.env.example). `super_agent/config.py` loads the repo-root `.env` without overriding variables already set.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GEMINI_MODEL` | yes | — | Router and suggestion model; startup fails when unset |
| `GOOGLE_API_KEY` | yes (or Vertex AI env) | — | Secret |
| `DATABASE_URL` | yes | — | `postgresql://user:pw@host:5432/db` (Cloud Run: `postgresql://user@/db?host=/cloudsql/<conn>` + `PGPASSWORD`) |
| `SESSION_DB_URL` | no | derived | Explicit `postgresql+asyncpg://` URL for ADK sessions |
| `SESSION_SECRET_KEY` | yes | — | Signs chat tokens; startup fails when unset (`start_local.sh` generates an ephemeral one) |
| `SESSION_TOKEN_EXPIRY_MIN` | no | `60` | Token lifetime |
| `AGENT_URL_<NAME>` | no | `http://localhost:82NN` | Base URL of each agent service, e.g. `AGENT_URL_ORDER_AGENT=http://order:8205`. Set by `start_local.sh`, `docker-compose.yml` and `deploy_cloud.sh` |
| `SERVICE_AUTH` | no | `none` | `gcp_id_token` on Cloud Run (ID tokens for agent calls) |
| `RUN_MIGRATIONS` | no | `false` | Apply `db/migrations` + seed on startup (the scripts and the `csa-db-init` job normally do this) |
| `SUGGESTIONS_ENABLED` | no | `true` | Generate follow-up suggestion chips after each turn |
| `DEBUG` | no | `false` | Enables `GET /api/debug/session` and FastAPI debug mode |
| `ALLOWED_ORIGINS` | no | `http://localhost:3000,http://localhost:5173` | CORS origins (comma-separated) |
| `RATE_LIMIT_RPM` / `RATE_LIMIT_RPH` / `RATE_LIMIT_BURST` | no | `20` / `200` / `5` | Per-session token bucket, **per gateway instance** |
| `AGENT_NAME` | no | `super_sales_agent` | ADK app name (session and memory scope) |
| `PORT` / `SERVER_PORT`, `SERVER_HOST` | no | `8000`, `0.0.0.0` | When running `python main.py` |
| `LOG_LEVEL` | no | `INFO` | |
| `LOG_DIR` | no | `<repo>/logs` | Directory of `frontend.log` (browser console forwarding) |
| `COMPACTION_*`, `CONTEXT_CACHE_*` | no | see `sales_common.config.ContextSettings` | Compaction and context-cache tuning |
| `SAFETY_*` | no | `BLOCK_LOW_AND_ABOVE` | Gemini safety thresholds |

## Running

The gateway needs PostgreSQL and the agent services. Normally start everything with the repo scripts:

```bash
scripts/setup_local.sh          # once
scripts/start_local.sh          # tools, agents, gateway :8000, UI :3000
scripts/stop_local.sh
```

Gateway only (agents already running, `.env` configured):

```bash
cd SuperAgent/server
uvicorn main:app --reload --port 8000
cd ../client && npm run dev     # UI on :3000, proxies /api to :8000
```

Smoke-run a few chat turns against a running gateway: `python SuperAgent/server/run_scenarios.py` (`GATEWAY_URL` overrides `http://localhost:8000`).

Docker: `docker build -f SuperAgent/Dockerfile -t csa-gateway .` from the repo root. The same image runs migrations (`python -m sales_common.migrate --seed`) for compose `db-init` and the Cloud Run job `csa-db-init`.

## Tests

```bash
pytest SuperAgent/tests -q                                             # no DB: pg-marked tests skipped
TEST_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_test pytest SuperAgent/tests -q
```

| Test file | Covers |
|---|---|
| `test_handoff_rules.py` | `evaluate_handoff()`, greeting detection, target normalization (pure, no LLM) |
| `test_workflow_run.py` | Full workflow turns with in-process fake agents and a scripted router (`tests/fakes.py`) |
| `test_sse.py` | Event → SSE mapping, de-duplication, card and cart payloads |
| `test_auth.py` | Token signing, expiry, tampering, revocation |
| `test_api.py` | Session and chat endpoints, `/api/client-log` (auth, sanitizing, rate limit, log path), `run_scenarios.py` against the app |

System-level tests: `tests/integration/` (all services as real processes with a scripted model) and `scripts/e2e_test.py` (real Gemini against a running stack).

## Adding a New Agent

1. Build the agent service per [../docs/agent-service-guide.md](../docs/agent-service-guide.md).
2. Add an `AgentSpec` to `super_agent/registry.py` (the workflow adds its node and edges automatically).
3. Add a row to `scripts/services.conf` and a block to `docker-compose.yml`.
4. Describe when to route to it in `ROUTER_INSTRUCTION` (`super_agent/prompts.py`).
5. Optional: add a deterministic handoff rule in `workflow.py` (`evaluate_handoff` + an edge from `handoff_policy`) with tests.
