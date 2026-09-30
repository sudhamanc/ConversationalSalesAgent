# Agent Service Guide (ADK 2.x + A2A + PostgreSQL)

This guide defines how every domain agent is built, served and tested after the ADK 2.x / A2A rewrite. It replaces the old "importlib isolation" pattern. Background decisions are in `openspec/changes/a2a-agent-services/design.md` and `openspec/changes/adk2-workflow-orchestration/design.md`.

## 1. Layout (ADK Bootstrap Template + server)

```text
OrderAgent/
├── pyproject.toml          # name "order-agent"; depends on "sales-common" (installed first)
├── Dockerfile              # build context = repo root
├── README.md / AGENTS.md
├── order_agent/
│   ├── __init__.py         # from .agent import root_agent, build_agent
│   ├── agent.py            # build_agent(model=None) -> Agent ; root_agent = build_agent()
│   ├── prompts.py          # domain prompt (static_instruction)
│   ├── tools/              # deterministic tools (plain functions / FunctionTool)
│   └── server.py           # app = create_a2a_app(root_agent)
└── tests/
    ├── conftest.py
    └── test_*.py
```

Rules:

- **Hardcoded agent names**, e.g. `order_agent`. The gateway routes by these names and the UI displays them.
- **No `load_dotenv()` in agent code.** Containers get env from compose or Cloud Run.
- **No `importlib` isolation, no `sys.modules[...]` lookups, and no imports of another agent's package.**
- **`GEMINI_MODEL` has no default.** `sales_common.config.model_name()` raises when it is unset.
- **Tools return JSON-serializable dicts** with explicit field names. Deterministic logic only; no LLM calls inside tools.
- **Do not swallow `BaseException` in tools.** ADK 2.x uses exceptions for retries and interrupts. Catch specific exceptions and return `{"success": false, "error": ...}`.

## 2. `agent.py` template

```python
from typing import Optional
from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import ORDER_AGENT_INSTRUCTION, ORDER_SHORT_DESCRIPTION
from .tools.cart_tools import add_to_cart, ...


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    return Agent(
        name="order_agent",
        model=model or model_name(),
        description=ORDER_SHORT_DESCRIPTION,
        static_instruction=ORDER_AGENT_INSTRUCTION,   # long, cacheable, NOT templated
        instruction=JOURNEY_CONTEXT_INSTRUCTION,       # short, templated from state
        tools=[add_to_cart, ...],
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        generate_content_config=generate_config(temperature=0.0, max_output_tokens=2048),
    )


root_agent = build_agent()
```

Callbacks accept lists. Agent-specific callbacks are appended after the shared ones. For `after_tool_callback`, the first callback that returns a truthy value wins, so an agent-specific callback that rewrites the response must merge `_context_update` itself or run first.

## 3. `server.py`

```python
from sales_common.a2a_server import create_a2a_app
from .agent import root_agent

app = create_a2a_app(root_agent)   # uses_database=False for agents without DB tools
```

Run with `uvicorn order_agent.server:app --host 0.0.0.0 --port $PORT`.

- `create_a2a_app` builds an ADK `App` with context compaction and context caching, `DatabaseSessionService` sessions, an a2a-sdk `DatabaseTaskStore`, and `GET /healthz`.
- The agent card is served at `/.well-known/agent-card.json` and advertises `PUBLIC_URL`.

## 4. Journey context (state across A2A)

- The gateway forwards `customer_context`, `serviceability_context`, `offer_context`, `order_context`, `payment_context`, a recent transcript, and the user profile in A2A request metadata.
- `import_forwarded_context` copies them into the agent's session state before it runs. Tools keep reading `tool_context.state["order_context"]`, and the templated `JOURNEY_CONTEXT_INSTRUCTION` shows them to the model.
- When a tool writes one of those keys (`tool_context.state["offer_context"] = {...}`), `export_context_delta` adds `_context_update` to the tool response. The gateway merges it into its session state.

## 5. Database access (PostgreSQL)

