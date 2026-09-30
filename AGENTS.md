# Multi-Agent System Architecture

**B2B Conversational Sales Agent: ADK 2.x Workflow Orchestration over A2A Agent Services**

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [CLAUDE.md](CLAUDE.md)
   - This file (AGENTS.md)
   - Component-specific docs (e.g., `DiscoveryAgent/AGENTS.md`, `services/catalog/README.md`)
   - [README.md](README.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [.env.example](.env.example) and [SuperAgent/README.md](SuperAgent/README.md)
   - Agent development → [docs/agent-service-guide.md](docs/agent-service-guide.md) + the component's AGENTS.md
   - Orchestration, routing, handoffs → [SuperAgent/README.md](SuperAgent/README.md)
   - Tool services → `services/<name>/README.md`
   - Database → [db/README.md](db/README.md)
   - Deployment → [GCP_DEPLOY.md](GCP_DEPLOY.md)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

Design history and rationale for the current architecture live in `openspec/changes/`:

| Change | Status | Scope |
|---|---|---|
| `adk2-workflow-orchestration` | Implemented | ADK 2.10 `Workflow` root, deterministic handoffs, App compaction/caching, DB sessions, memory |
| `a2a-agent-services` | Implemented | One A2A service per agent, PostgreSQL, notification outbox, no importlib/`sys.modules` |
| `catalog-serviceability-mcp` | Implemented | Catalog and serviceability as REST + MCP services |
| `multi-service-scripts` | Implemented | `scripts/`, `docker-compose.yml`, per-service Dockerfiles, Cloud Run deployment |
| `mcp-remaining-domains` | **Planned (not implemented)** | REST + MCP services for CRM, pricing, orders, payments, fulfillment, notifications |

---

## System Architecture

### Multi-Agent System (MAS) Pattern

The system is a **gateway + independently deployed agent services** architecture on Google ADK 2.10:

- The **gateway** (`SuperAgent/`) hosts the React UI, the SSE chat API and the root ADK 2.x **`Workflow`** named `sales_journey`. The workflow classifies each user turn with a small router LLM, calls exactly one domain agent, and applies **deterministic handoff rules** in Python.
- Each of the **10 domain agents** is its own **A2A service** (its own process or container), called by the gateway through `RemoteA2aAgent`.
- **Deterministic tools** are either served by **REST + MCP tool services** (catalog, serviceability) or run in-process as plain function tools against **PostgreSQL**.

The architecture keeps a strict separation between autonomous reasoning (LLM-driven: intent classification and conversation) and deterministic execution (tools, SQL, workflow rules), so critical business data is never hallucinated.

```mermaid
graph TD
    UI["React 19 UI<br/>Vite dev server or built into the gateway image"] -->|HTTPS SSE /api/chat| GW
    subgraph GWBOX["Gateway :8000 - SuperAgent"]
        GW["FastAPI<br/>session tokens, rate limit, SSE mapping"] --> WF["sales_journey Workflow<br/>ADK App: compaction + context cache<br/>ContextBridgePlugin"]
    end
    WF -->|A2A JSON-RPC + journey metadata| AGENTS
    subgraph AGENTS["A2A agent services :8201-8210"]
        DISC["discovery_agent"]
        SVCA["serviceability_agent"]
        PROD["product_agent"]
        OFFER["offer_management_agent"]
        ORDER["order_agent"]
        PAY["payment_agent"]
        FUL["service_fulfillment_agent"]
        COMM["customer_communication_agent"]
        GREET["greeting_agent"]
        FAQ["faq_agent"]
    end
    SVCA -->|MCP streamable HTTP| SVCS["serviceability service :8102<br/>REST /api/v1 + MCP /mcp/"]
    PROD -->|MCP streamable HTTP| CAT["catalog service :8101<br/>REST /api/v1 + MCP /mcp/ + RAG"]
    GW -->|asyncpg + psycopg| PG[("PostgreSQL 16<br/>ADK sessions, memory, A2A tasks,<br/>business tables")]
    AGENTS -->|asyncpg sessions + psycopg tools| PG
    SVCS --> PG
    CAT --> PG
    WF -->|router LLM| GEM(("Gemini API"))
    AGENTS -->|agent LLM| GEM
```

Ports and names come from [`scripts/services.conf`](scripts/services.conf), the single service manifest used by every operations script.

### Agent Communication: A2A + Workflow

Agents never import or call each other. All communication goes through the gateway workflow:

1. **Gateway → agent (A2A).** Each domain node in `sales_journey` is a `RemoteA2aAgent` built by `sales_common.a2a_client.remote_agent()`. It fetches the agent card from `<AGENT_URL_*>/.well-known/agent-card.json` and sends A2A JSON-RPC requests.
   - **Message:** only a directed message is sent, not the gateway's whole history. The workflow writes it to the state key `a2a_outbound_message` (the user's text, or a synthetic handoff message) and the `context_builder` (`outbound_message_builder`) sends just that text.
   - **Context id:** the gateway session id is forwarded as the A2A context id, so each gateway session maps to one stable session per remote agent.
   - **Metadata:** the journey context (5 keys), a recent transcript and the user profile travel as A2A request metadata (`build_forwarded_metadata`).
2. **Agent side.** The shared `before_agent_callback` `sales_common.context.import_forwarded_context` copies the metadata into the agent's own session state, so tools keep reading `tool_context.state["order_context"]` and the templated `JOURNEY_CONTEXT_INSTRUCTION` shows the context to the model.
3. **Agent → gateway.** A2A carries message parts only; a remote `state_delta` is not returned. The shared `after_tool_callback` `export_context_delta` therefore appends `"_context_update": {key: value}` to a tool's response whenever the tool changed a journey key. `function_response` parts do cross A2A, and the gateway's `ContextBridgePlugin.on_event_callback` merges `_context_update` into the event's `state_delta` before the event is persisted.
4. **Deterministic handoffs.** `HandoffPolicyNode` reads the merged state and, when a rule matches, routes to the next agent within the same turn.

### Model Context Protocol (MCP)

MCP is used for **real network tool services**, not as a label for in-process functions:

| Tool service | Directory | MCP endpoint | REST | Consumer |
|---|---|---|---|---|
| Catalog | `services/catalog/` | `http://localhost:8101/mcp/` | `/api/v1/products...`, `/api/v1/knowledge/search` | `product_agent` (8 tools, incl. RAG `search_product_knowledge`) |
| Serviceability | `services/serviceability/` | `http://localhost:8102/mcp/` | `/api/v1/addresses/*`, `/api/v1/serviceability/check` | `serviceability_agent` (6 tools) |

- Servers use `mcp` 2.x `MCPServer`, mounted as stateless streamable HTTP with JSON responses. REST and MCP share one `core.py` per service.
- Agents connect with `sales_common.mcp_client.mcp_toolset(url)` (ADK `McpToolset` + `StreamableHTTPConnectionParams`, service-auth headers). URLs come from `CATALOG_MCP_URL` / `SERVICEABILITY_MCP_URL` and must end in `/mcp/`.
- The other six domain agents still run their tools in-process against PostgreSQL. Moving them behind REST + MCP is the planned change `mcp-remaining-domains`.

---

## Sub-Agent Registry

Every agent is an A2A service. The gateway's registry is `SuperAgent/super_agent/registry.py` (name, routing description, `AGENT_URL_<NAME>` with a localhost default).

| Agent (A2A name) | Location | Local port | `services.conf` name | Cloud Run service | Description |
|---|---|---|---|---|---|
| **Gateway** (`sales_journey`) | `SuperAgent/` | 8000 | `gateway` | `csa-gateway` | UI, SSE API, workflow router, handoffs, sessions, memory |
| `discovery_agent` | `DiscoveryAgent/discovery_agent/` | 8201 | `discovery` | `csa-agent-discovery` | Company lookup/registration, contacts, BANT qualification |
| `serviceability_agent` | `ServiceabilityAgent/serviceability_agent/` | 8202 | `serviceability-agent` | `csa-agent-serviceability` | Pre-sale address validation and coverage (MCP → serviceability service) |
| `product_agent` | `ProductAgent/product_agent/` | 8203 | `product` | `csa-agent-product` | Catalog, specs, comparisons, knowledge search; no pricing (MCP → catalog service) |
| `offer_management_agent` | `OfferManagement/offer_management/` | 8204 | `offer` | `csa-agent-offer` | Pricing, discounts, quotes (the only pricing source) |
| `order_agent` | `OrderAgent/order_agent/` | 8205 | `order` | `csa-agent-order` | Cart, orders, contracts, cancellations |
| `payment_agent` | `PaymentAgent/payment_agent/` | 8206 | `payment` | `csa-agent-payment` | Credit checks, payment methods, payment processing |
| `service_fulfillment_agent` | `ServiceFulfillmentAgent/service_fulfillment_agent/` | 8207 | `fulfillment` | `csa-agent-fulfillment` | Installation scheduling, provisioning, activation |
| `customer_communication_agent` | `CustomerCommunicationAgent/customer_communication_agent/` | 8208 | `communication` | `csa-agent-communication` | Notification history/sends; runs the outbox dispatcher |
| `greeting_agent` | `GreetingAgent/greeting_agent/` | 8209 | `greeting` | `csa-agent-greeting` | Greetings and phone script listing all products |
| `faq_agent` | `FAQAgent/faq_agent/` | 8210 | `faq` | `csa-agent-faq` | Policies, SLAs, contracts, general questions; router fallback |

| Tool service | Location | Local port | `services.conf` name | Cloud Run service |
|---|---|---|---|---|
| Catalog | `services/catalog/catalog_service/` | 8101 | `catalog` | `csa-catalog` |
| Serviceability | `services/serviceability/serviceability_service/` | 8102 | `serviceability` | `csa-serviceability` |