```python
from sales_common import db, notifications
from sales_common.repositories.quotes import mark_ordered

with db.transaction() as conn:                       # commit on success, rollback on error
    conn.execute("INSERT INTO orders (...) VALUES (%s, %s)", (a, b))
    row = conn.execute("SELECT * FROM orders WHERE order_id = %s", (oid,)).fetchone()  # dict row
    mark_ordered(offer_id, conn=conn)
    notifications.enqueue("order_confirmation", recipient_email=email, order_id=oid,
                          customer_id=cid, args={...template args...}, conn=conn)
```

SQLite → PostgreSQL translation:

| SQLite | PostgreSQL |
|---|---|
| `?` | `%s` (named: `%(name)s`) |
| `INSERT OR REPLACE` | `INSERT ... ON CONFLICT (pk) DO UPDATE SET ...` |
| `INSERT OR IGNORE` | `ON CONFLICT DO NOTHING` |
| `cursor.lastrowid` | `RETURNING id` |
| `PRAGMA ...`, `sqlite3.Row` | remove; rows are dicts |
| `datetime('now')` | pass `db.now_iso()` (timestamps are ISO TEXT) |

- **Quoting:** the `accounts` table uses quoted, case-sensitive columns `"Company Name"`, `"Industry"`, `"Street"`, `"City"`, `"State"`, `"Website"`, `"Existing Customer"`, and so on. Always double-quote them in SQL; unquoted `Street` folds to `street` and fails.
- **Schema:** lives in `db/migrations/*.sql`. Agents never create tables at runtime.
- **No fallbacks:** there are no silent in-memory fallbacks. If `DATABASE_URL` is unset, `sales_common.db` raises.

## 6. Notifications (outbox)

- Producers never call the communication agent. They call `sales_common.notifications.enqueue(...)` inside their business transaction.
- Supported types are in `sales_common.notifications.NOTIFICATION_TYPES`.
- `args` must contain everything the communication service needs to render the message (ids, names, amounts, dates).

## 7. Prompts

- Remove every instruction to `transfer_to_agent` or to hand off to a named peer agent. Agents cannot transfer; the gateway workflow routes each user turn and runs the deterministic handoffs (Discovery→Serviceability, Scheduling→Payment).
- Keep domain behaviour and output formats unchanged. The UI parses some formats, such as the order and payment JSON blocks and the serviceability key:value lines.

## 8. Tests

`tests/conftest.py`:

```python
import os
os.environ.setdefault("GEMINI_MODEL", "gemini-test")      # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
```

- Tool tests run against a scratch PostgreSQL database (`TEST_DATABASE_URL`) after `sales_common.migrate.run(seed=True)`. Skip them when `TEST_DATABASE_URL` is unset.
- Agent tests use `sales_common.testing.ScriptLlm` (scripted function calls and text) with an ADK `Runner` and an `InMemorySessionService`. No API key is needed.
- Run with `pytest <AgentDir>/tests -q`.

## 9. Dockerfile template

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8080
WORKDIR /app
COPY libs/sales_common /app/libs/sales_common
RUN pip install /app/libs/sales_common
COPY OrderAgent /app/OrderAgent
RUN pip install /app/OrderAgent
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn order_agent.server:app --host 0.0.0.0 --port ${PORT}"]
```

## 10. Environment variables (all agent services)

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_MODEL` | yes | e.g. `gemini-3-flash-preview` |
| `GOOGLE_API_KEY` | yes (or Vertex AI env) | secret |
| `DATABASE_URL` | yes | `postgresql://user:pw@host:5432/db`; sessions derive `postgresql+asyncpg://` (override `SESSION_DB_URL`) |
| `PUBLIC_URL` | yes | URL other services use to reach this agent (agent card) |
| `SERVICE_AUTH` | no | `none` (default) or `gcp_id_token` |
| `LOG_LEVEL` | no | default `INFO` |
| `COMPACTION_*`, `CONTEXT_CACHE_*` | no | see `sales_common.config.ContextSettings` |