Shared runtime code lives in `libs/sales_common/sales_common/` (`config`, `db`, `migrate`, `context`, `adk_app`, `a2a_server`, `a2a_client`, `mcp_client`, `auth`, `memory`, `notifications`, `repositories`, `maintenance`, `testing`).

---

## Technical Stack

### Core Technologies

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **LLM** | Google Gemini | `GEMINI_MODEL` (e.g. `gemini-3-flash-preview`) | Intent routing, conversation |
| **Agent Framework** | Google ADK | `google-adk[a2a,mcp,db]==2.10.0` | `Workflow` graph, `App` (compaction, context cache), `DatabaseSessionService`, `to_a2a`, `RemoteA2aAgent`, `McpToolset` |
| **Agent protocol** | A2A (`a2a-sdk`) | 1.x | Agent cards, JSON-RPC, `DatabaseTaskStore` |
| **Tool protocol** | MCP (`mcp`) | `>=2.2,<3` (`MCPServer`) | Catalog and serviceability tool servers |
| **Backend** | Python + FastAPI / Starlette | 3.12 (images), FastAPI ≥ 0.115 | Gateway API, tool services, A2A apps |
| **Database** | PostgreSQL | 16 (Cloud SQL in GCP) | Business tables, ADK sessions, memory, A2A tasks |
| **DB drivers** | psycopg 3 (pool), SQLAlchemy 2.1 + asyncpg + greenlet | - | Sync tools; async ADK sessions and task store |
| **Session tokens** | itsdangerous | ≥ 2.2 | Signed, expiring chat tokens + revocation table |
| **RAG** | ChromaDB + sentence-transformers (`all-MiniLM-L6-v2`) | chromadb ≥ 1.0 | Product knowledge search (catalog service only) |
| **Frontend** | React + Vite + Tailwind CSS | React 19, Vite 6, Tailwind 3 | Chat UI with SSE streaming |
| **Deployment** | Docker Compose (local), Cloud Run + Cloud SQL (GCP) | - | One container per service |

### Model Configuration

- `GEMINI_MODEL` is **required** and has no default (`sales_common.config.model_name()` raises when unset).
- Temperatures: router 0.0 (≤ 256 output tokens); greeting and FAQ 0.7; service fulfillment 0.3; transactional agents 0.0.
- Safety thresholds from `SAFETY_*` env vars (`sales_common.config.safety_settings`).
- Long, stable prompts go in `static_instruction` (cache-friendly prefix); the short templated `instruction` carries journey context.

---

## The Golden Rule

**All agents MUST strictly follow ADK standards.** The full, authoritative rules and templates are in **[docs/agent-service-guide.md](docs/agent-service-guide.md)**. Summary:

### 1. ADK Bootstrap Template Structure + A2A server

```text
OrderAgent/
├── pyproject.toml          # depends on sales-common (installed first)
├── Dockerfile              # build context = repo root
├── README.md / AGENTS.md
├── order_agent/
│   ├── __init__.py         # from .agent import root_agent, build_agent
│   ├── agent.py            # build_agent(model=None) -> Agent ; root_agent = build_agent()
│   ├── prompts.py          # static_instruction + short description
│   ├── tools/              # deterministic tools
│   └── server.py           # app = create_a2a_app(root_agent)
└── tests/
```

### 2. ADK Agent Initialization Pattern

```python
def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    return Agent(
        name="order_agent",                          # hardcoded; the gateway routes by it
        model=model or model_name(),                 # GEMINI_MODEL, fail fast
        description=ORDER_SHORT_DESCRIPTION,
        static_instruction=ORDER_AGENT_INSTRUCTION,  # long, cacheable
        instruction=JOURNEY_CONTEXT_INSTRUCTION,     # templated from forwarded state
        tools=[add_to_cart, ...],
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        generate_content_config=generate_config(temperature=0.0, max_output_tokens=2048),
    )
```

`build_agent(model=...)` lets tests inject `sales_common.testing.ScriptLlm`.

### 3. Tool Definition Pattern

- **Shared, reusable, read-mostly tools** → a REST + MCP tool service under `services/<domain>/` (see the catalog and serviceability READMEs), consumed with `McpToolset`.
- **Agent-local tools** → plain Python functions (or `FunctionTool`) in `<agent>/tools/`, using `sales_common.db` for PostgreSQL.
- Either way: a clear docstring (it becomes the tool description), **JSON-serializable dict results with explicit field names**, deterministic logic only, no LLM calls inside tools.

### 4. A2A Service per Agent (replaces "Importlib Isolation")

- Every agent is served by `server.py` → `sales_common.a2a_server.create_a2a_app(root_agent)`, which provides an ADK `App` (compaction + context cache), `DatabaseSessionService` sessions, an a2a-sdk `DatabaseTaskStore`, the agent card at `/.well-known/agent-card.json` (advertising `PUBLIC_URL`) and `GET /healthz`.
- **No `importlib` isolation, no `sys.modules[...]` lookups, no imports of another agent's package.** Cross-domain effects go through the workflow (A2A), the notification outbox (`sales_common.notifications.enqueue`) or shared SQL helpers (`sales_common.repositories`).
- Agents do not call `transfer_to_agent` and prompts must not tell them to hand off to a named peer; the gateway workflow owns routing and handoffs.

### 5. Agent Naming

- A2A names are hardcoded snake_case ending in `_agent` (e.g. `offer_management_agent`). The same name appears in `registry.py`, the `a2a_name` column of `scripts/services.conf`, the router prompt and the UI.
- The gateway env var for an agent is `AGENT_URL_<A2A_NAME_UPPER>` (e.g. `AGENT_URL_ORDER_AGENT`).

### 6. Configuration Management

- Configuration comes from environment variables only. Agent code never calls `load_dotenv()`; `scripts/start_local.sh`, Docker Compose (`env_file: .env`) or Cloud Run provide the environment. The gateway loads the root `.env` for local convenience without overriding set variables.
- Use `sales_common.config` helpers (`require_env`, `env_int`, `model_name`, `ContextSettings.from_env`). Critical values fail fast; there are no silent fallbacks (e.g. `sales_common.db` raises when `DATABASE_URL` is unset).
- The shared variable reference is [.env.example](.env.example); gateway variables are in [SuperAgent/README.md](SuperAgent/README.md).

### 7. Logging Standards

```python
import logging
logger = logging.getLogger("order_agent.tools")

logger.info("Order %s created for %s", order_id, customer_id)
logger.warning("Memory search failed: %s", type(exc).__name__)   # no secrets, no raw payloads
```

- Services call `sales_common.logging.setup_logging(name)`; `LOG_LEVEL` controls verbosity. Database URLs are logged via `mask_url()`.
- Local logs: `logs/<service>.log` (written by `scripts/start_local.sh`). Cloud: Cloud Logging per Cloud Run service.

### 8. Error Handling Pattern

```python
try:
    with db.transaction() as conn:
        ...
except psycopg.Error as exc:
    logger.error("create_order failed: %s", type(exc).__name__)
    return {"success": False, "error": "Order could not be saved. Please try again."}
```

- Catch **specific** exceptions and return `{"success": false, "error": ...}`. **Never swallow `BaseException`**: ADK 2.x uses exceptions for retries and interrupts.
- The gateway retries retryable model errors (503/429) before any domain event is seen and otherwise streams a user-friendly `error` SSE event naming the unavailable service.

### 9. Testing Requirements

Every service MUST include:

- **Tool tests** against a scratch PostgreSQL database (`TEST_DATABASE_URL`, after `sales_common.migrate.run(seed=True)`), skipped when unset.
- **Agent tests** with `sales_common.testing.ScriptLlm` (scripted function calls and text) and an in-memory ADK `Runner`; no API key needed.
- **Gateway tests** (`SuperAgent/tests/`): handoff rules, workflow runs with in-process fake agents, SSE mapping, auth, API.
- **Integration tests** (`tests/integration/test_local_stack.py`): real processes for all 13 services, real A2A, real MCP, real PostgreSQL, and a scripted `fake-sales` model.
- **E2E** against a running stack: `python scripts/e2e_test.py --base-url http://127.0.0.1:8000` (real Gemini).
- Scenario coverage per [Scenarios.md](Scenarios.md).

```bash
pytest OrderAgent/tests -q
TEST_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_test pytest SuperAgent/tests libs/sales_common/tests -q
TEST_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_test venv/bin/python -m pytest tests/integration -q -s
```

---

## Agent Interaction Flow

### Current Implementation: Workflow Graph + Deterministic Handoffs

The root of the gateway is the ADK 2.x `Workflow` `sales_journey` (`SuperAgent/super_agent/workflow.py`), wrapped in an `App` (`SuperAgent/super_agent/agent.py`):

```mermaid
graph TD
    START(["START"]) --> PREP["prepare_turn<br/>record turn, search memory,<br/>build router input"]
    PREP -->|fast: pure greeting| DISPATCH
    PREP -->|llm| ROUTER["route_intent<br/>LlmAgent single_turn<br/>output_schema RouteDecision"]
    ROUTER --> DISPATCH["dispatch<br/>validate target, fallback faq_agent,<br/>write a2a_outbound_message"]
    DISPATCH -->|route by agent name| AGENTS["10 RemoteA2aAgent nodes"]
    AGENTS --> HANDOFF["HandoffPolicyNode<br/>custom Node, max 2 hops"]
    HANDOFF -->|serviceability_agent| AGENTS
    HANDOFF -->|payment_agent| AGENTS
    HANDOFF -->|end| FINISH["finish_turn<br/>persist user: profile keys"]
```

| Node | Kind | Responsibility |
|---|---|---|
| `prepare_turn` | function node | Stores `turn_user_message`, resets `handoff_hops`, appends to `transcript`. Pure greetings take the **fast path** to `greeting_agent` (no LLM). Otherwise searches memory and builds a compact router input: message, `last_agent`, last reply excerpt (≤ 400 chars), journey flags, company name, memories. |
| `route_intent` | `LlmAgent` (`mode="single_turn"`, `include_contents="none"`, temperature 0) | Returns `RouteDecision{target, reason}`. Routing rules are in `SuperAgent/super_agent/prompts.py` (`ROUTER_INSTRUCTION`). |
| `dispatch` | function node | Validates the target against the registry (unknown → `faq_agent`), writes `last_agent` and `a2a_outbound_message`, routes to that agent node. |
| agent nodes | `RemoteA2aAgent` × 10 | Run the domain agent as a remote A2A call. |
| `handoff_policy` | `HandoffPolicyNode(Node)` | Applies `evaluate_handoff()` rules; appends the reply to the transcript; routes to the next agent or `end`. |
| `finish_turn` | function node | Writes `user:customer_id` / `user:company_name` for returning visitors. |

**Deterministic handoffs (same turn, no extra user message):**

| From | To | Condition | Message sent to the target |
|---|---|---|---|
| `discovery_agent` | `serviceability_agent` | `customer_context` has a `customer_id` and an address `zip_code`, and serviceability was not yet checked for that ZIP | `Check service availability for this address: {street, city, state, zip_code}` (JSON) |
| `service_fulfillment_agent` | `payment_agent` | `ContextBridgePlugin` saw a successful `schedule_installation` (`appointment_confirmed_order`), payment is not completed/approved/captured, and the order status is `pending_payment`, `draft` or empty | `Installation is scheduled for order <id>; total <amount>. Start payment: ...` |

At most **2 handoff hops** per turn (`MAX_HANDOFF_HOPS`). Rules are pure functions and unit-tested without an LLM (`SuperAgent/tests/test_handoff_rules.py`).

This replaces the ADK 1.x design (LLM coordinator with `sub_agents`, three `after_agent_callback` handoff hacks and a synthetic server-side "Proceed to payment" re-run).

### State, Sessions, Memory and Context Features

| ADK feature | How it is used |
|---|---|
| **Sessions** | `DatabaseSessionService` on PostgreSQL (`postgresql+asyncpg://`, derived from `DATABASE_URL` or `SESSION_DB_URL`) in the gateway and in every agent service. Sessions survive restarts and work across instances. |
| **State** | Session scope: `customer_context`, `serviceability_context`, `offer_context`, `order_context`, `payment_context`, plus `last_agent`, `last_reply`, `transcript`, `turn_user_message`, `handoff_hops`, `a2a_outbound_message`, `appointment_confirmed_order`. User scope: `user:customer_id`, `user:company_name`. |
| **Events** | The SSE API maps workflow events to UI events (`token`, `activity_update`, `structured_card`, `cart_update`, `suggestions`, `done`, `error`). Only domain-agent events produce text; repeated final texts are de-duplicated. |
| **Memory** | `sales_common.memory.PostgresMemoryService` (table `adk_memories`, PostgreSQL full-text search, always scoped by app and user). The session is added to memory after each turn; `prepare_turn` searches it for routing context. |
| **Context compression** | `EventsCompactionConfig`: every 8 invocations with overlap 2, or above 60k tokens keeping 10 events (`COMPACTION_*`). |
| **Model context caching** | `ContextCacheConfig`: TTL 1800 s, refresh every 10 invocations, min 4096 tokens (`CONTEXT_CACHE_*`). |
| **Conversational context** | `static_instruction` prompts, `{customer_context?}`-style templating from forwarded state, and a forwarded recent transcript for agents that do not see other agents' turns. |

### Structured JSON Tool Outputs (zero-hallucination strategy)

**Problem identified (Feb 2026):** when data moved between agents as formatted text, Gemini occasionally rephrased it and changed critical values:

```
DiscoveryAgent tool returns: "123 Main Street, Philadelphia, PA 19103"
→ passed on as: "123 Main Street, Philadelphia, PA 19106"   (zip code changed)
```

**Solution:** every tool returns **JSON with explicit field names**, and exact values travel as structured state rather than prose:

```python
# ❌ BEFORE (formatted text, prone to rephrasing)
return f"Company: {name}\nAddress: {street}, {city}, {state} {zip_code}"

# ✅ AFTER (structured dict)
return {
    "company_name": name,
    "address": {"street": street, "city": city, "state": state, "zip_code": zip_code},
}
```

In the current architecture this is enforced end to end:

- Tools write authoritative facts to journey keys (`tool_context.state["customer_context"] = {...}`); `export_context_delta` ships them to the gateway as `_context_update`.
- Handoff messages are built by `HandoffPolicyNode` from state (e.g. the address JSON for serviceability), never from the previous agent's prose.
- MCP tool results are JSON objects (`structuredContent`).

**Key learnings (still valid):**

- LLM-to-LLM transfer is unreliable for exact values (addresses, numbers, codes).
- Tools should return machine-readable formats even when consumed by an LLM.
- Deterministic code, not prompts, should decide when a mandatory next step happens.

| Challenge | Solution | Mechanism |
|---|---|---|
| Agent handoff timing | Deterministic handoff rules | `HandoffPolicyNode` evaluates merged journey state |
| Data corruption across turns and agents | Structured JSON + journey state | Tools write state; `_context_update` + A2A metadata carry it |
| User flexibility | LLM intent routing | `route_intent` with last agent, last reply, journey flags and memories |
| Zero-hallucination compliance | Deterministic tools | Pricing only from `offer_management_agent`; catalog never discloses prices |

### Typical Sales Conversation Flow

```mermaid
sequenceDiagram
    participant Customer
    participant Gateway as Gateway sales_journey
    participant Greeting
    participant Discovery
    participant Serviceability
    participant Product
    participant Offer as OfferManagement
    participant Order
    participant Fulfillment as ServiceFulfillment
    participant Payment

    Customer->>Gateway: Hi
    Gateway->>Greeting: fast path, no router call
    Greeting-->>Customer: Phone script listing products

    Customer->>Gateway: We are VoiceStream Networks at 123 Main St, Boston
    Gateway->>Discovery: router selects discovery_agent
    Discovery-->>Gateway: company registered, customer_context via _context_update
    Gateway->>Serviceability: HandoffPolicyNode, same turn
    Serviceability-->>Customer: Serviceable, Fiber 1G 5G 10G

    Customer->>Gateway: Compare Fiber 1G and 5G
    Gateway->>Product: MCP tools on catalog service
    Product-->>Customer: Specs, no pricing

    Customer->>Gateway: Quote Fiber 5G plus SD-WAN
    Gateway->>Offer: router selects offer_management_agent
    Offer-->>Customer: Quote card with offer_id and totals

    Customer->>Gateway: Proceed with this quote
    Gateway->>Order: cart and order, status pending_payment
    Order-->>Customer: Order created

    Customer->>Gateway: Schedule installation tomorrow morning
    Gateway->>Fulfillment: schedule_installation
    Fulfillment-->>Gateway: success, appointment_confirmed_order set by ContextBridgePlugin
    Gateway->>Payment: HandoffPolicyNode, same turn
    Payment-->>Customer: Asks for payment method
```

Each `Customer->>Gateway` arrow is a separate user turn. Notifications (order confirmation, payment receipt, installation reminders) are written to the outbox by the producing agent and delivered by the communication service.

### Routing Decision Tree

The router prompt (`ROUTER_INSTRUCTION`) classifies intent in this priority order; the workflow then calls exactly one agent:

1. **Company/business identification** → `discovery_agent`
2. **Address validation / coverage** → `serviceability_agent` (also reached automatically after discovery)
3. **Product catalog and technical fit** (no pricing) → `product_agent`
4. **Pricing, discounts, quotes** → `offer_management_agent`
5. **Cart, order, contract, cancellation** → `order_agent`
6. **Payment, credit check** → `payment_agent` (also reached automatically after scheduling)
7. **Installation scheduling and activation** → `service_fulfillment_agent`
8. **Notifications and notification history** → `customer_communication_agent`
9. **Greetings** → `greeting_agent` (pure greetings bypass the router)
10. **Policies, SLAs, support, anything else** → `faq_agent` (also the fallback for invalid router output)

---

## Deployment Architecture

### Local Development

| Option | Command | Notes |
|---|---|---|
| Native processes | `scripts/setup_local.sh` then `scripts/start_local.sh` | Needs a PostgreSQL 16 at `DATABASE_URL`. Runs migrations + seed, starts tools, agents, gateway (`:8000`) and the Vite UI (`:3000`). Logs in `logs/<name>.log`; stop with `scripts/stop_local.sh`. |
| Containers | `docker compose up --build` | PostgreSQL 16, one-shot `db-init`, 2 tool services, 10 agents, gateway on a private network; only the gateway is published (`http://localhost:8000` serves UI + API). |
| Database ops | `scripts/db.sh migrate`, `seed`, `reset --yes` | `reset` refuses non-local hosts unless `--allow-remote`. |

### Google Cloud

13 Cloud Run services (gateway public; agents and tool services private, called with Google-signed ID tokens), one Cloud Run job (`csa-db-init`) for migrations + seed, Cloud SQL for PostgreSQL 16, Secret Manager and Artifact Registry. Managed by `scripts/setup_gcp.sh`, `scripts/deploy_cloud.sh`, `scripts/start_cloud.sh` and `scripts/shutdown_cloud.sh`. See [GCP_DEPLOY.md](GCP_DEPLOY.md).

### Production Considerations (Future)

- Per-domain REST + MCP services and single-writer table ownership (`mcp-remaining-domains`), then per-service databases.
- Shared rate limiting (currently an in-memory token bucket per gateway instance).
- OpenTelemetry tracing across gateway → A2A → MCP hops.
- Terraform / CI/CD pipelines (scripts use `gcloud` today).

---

## Key Architectural Decisions

### Why a Workflow Graph Instead of an LLM Coordinator?

- An ADK coordinator `LlmAgent` with `sub_agents` is **sticky**: after `transfer_to_agent`, later user turns go straight to the sub-agent until it transfers back. A **remote A2A agent cannot transfer back** to the gateway, so a coordinator over `RemoteA2aAgent` sub-agents would get stuck on the first remote agent.
- The workflow routes **every turn** afresh, so the conversation can move freely between agents.
- Business-mandatory steps (Discovery → Serviceability, Scheduling → Payment) are **deterministic Python rules**, not prompt instructions or callback hacks. LLM judgment is used only for intent classification.
- The same graph runs with in-process fake agents (tests) and `RemoteA2aAgent` nodes (deployment).
- `HandoffPolicyNode` subclasses `google.adk.workflow.Node`, the supported 2.x extension point (1.x `BaseAgent._run_async_impl` custom agents are bypassed by the graph engine; `SequentialAgent`/`LoopAgent` are deprecated).

### Why the Context Bridge?

- A2A carries **message parts only**: local `session.state` is not sent and the remote `state_delta` is not returned.
- Forwarding the journey context as request metadata (in) and `_context_update` inside tool responses (out) keeps every agent's tools and prompts working on the same structured state, without coupling agents to a gateway-owned table.
- `ContextBridgePlugin.on_event_callback` merges updates **before the event is persisted**, so `HandoffPolicyNode` sees them in the same turn.

### Why A2A Services Instead of Importlib Isolation?

- The old design loaded ten agents into one process via `importlib` wrappers and `sys.modules` cross-calls: one monolithic image, one Cloud Run instance, silent failures when a module was missing.
- Each agent is now deployable and scalable on its own, owns its sessions, and is discoverable through its agent card. Cross-domain side effects use the notification outbox and shared SQL repositories instead of in-process calls.

### Why REST + MCP Tool Services?

- One source of truth for the 16 SKUs and coverage data (previously duplicated dicts in three agents).
- The same `core.py` serves agents (MCP) and other systems (REST); changing data no longer means redeploying an LLM agent.
- The product agent image no longer bundles PyTorch or the embedding model; only the catalog service does.

### Why PostgreSQL?

- Durable ADK sessions, memory and A2A tasks shared by many instances; business tables with versioned migrations (`db/migrations`) and idempotent seed files (`db/seed`).
- Cloud SQL in GCP and a `postgres:16` container locally keep environments symmetric. SQLite and the GCS database sync were retired.

### Why ADK Over LangChain/LlamaIndex?

| Feature | ADK | LangChain | Decision |
|---|---|---|---|
| Multi-agent orchestration | ✅ Native graph workflows + A2A | ⚠️ Via LangGraph | ADK built for multi-agent |
| Google Gemini integration | ✅ First-class (context caching) | ➖ Generic | Optimized for Gemini |
| Protocols | ✅ A2A + MCP built in | ➖ Adapters | ADK advantage |
| Learning curve | ⚠️ Newer docs | ✅ Mature | Acceptable trade-off |

---

## Security & Compliance

### Data Privacy (Academic Demo)

- ✅ Mock customer data only (no real PII)
- ✅ Secrets in `.env` locally (never committed) and Secret Manager in GCP
- ⚠️ Production requires: encryption at rest/transit review, PII anonymization

### Service and Session Security

- Chat session tokens are signed with `SESSION_SECRET_KEY` (itsdangerous, expiring); revocation is stored in `revoked_sessions`.
- Service-to-service calls on Cloud Run use Google-signed ID tokens (`SERVICE_AUTH=gcp_id_token`); only `csa-gateway` may invoke agents and only `csa-agents` may invoke tool services.

### Payment Security

- ⚠️ **NOT PCI-DSS compliant** (demo only). The payment agent includes idempotency keys, a payment state machine, an append-only `payment_events` audit trail and per-customer rate limiting.

### LLM Safety

- Pricing only from deterministic offer tools; the catalog service never returns prices.
- Safety thresholds via `SAFETY_*` env vars.

---

## Observability & Debugging

- `LOG_LEVEL=DEBUG` for verbose logs. Per-service local logs: `tail -f logs/gateway.log logs/order.log`.
- **Delegation audit trail:** `ContextBridgePlugin` logs one `delegation author=<agent> tool=<tool> success=<bool> session=<id>` line per remote tool call and a `context_update keys=[...]` line per merge; the workflow logs `Routing turn to <agent>` and `Handoff <from> -> <to> (hop n)`.
- `DEBUG=true` enables `GET /api/debug/session` on the gateway (your own session's ADK state).
- Health: gateway `GET /health` and `/healthz`; every agent and tool service `GET /healthz`; agent cards at `/.well-known/agent-card.json`.

---

## Development Workflow

### Adding a New Agent

1. **Create the service** following [docs/agent-service-guide.md](docs/agent-service-guide.md): `NewAgent/pyproject.toml`, `new_agent/{__init__,agent,prompts,server}.py`, `tools/`, `tests/`, `Dockerfile` (build context = repo root).
2. **Register it in the gateway:** add an `AgentSpec("new_agent", "<routing description>", "http://localhost:82NN")` to `SuperAgent/super_agent/registry.py`. `build_workflow` adds the node and its edges from the registry.
3. **Add a row to `scripts/services.conf`** (`name|dir|module|port|agent|csa-agent-<name>|new_agent|<mcp deps>`) so `setup_local.sh`, `start_local.sh`, `stop_local.sh` and `deploy_cloud.sh` pick it up (the gateway gets `AGENT_URL_NEW_AGENT` automatically), and add a matching block to `docker-compose.yml`.
4. **Update the router prompt** (`ROUTER_INSTRUCTION` in `SuperAgent/super_agent/prompts.py`) with when to choose `new_agent`.
5. **Handoffs (optional):** add a rule to `evaluate_handoff()` and an edge from `handoff_policy` in `build_workflow`, with tests in `SuperAgent/tests/test_handoff_rules.py`.
6. **Tests + docs:** agent tests, gateway tests, the agent's `AGENTS.md`/`README.md`, and this file's registry.

### Adding a Tool Service

Follow `services/catalog/` or `services/serviceability/`: `core.py` shared by FastAPI routers (`/api/v1`) and an `MCPServer` mounted at `/mcp/` (stateless HTTP, `host="0.0.0.0"`), a `tool` row in `scripts/services.conf`, and an `ENV_VAR=<service>` entry in the consuming agent's `mcp_deps` column.

### Modifying Agent Instructions

- Domain prompts: `<agent>/prompts.py` (`static_instruction`). Routing rules: `SuperAgent/super_agent/prompts.py`.
- Keep output formats the UI parses (order/payment JSON blocks, serviceability key:value lines).
- Restart just that service: `scripts/stop_local.sh --only order && scripts/start_local.sh --only order --skip-migrate --no-ui`.

---

## Project TODOs

**Done in the ADK 2.x / A2A rewrite:**

- ✅ Persistent quotes, carts, orders and pending carts (PostgreSQL tables `quotes`, `carts`, `cart_items`, `orders`, `order_items`).
- ✅ `customer_master` written after successful activation.
- ✅ Typed SSE events from tool responses (`activity_update`, `cart_update`, `structured_card` for quotes) instead of relying only on prose parsing.
- ✅ Durable sessions, long-term memory, compaction and context caching.
- ✅ Deterministic handoffs; removal of `after_agent_callback` hacks, the synthetic payment re-run, importlib wrappers and `sys.modules` cross-calls.
- ✅ Catalog and serviceability as REST + MCP services; multi-service scripts and Cloud Run deployment.

**Remaining:**

1. **`mcp-remaining-domains`** (planned): REST + MCP services for CRM, pricing, orders, payments, fulfillment and notifications, with single-writer table ownership; OfferManagement reads prices from the catalog service instead of its own price book.
2. **Known domain bugs:** all fixed with regression tests (see README "Recent Fixes and Known Limitations"). Residual limitations are listed in each agent's `AGENTS.md` under "Known issues".
3. **Structured UI contracts:** extend `structured_card` to serviceability, product and order results so `responseFormatters.js` becomes a fallback only.
4. **Rate limiting** is per gateway instance (in-memory token bucket); move to a shared store for multi-instance deployments.
5. **Known environment limitations:** the RAG embedding model download is blocked in the build sandbox (the catalog service then reports `available: false` for knowledge search); Docker images were not built in the sandbox (run `docker compose build` / `scripts/deploy_cloud.sh` yourself).
6. Per-service databases and IaC (Terraform) once table ownership is single-writer.

---

## References

- **Project README:** [README.md](README.md)
- **Agent Service Guide:** [docs/agent-service-guide.md](docs/agent-service-guide.md)
- **Gateway:** [SuperAgent/README.md](SuperAgent/README.md)
- **Database:** [db/README.md](db/README.md)
- **Tool services:** [services/catalog/README.md](services/catalog/README.md), [services/serviceability/README.md](services/serviceability/README.md)
- **Deployment:** [GCP_DEPLOY.md](GCP_DEPLOY.md)
- **Design changes:** `openspec/changes/`
- **Test Scenarios:** [Scenarios.md](Scenarios.md)
- **Google ADK Docs:** <https://google.github.io/adk-docs/>
- **A2A Protocol:** <https://a2a-protocol.org/>
- **Model Context Protocol:** <https://modelcontextprotocol.io/>
- **Gemini API:** <https://ai.google.dev/gemini-api/docs>
