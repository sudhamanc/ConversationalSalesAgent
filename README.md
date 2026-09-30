# B2B Conversational Sales Agent

A multi-agent system for end-to-end B2B telecom sales conversations, built on Google ADK 2.x with Gemini: an orchestration **workflow** in a gateway, **10 domain agents as independent A2A services**, and **REST + MCP tool services**, all backed by PostgreSQL.

**Drexel University – Senior Design Project — Winter/Spring 2026**

---

## What This Project Is

This repository implements a **multi-agent system** that automates the full B2B telecom sales lifecycle, from prospect discovery through order fulfillment. A **gateway** (`SuperAgent/`) runs an ADK 2.x `Workflow` that routes each customer turn to one of 10 specialized agents. Each agent is its own **A2A (Agent2Agent) service**, deployable and scalable on its own.

Built on **Google ADK 2.10 (Agent Development Kit)** with **Google Gemini**, the system enforces a strict separation between:

- **LLM-driven reasoning:** intent classification and natural-language conversation
- **Deterministic execution:** database lookups, pricing, address validation, payment processing, and the business-mandatory handoffs between agents

The LLM decides *what* the customer wants; critical business data (addresses, prices, orders) always comes from deterministic tools, never from generated text.

---

## Architecture

```mermaid
graph TD
    USER["Browser<br/>React 19 UI"] -->|HTTPS SSE| GW["Gateway :8000<br/>FastAPI + sales_journey Workflow"]
    GW -->|A2A JSON-RPC| AG["10 agent services :8201-8210<br/>ADK agents served with to_a2a"]
    AG -->|MCP streamable HTTP| TS["Tool services<br/>catalog :8101, serviceability :8102<br/>REST /api/v1 + MCP /mcp/"]
    GW --> PG[("PostgreSQL 16<br/>sessions, memory, A2A tasks,<br/>business tables")]
    AG --> PG
    TS --> PG
    GW -->|router| GEM(("Gemini API"))
    AG -->|agents| GEM
```

```
User → React UI → Gateway (FastAPI → ADK Runner → sales_journey Workflow)
     → RemoteA2aAgent → Agent service (ADK agent → tools / MCP) → PostgreSQL
```

Responses stream back to the browser via Server-Sent Events (SSE). A per-service overview with the full node graph is in [AGENTS.md](AGENTS.md#system-architecture).

> `architecture-diagram.png` and `architecture.html` show the earlier single-process (ADK 1.x) architecture and are kept for presentation history.

### Architectural Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  PRESENTATION    React 19 + Vite + Tailwind  ⇄  FastAPI SSE gateway │
├─────────────────────────────────────────────────────────────────────┤
│  ORCHESTRATION   sales_journey Workflow: router LLM, dispatch,      │
│                  deterministic handoffs, sessions, memory           │
├──────────────┬───────────────────┬──────────────────────────────────┤
│ DISCOVERY    │ CONFIGURATION     │ TRANSACTION    (A2A services)    │
│ Discovery    │ Serviceability    │ Order · Payment · Fulfillment    │
│ Greeting     │ Product           │ Customer Communication           │
│ FAQ          │ Offer Management  │                                  │
├──────────────┴───────────────────┴──────────────────────────────────┤
│  TOOL SERVICES   catalog: REST+MCP+RAG · serviceability: REST+MCP   │
├─────────────────────────────────────────────────────────────────────┤
│  DATA            PostgreSQL 16 (Cloud SQL in GCP) · SMTP · Gemini   │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Separation of concerns** | Each agent owns one domain and runs as its own service |
| **Zero-hallucination for critical data** | Addresses, prices, orders always come from deterministic tools |
| **Router-only orchestrator** | The gateway classifies intent and dispatches; it never writes customer-facing domain answers |
| **Deterministic handoffs** | Mandatory next steps (Discovery → Serviceability, Scheduling → Payment) are Python rules in the workflow |
| **Temperature-stratified agents** | Greeting/FAQ 0.7; transactional agents and the router 0.0 |
| **Structured data contracts** | Tools return JSON (not prose) to prevent LLM rephrasing of critical values |
| **Shared journey-state contracts** | Agents publish authoritative context into ADK session state; it crosses the A2A boundary through metadata and `_context_update` |
| **A2A service per agent** | No in-process coupling: no `importlib` loading or `sys.modules` calls between agents (see [docs/agent-service-guide.md](docs/agent-service-guide.md)) |

### How Agents Communicate

```
User message → Gateway workflow (sales_journey)
                 │
                 ├─ prepare_turn → route_intent (router LLM, RouteDecision)
                 │     pure greetings skip the router (fast path)
                 │
                 ├─ dispatch → RemoteA2aAgent("<agent>")  ── A2A JSON-RPC ──►  agent service
                 │     sends: directed message (a2a_outbound_message)
                 │            + metadata: journey context, transcript, user profile
                 │
                 ├─ agent tools change journey keys → "_context_update" in tool responses
                 │     ContextBridgePlugin merges them into gateway session state
                 │
                 └─ HandoffPolicyNode (deterministic, same turn, ≤ 2 hops)
                       discovery_agent           → serviceability_agent
                       service_fulfillment_agent → payment_agent
```

- **Gateway → agent** is A2A. Each domain node in the workflow is a `RemoteA2aAgent` that fetches the agent's card (`/.well-known/agent-card.json`) and sends only the directed message for that agent, with the gateway session id as the A2A context id.
- **Shared journey state is the data plane.** The five journey keys (`customer_context`, `serviceability_context`, `offer_context`, `order_context`, `payment_context`) travel to the agent as A2A request metadata. `import_forwarded_context` (a `before_agent_callback`) copies them into the agent's session state so its tools and templated instructions can use them.
- **Agent → gateway.** A2A does not return remote state changes, so `export_context_delta` (an `after_tool_callback`) adds `_context_update` to a tool's response. The gateway's `ContextBridgePlugin` merges it into the session before the handoff node runs.
- **Deterministic handoffs.** `HandoffPolicyNode` checks the merged state after each agent and routes to the next agent within the same turn. This replaces the former `after_agent_callback` transfers and the synthetic "Proceed to payment" re-run.
- **Cross-domain side effects** do not call other agents. Notifications are written to a transactional **outbox** (`notifications` rows with `status='pending'`) that the customer communication service dispatches; quote status updates and customer-state lookups use shared SQL helpers (`sales_common.repositories`).

### Session State, Sessions and Memory

The system uses **ADK session state as a shared, structured memory layer** across the sales journey. It is a deliberate contract for moving exact business facts between agents without re-parsing free-form conversation.

| Scope | Keys | Written by |
|---|---|---|
| Session (journey) | `customer_context` | discovery tools after registration or lookup |
| | `serviceability_context` | serviceability agent callback after a coverage check |
| | `offer_context` | offer management tools after a quote |
| | `order_context` | order tools after order creation |
| | `payment_context` | payment tools after processing |
| Session (workflow) | `last_agent`, `last_reply`, `transcript`, `turn_user_message`, `handoff_hops`, `a2a_outbound_message`, `appointment_confirmed_order` | gateway workflow nodes and `ContextBridgePlugin` |
| User (`user:`) | `user:customer_id`, `user:company_name` | `finish_turn`, so a returning browser is recognized in a new session |

- **Sessions** are durable: ADK `DatabaseSessionService` on PostgreSQL in the gateway and in every agent service. They survive restarts and are shared by all instances.
- **Identity:** the browser generates an anonymous `csa_uid` (UUIDv4); the ADK user id is `web:<uuid>`. Chat tokens are signed with `SESSION_SECRET_KEY` and can be revoked.
- **Long-term memory:** `sales_common.memory.PostgresMemoryService` stores user and agent turns in `adk_memories` (PostgreSQL full-text search, scoped per app and user). The session is saved to memory after each turn, and relevant memories are given to the router.
- **Context management:** every ADK `App` uses events compaction (every 8 invocations with overlap 2, or above 60k tokens) and Gemini context caching (TTL 30 min, min 4096 tokens).

**Why:** exact values (zip codes, order ids, offer ids, transaction ids) are never regenerated from conversation text; multi-turn steps (payment, scheduling, activation) resume from state; retries and restarts are safe; and each state write is observable in logs.

---

## Agent Architecture

### Gateway Workflow and Agent Services

```
                        ┌───────────────────────────────┐
                        │  Gateway (SuperAgent)          │
                        │  sales_journey Workflow        │
                        │  • route_intent (router LLM)   │
                        │  • dispatch                    │
                        │  • HandoffPolicyNode           │
                        │  • sessions + memory           │
                        └───────────────┬───────────────┘
                                        │ A2A
         ┌──────────────────────────────┼──────────────────────────────┐
         │                              │                              │
┌────────▼─────────┐        ┌───────────▼────────────┐       ┌─────────▼──────────────┐
│ DISCOVERY        │        │ CONFIGURATION          │       │ TRANSACTION            │
├──────────────────┤        ├────────────────────────┤       ├────────────────────────┤
│ greeting_agent   │        │ serviceability_agent   │       │ order_agent            │
│ discovery_agent  │        │   └ MCP: serviceability│       │ payment_agent          │
│ faq_agent        │        │ product_agent          │       │ service_fulfillment_   │
│                  │        │   └ MCP: catalog + RAG │       │   agent                │
│                  │        │ offer_management_agent │       │ customer_communication_│
│                  │        │                        │       │   agent (outbox)       │
└──────────────────┘        └────────────────────────┘       └────────────────────────┘
```

### Agent Registry

| Agent (A2A name) | Directory | Port | Cluster | Tables owned | Tools / infrastructure |
|-------|---------|------|---------|----------------|----------------|
| Gateway (`sales_journey`) | `SuperAgent/` | 8000 | Orchestrator | `adk_memories`, `revoked_sessions` | ADK Runner, router LLM, React UI |
| `greeting_agent` | `GreetingAgent/` | 8209 | Discovery | — | Prompt only |
| `discovery_agent` | `DiscoveryAgent/` | 8201 | Discovery | `accounts`, `contacts`, `spend`, `opportunities`, `insights`, `actions` | PostgreSQL tools |
| `faq_agent` | `FAQAgent/` | 8210 | Discovery | — | Prompt only |
| `serviceability_agent` | `ServiceabilityAgent/` | 8202 | Configuration | — | MCP → serviceability service (`coverage_zones`) |
| `product_agent` | `ProductAgent/` | 8203 | Configuration | — | MCP → catalog service (`products` + ChromaDB RAG) |
| `offer_management_agent` | `OfferManagement/` | 8204 | Configuration | `quotes` | PostgreSQL tools, price book |
| `order_agent` | `OrderAgent/` | 8205 | Transaction | `carts`, `cart_items`, `orders`, `order_items` | PostgreSQL tools |
| `payment_agent` | `PaymentAgent/` | 8206 | Transaction | `payments`, `payment_events`, `payment_rate_limit`, `customer_payment_methods` | Hardened payment pipeline |
| `service_fulfillment_agent` | `ServiceFulfillmentAgent/` | 8207 | Transaction | `fulfillments`, `customer_master` | Scheduling, provisioning, activation |
| `customer_communication_agent` | `CustomerCommunicationAgent/` | 8208 | Transaction | `notifications`, `dedup_cache` | Outbox dispatcher, SMTP or simulated delivery |

| Tool service | Directory | Port | Tables owned | Interfaces |
|---|---|---|---|---|
| Catalog | `services/catalog/` | 8101 | `products` | REST `/api/v1`, MCP `/mcp/` (8 tools), ChromaDB knowledge index |
| Serviceability | `services/serviceability/` | 8102 | `coverage_zones` | REST `/api/v1`, MCP `/mcp/` (6 tools), optional upstream GIS |

The service manifest used by all scripts is [`scripts/services.conf`](scripts/services.conf); the gateway's routing registry is `SuperAgent/super_agent/registry.py`.

### Agent Routing Priority

The router (`route_intent`) picks one agent per turn in this priority order:

| Priority | Intent Pattern | Target Agent |
|----------|---------------|--------------|
| 1 | Company/business identification | `discovery_agent` |
| 2 | Address validation, coverage check | `serviceability_agent` |
| 3 | Product catalog, specs, SLA questions (no pricing) | `product_agent` |
| 4 | Pricing, quotes, discounts | `offer_management_agent` |
| 5 | Cart, checkout, order placement | `order_agent` |
| 6 | Payment, credit check | `payment_agent` |
| 7 | Installation, scheduling, activation | `service_fulfillment_agent` |
| 8 | Send notification, show history | `customer_communication_agent` |
| 9 | Greetings ("Hi", "Hello"); pure greetings skip the router | `greeting_agent` |
| 10 | Policy, SLA, general questions; fallback for invalid router output | `faq_agent` |

---

## Database Architecture (PostgreSQL)

All services share **one PostgreSQL 16 database** (a `postgres:16` container or your own server locally, Cloud SQL in GCP). It replaces the earlier SQLite `sales_agent.db` and its GCS sync.

- **Schema** is managed only by versioned SQL migrations in `db/migrations/` (`001_sales_schema.sql` 19 sales tables, `002_catalog.sql` `products`, `003_platform.sql` `adk_memories` + `revoked_sessions`, `004_coverage.sql` `coverage_zones`). Services never create business tables at runtime.
- **Seed data** in `db/seed/` (demo accounts exported from the legacy SQLite database, 16 SKUs, 38 coverage ZIPs) is applied once per database.
- **Apply** with `scripts/db.sh migrate | seed | reset --yes` or `python -m sales_common.migrate [--seed]`. Applied files are tracked in `schema_migrations` / `seed_versions`.
- **Library-managed tables:** ADK session tables (`sessions`, `events`, `app_states`, `user_states`) are created by `DatabaseSessionService`, and `a2a_tasks` by the a2a-sdk `DatabaseTaskStore`.
- **Access:** agent tools use `sales_common.db` (psycopg 3 connection pool, dict rows, `transaction()`); ADK sessions and tasks use SQLAlchemy + asyncpg.

```
┌───────────────────────────────────────────────────────────────────────────┐
│           PostgreSQL 16  (one database, table ownership per service)      │
├──────────────┬───────────┬───────────┬──────────┬──────────┬──────────────┤
│  DISCOVERY   │   OFFER   │   ORDER   │ PAYMENT  │ FULFILL  │    COMMS     │
│ accounts     │ quotes    │ carts     │ payments │fulfill-  │ notifications│
│ contacts     │           │ cart_items│ payment_ │ ments    │  (outbox)    │
│ spend        │           │ orders    │  events  │customer_ │ dedup_cache  │
│ opportunities│           │ order_    │ payment_ │ master   │              │
│ insights     │           │  items    │ rate_... │          │              │
│ actions      │           │           │ customer_│          │              │
│              │           │           │ payment_ │          │              │
│              │           │           │ methods  │          │              │
├──────────────┴───────────┴───────────┴──────────┴──────────┴──────────────┤
│ TOOL SERVICES   products (catalog) · coverage_zones (serviceability)      │
│ PLATFORM        adk_memories · revoked_sessions · ADK sessions · a2a_tasks│
└───────────────────────────────────────────────────────────────────────────┘
```

Table ownership (the single writer per table, and the remaining cross-domain writers) is documented in [db/README.md](db/README.md).

### Entity Relationship Diagram

```mermaid
erDiagram
    accounts ||--o{ contacts : "has"
    accounts ||--o| spend : "has"
    accounts ||--o{ opportunities : "has"
    accounts ||--o| insights : "has"
    accounts ||--o| actions : "has"
    accounts ||--o{ quotes : "quoted for"
    accounts ||--o{ carts : "shops via"
    accounts ||--o{ orders : "places"
    accounts ||--o| customer_master : "becomes"

    quotes ||--o| orders : "converted to"

    carts ||--|{ cart_items : "contains"

    orders ||--|{ order_items : "contains"
    orders ||--o| payments : "paid by"
    orders ||--o| fulfillments : "fulfilled by"
    orders ||--o{ notifications : "triggers"

    fulfillments ||--o| customer_master : "creates"

    accounts {
        text Company_Name PK
        text Parent_Company
        text Industry
        text Territory_Region
        text Street
        text City
        text State
        text zip_code "NOT NULL"
        text Website
        text Existing_Customer "Y/N"
        text Current_Products
        text Products_of_Interest
        text customer_id "UUID"
    }

    contacts {
        text Company_Name FK
        text Name
        text Title
        text Role_in_Decision_Making
        text Email
        text Phone
        text Notes
    }

    spend {
        text Company_Name FK
        int Estimated_Annual_Spend
        int Digital
        int Programmatic
        int TV
        int Audio
        int OOH
        int Search
        int Social
        text Primary_Agency
    }

    opportunities {
        text Company_Name FK
        text Opportunity_Name
        text Stage
        int Total_MRC_Est
        text Budget
        text Authority
        text Need
        int Timeline_days
        real BANT_Score_0to100
        text BANT_Priority_Bucket
    }

    insights {
        text Company_Name FK
        text Buying_Signals
        text Pain_Points
        text Recommended_Positioning
    }

    actions {
        text Company_Name FK
        text Owner
        text Priority
        text Initial_Outreach_Date
        text Follow_Up_Cadence
    }

    quotes {
        text offer_id PK
        text customer_id FK
        text company_name
        text items_json
        int term_months
        real bant_score
        real subtotal
        real total_discount
        real total_price
        real monthly_total
        real yearly_total
        text status "active/ordered/expired"
        text expires_at
    }

    carts {
        text cart_id PK
        text customer_id FK
        real total_amount
        text status "active/expired"
        text expires_at
    }

    cart_items {
        int id PK
        text cart_id FK
        text service_type
        real price
        int quantity
        real subtotal
    }

    orders {
        text order_id PK
        text customer_name
        text customer_id FK
        text service_address
        text contact_phone
        text contact_email
        text offer_id FK
        text status "draft/pending_payment/paid/fulfilled/cancelled/escalated"
        real total_amount
        text expires_at
    }

    order_items {
        int id PK
        text order_id FK
        text service_type
        real price
        int quantity
        real subtotal
    }

    payments {
        text payment_id PK
        text order_id FK
        text customer_id FK
        text transaction_id
        real amount
        text status "initiated/processing/completed/failed"
        int credit_score
        text payment_method
        text expires_at
    }

    fulfillments {
        text fulfillment_id PK
        text order_id FK
        text customer_id FK
        text dispatch_id
        text activation_id
        text circuit_id
        text account_id
        text appointment_date
        text status "scheduled/dispatched/installed/activated"
    }

    customer_master {
        text customer_id PK
        text company_name
        text street
        text city
        text state
        text zip_code
        text contact_name
        text contact_email
        text contact_phone
        text first_order_id FK
        text circuit_id
        text account_id
        text contracted_products
        real monthly_revenue
        text activated_at
    }

    notifications {
        text notification_id PK
        text notification_type
        text recipient_email
        text recipient_phone
        text subject
        text message
        text customer_id FK
        text order_id FK
        text status "pending/sent/simulated/failed"
        text channels_json
        text metadata_json "template + args"
    }

    dedup_cache {
        text dedup_key PK
        text sent_at
    }
```

### How Entities Are Updated Along the Sales Conversation

Each row is a user turn that triggers one or more agent actions:

| Stage | Conversation Trigger | Agent / service | Tables Written | Operation |
|-------|---------------------|-------|---------------|-----------|
| **1. Greeting** | "Hi, I need internet for my office" | `greeting_agent` | — | No DB writes. Returns the phone script. |
| **2. Discovery** | "We're VoiceStream Networks at 123 Main St, Boston" | `discovery_agent` | `accounts` | **INSERT** company with address, zip code, `customer_id`; publishes `customer_context`. |
| | *(agent asks for contact info)* | `discovery_agent` | `contacts` | **INSERT** contact with name, title, email, phone. |
| | *(agent runs BANT qualification)* | `discovery_agent` | `opportunities`, `insights` | **INSERT** opportunity with BANT scores; buying signals and pain points. |
| **3. Serviceability** | *(same turn, deterministic handoff)* or "Check coverage" | `serviceability_agent` → serviceability service | — | No writes. Reads `coverage_zones` through MCP; publishes `serviceability_context`. |
| **4. Product** | "Show me Fiber 5G specs" | `product_agent` → catalog service | — | No writes. Reads `products` through MCP; `search_product_knowledge` queries the ChromaDB index. |
| **5. Quote** | "Give me pricing for Fiber 5G + SD-WAN" | `offer_management_agent` | `quotes`, `notifications` | **INSERT** quote (offer_id, items, discounts, totals; status `active`, 30-day expiry); outbox row for the quote confirmation. |
| **6. Order** | "Proceed with this quote" | `order_agent` | `carts`, `cart_items`, `orders`, `order_items`, `quotes`, `notifications` | **INSERT** cart and order (status `pending_payment`, 48h expiry). **UPDATE** `quotes.status` → `ordered` via `sales_common.repositories.quotes`. Outbox row for the order confirmation. |
| **7. Scheduling** | "Schedule installation" | `service_fulfillment_agent` | `fulfillments`, `notifications` | **INSERT** fulfillment with appointment (status `scheduled`); the workflow then hands off to payment in the same turn. |
| **8. Payment** | *(same turn, deterministic handoff)* then card details | `payment_agent` | `payments`, `payment_events`, `orders`, `notifications` | **INSERT** payment + audit events; **UPDATE** `orders.status` → `paid`; outbox row for the payment receipt. |
| **9. Dispatch / install** | "Simulate install day" | `service_fulfillment_agent` | `fulfillments` | **UPDATE** dispatch id, status → `dispatched` → `installed`. |
| **10. Activation** | "Activate service" | `service_fulfillment_agent` | `fulfillments`, `customer_master`, `accounts`, `orders`, `notifications` | **UPDATE** fulfillment (circuit_id, account_id, `activated`); **INSERT** `customer_master`; **UPDATE** `accounts."Existing Customer"` → `Y` and `orders.status` → `fulfilled`. |
| **Cross-cutting** | *(continuous)* | customer communication dispatcher | `notifications`, `dedup_cache` | Picks `pending` outbox rows (`FOR UPDATE SKIP LOCKED`), renders them, sends via SMTP or simulation, marks `sent` / `simulated` / `failed`, records dedup keys. |
| **Maintenance** | *(startup + hourly)* | gateway (`sales_common.maintenance`) | `quotes`, `carts`, `orders`, `notifications` | Expires stale quotes and carts, cancels timed-out `pending_payment` orders, escalates stuck paid orders, enqueues abandoned-cart / order-cancelled notifications. |

### Entity Lifecycle State Machines

```
Quote:      active ──→ ordered ──→ (done)
                 └──→ expired (TTL: 30 days)

Cart:       active ──→ (consumed by order)
                 └──→ expired (TTL: 24 hours)

Order:      draft ──→ pending_payment ──→ paid ──→ fulfilled
                           │               └──→ escalated (paid, stuck >7 days)
                           └──→ cancelled (pending_payment TTL: 48h)

Payment:    initiated ──→ processing ──→ completed
                                   └──→ failed

Notification (outbox): pending ──→ sent | simulated | failed

Fulfillment: scheduled ──→ dispatched ──→ installed ──→ activated

Account:    Existing_Customer=N ──→ Existing_Customer=Y (on activation)
```


### Table-to-Service Access Matrix

| Table | Discovery | Offer | Order | Payment | Fulfillment | Comms | Catalog svc | Serviceability svc | Gateway |
|-------|:---------:|:-----:|:-----:|:-------:|:-----------:|:-----:|:-----------:|:------------------:|:-------:|
| **accounts** | R/W | — | — | — | R/W | — | — | — | R |
| **contacts** | R/W | — | — | — | — | — | — | — | R |
| **spend**, **actions** | R | — | — | — | — | — | — | — | — |
| **opportunities**, **insights** | R/W | — | — | — | — | — | — | — | — |
| **quotes** | — | R/W | W | — | — | — | — | — | W |
| **carts**, **cart_items** | — | — | R/W | — | — | — | — | — | W |
| **orders** | — | — | R/W | R/W | R/W | — | — | — | R/W |
| **order_items** | — | — | R/W | — | R | — | — | — | — |
| **payments** + payment tables | — | — | — | R/W | — | — | — | — | — |
| **fulfillments** | — | — | — | — | R/W | — | — | — | — |
| **customer_master** | R | — | — | — | W | — | — | — | — |
| **notifications** (outbox) | — | W | W | W | W | R/W | — | — | W |
| **dedup_cache** | — | — | — | — | — | R/W | — | — | — |
| **products** | — | — | — | — | — | — | R | — | — |
| **coverage_zones** | — | — | — | — | — | — | — | R | — |
| **adk_memories**, **revoked_sessions** | — | — | — | — | — | — | — | — | R/W |

> **R** = SELECT, **W** = INSERT/UPDATE. **Gateway** includes the hourly `cleanup_stale_records()` maintenance. Every agent service and the gateway also use the library-managed ADK session and `a2a_tasks` tables. The follow-up `mcp-remaining-domains` removes the remaining cross-domain writers (e.g. Payment and Fulfillment updating `orders`).

### PaymentAgent Hardening

The PaymentAgent is a **deterministic, defense-in-depth payment workflow** rather than a simple "charge card" wrapper:

- **Idempotency keys** on `process_payment()` so client retries return the original result instead of creating duplicate charges.
- **Duplicate-payment protection** that checks whether an order already has a completed payment before inserting a new one.
- A **payment state machine** with explicit transitions (`initiated → processing → completed/failed`).
- **Per-customer rate limiting** for payment attempts (`payment_rate_limit`).
- **Velocity-aware approval checks** that simulate transaction-count and cumulative-spend controls.
- An **append-only `payment_events` audit trail** for every status transition.
- **Cryptographically random tokens and transaction identifiers.**
- **CVV discard** after validation; sensitive verification data is never stored.
- **Order-linked persistence** in PostgreSQL, with `orders.status` updated to `paid` only after successful completion, in the same transaction as the payment-receipt outbox row.
- **Journey-state propagation:** `payment_context` is written to state and returned to the gateway as `_context_update`, so downstream steps never re-infer payment results from conversation text.

---

## Example Conversation Flows

### Discovery → Serviceability (zero-click handoff)

```
User: "We're Crane.io at 123 Main St, Philadelphia PA 19103"
  ↓ route_intent → discovery_agent (A2A)
  ↓ Discovery registers the company; customer_context returns as _context_update
  ↓ ContextBridgePlugin merges it into the gateway session
  ↓ HandoffPolicyNode: customer has a zip code, no serviceability check yet
  ↓ serviceability_agent receives "Check service availability for this address: {JSON}"
  ↓ serviceability service (MCP) → "✅ Serviceable with Fiber 1G/5G/10G"
  (Same turn: no user message needed between Discovery and Serviceability)
```

### Product → Offer → Order → Scheduling → Payment (zero-click handoff)

```
User: "Fiber 5G pricing with SD-WAN?"
  ↓ route_intent → offer_management_agent
  ↓ Pricing calculation (JSON quote) → quote card in the UI
  ↓ "Quote #12345: $X,XXX/month"

User: "Proceed"
  ↓ route_intent → order_agent → cart + order (status: pending_payment)

User: "Schedule installation for tomorrow morning"
  ↓ route_intent → service_fulfillment_agent → schedule_installation → "Confirmed! APT-20260505-482"
  ↓ ContextBridgePlugin records appointment_confirmed_order
  ↓ HandoffPolicyNode: order unpaid → payment_agent
  ↓ PaymentAgent asks for the payment method, then credit check + authorization
  (Same turn: no user message needed between Scheduling and Payment)
```

---

## 🗃️ RAG / ChromaDB Knowledge Base

Product data and product knowledge live in the **catalog service** (`services/catalog/`), not in the product agent. The product agent reaches both through MCP:

| Data Source | MCP tools | When Used |
|-------------|-------|-----------|
| **`products` table** (PostgreSQL, 16 SKUs) | `get_product_by_id`, `list_available_products`, `compare_products`, `search_products_by_criteria`, `suggest_alternatives`, `get_best_value_product`, `get_product_categories` | Product lookups, comparisons, filtering by speed/category |
| **ChromaDB vector store** (RAG) | `search_product_knowledge` | Documentation-level questions: SLA specifics, installation requirements, codec details, use-case fit |

> **Key nuance:** "Compare Fiber 1G vs 5G" reads the **catalog table**, not RAG. RAG is used only when the question needs documentation-level depth (e.g., "What codec does Business Voice use?"). Prices are never returned by the catalog service; they come only from the offer management agent.

### How RAG Works

```
User question
  → product_agent calls search_product_knowledge (MCP → catalog service)
  → query encoded to a 384-dim vector (sentence-transformers all-MiniLM-L6-v2)
  → ChromaDB similarity search → top_k passages (default 4)
  → structured passages {text, doc_file, section, product_ids, distance}
  → agent composes a grounded answer
```

- **Sources:** `services/catalog/data/product_docs/*.md` (fiber, coax, voice, SD-WAN, mobile).
- **Index:** `CHROMA_PATH` (default `services/catalog/data/embeddings`, gitignored). Build it with `python services/catalog/scripts/ingest_knowledge.py`, or let the service build it in the background on first start (`RAG_BUILD_ON_START=true`).
- **Docker / Cloud Run:** the catalog image installs CPU-only PyTorch, pre-stages the embedding model at `EMBEDDING_MODEL_PATH` and builds the index at image build time; at runtime it works offline.
- **Degraded mode:** when the model or index is unavailable, `search_product_knowledge` returns `available: false` and the rest of the catalog keeps working. (In the build sandbox used for the rewrite the model download was blocked, so this path was the one exercised.)

Details: [services/catalog/README.md](services/catalog/README.md).

---

## Sales Conversation Flow

Typical end-to-end flow:

1. **Discovery** — collect business/location context
2. **Serviceability** — verify address + infrastructure (automatic after discovery)
3. **Product** — recommend technically compatible products
4. **Offer Management** — compute quote JSON (pricing + discounts + totals)
5. **Order** — cart/checkout and contract creation
6. **Fulfillment** — schedule installation
7. **Payment** — credit check + authorization (automatic after scheduling)
8. **Activation** — install day, activation, `customer_master`
9. **Customer Comms** — confirmations and reminders via the notification outbox

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite 6 + Tailwind CSS 3 |
| Gateway / services | FastAPI / Starlette, Python 3.12 |
| Agent Framework | Google ADK 2.10.0 (`google-adk[a2a,mcp,db]`): `Workflow`, `App`, `DatabaseSessionService`, `RemoteA2aAgent`, `to_a2a`, `McpToolset` |
| Agent protocol | A2A (a2a-sdk 1.x) with agent cards and a PostgreSQL task store |
| Tool protocol | MCP (`mcp` 2.x `MCPServer`, streamable HTTP) |
| LLM | Gemini (configured via `GEMINI_MODEL`, e.g. `gemini-3-flash-preview`) |
| Streaming | Server-Sent Events (SSE) |
| Database | PostgreSQL 16 (psycopg 3, SQLAlchemy 2.1 + asyncpg), versioned SQL migrations |
| RAG | ChromaDB + sentence-transformers (catalog service) |
| Deployment | Docker Compose locally; Cloud Run + Cloud SQL + Secret Manager on GCP |

---

## Repository Layout

```
ConversationalSalesAgent/
├── AGENTS.md / CLAUDE.md            # Architecture, standards, assistant instructions
├── README.md / Scenarios.md         # Overview and test scenarios
├── GCP_DEPLOY.md                    # Multi-service Cloud Run deployment guide
├── .env.example                     # Shared environment template (copied to .env)
├── docker-compose.yml               # Full local stack in containers
├── docs/agent-service-guide.md      # How every agent service is built, served and tested
├── openspec/changes/                # Design proposals and specs for the rewrite
├── libs/sales_common/               # Shared runtime library (config, db, A2A, MCP, memory, outbox)
├── db/                              # migrations/ + seed/ (PostgreSQL), README with table ownership
├── scripts/                         # services.conf + setup/start/stop/db/deploy scripts, e2e_test.py
├── services/
│   ├── catalog/                     # Product catalog REST + MCP + RAG (port 8101)
│   └── serviceability/              # Address + coverage REST + MCP (port 8102)
├── SuperAgent/                      # Gateway (port 8000)
│   ├── super_agent/                 #   sales_journey workflow, registry, router prompt, plugins
│   ├── server/                      #   FastAPI app: session, chat (SSE), debug endpoints
│   ├── client/                      #   React UI
│   └── tests/
├── DiscoveryAgent/                  # A2A agent services (ports 8201-8210), each with
├── ServiceabilityAgent/             #   <pkg>/agent.py, prompts.py, tools/, server.py,
├── ProductAgent/                    #   tests/, Dockerfile, AGENTS.md, README.md
├── OfferManagement/
├── OrderAgent/
├── PaymentAgent/
├── ServiceFulfillmentAgent/
├── CustomerCommunicationAgent/
├── GreetingAgent/
├── FAQAgent/
├── BootStrapAgent/                  # ADK bootstrap template (reference only)
└── tests/integration/               # Multi-process integration test (scripted fake model)
```

---

## Getting Started (Local)

### Prerequisites

- Python 3.12 (3.11+ works for development)
- Node.js 20 (for the React UI)
- PostgreSQL 16, either your own server or Docker (`docker compose`)
- A Gemini API key

### Option A: Native processes (recommended for development)

```bash
# 1. One-time setup: venv, editable installs of libs/sales_common and every service,
#    client npm ci, and .env copied from .env.example (only if .env does not exist)
scripts/setup_local.sh

# 2. Edit .env: GOOGLE_API_KEY, GEMINI_MODEL, DATABASE_URL (default postgresql://csa:csa@localhost:5432/csa)
#    and optionally SESSION_SECRET_KEY (an ephemeral one is generated if empty)

# 3. A PostgreSQL 16 database matching DATABASE_URL, e.g. a throwaway container:
docker run -d --name csa-pg -e POSTGRES_USER=csa -e POSTGRES_PASSWORD=csa -e POSTGRES_DB=csa \
  -p 127.0.0.1:5432:5432 postgres:16

# 4. Start everything: migrations + seed, 2 tool services, 10 agents, gateway, Vite UI
scripts/start_local.sh
```

- UI: `http://localhost:3000` (Vite proxies `/api` to the gateway)
- Gateway health: `http://localhost:8000/health`
- Agent cards: `http://localhost:8201/.well-known/agent-card.json` … `:8210`
- Tool services: `http://localhost:8101/docs`, `http://localhost:8102/docs`

Useful flags: `scripts/start_local.sh --only catalog,product,gateway`, `--no-ui`, `--skip-migrate`.

> The `postgres` service in `docker-compose.yml` is not published on the host, so native processes need their own PostgreSQL (as above).

### Option B: Everything in containers

```bash
cp .env.example .env      # set GOOGLE_API_KEY, GEMINI_MODEL, POSTGRES_PASSWORD
docker compose up --build
```

Starts PostgreSQL 16, a one-shot `db-init` (migrations + seed), both tool services, all 10 agents and the gateway on a private network. Only the gateway is published: `http://localhost:8000` serves the built UI and the API.

### Logs and Stopping

```bash
tail -f logs/gateway.log logs/discovery.log logs/serviceability-agent.log   # native processes
scripts/stop_local.sh                     # stops only the PIDs recorded in logs/pids/
scripts/stop_local.sh --only order,ui     # stop selected services
docker compose down                       # containers
```

### Database Operations

```bash
scripts/db.sh migrate            # apply pending migrations
scripts/db.sh seed               # migrations + seed files (each applied once)
scripts/db.sh reset --yes        # drop and recreate the schema, then migrate + seed (local hosts only)
```

### Tests

```bash
pytest OrderAgent/tests -q                                   # any agent or service
TEST_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_test pytest SuperAgent/tests -q
TEST_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_test venv/bin/python -m pytest tests/integration -q -s
python scripts/e2e_test.py --base-url http://127.0.0.1:8000  # against a running stack (real Gemini)
```

DB-backed tests are skipped when `TEST_DATABASE_URL` is unset; use a scratch database. Agent tests use a scripted model and need no API key.

---

## GCP Cloud Run Deployment

The system deploys as **13 Cloud Run services** (public gateway; private agents and tool services called with Google-signed ID tokens), a **Cloud Run job** for migrations + seed, and **Cloud SQL for PostgreSQL 16**:

```bash
scripts/setup_gcp.sh                   # one time: APIs, Artifact Registry, Cloud SQL, secrets, service accounts
scripts/deploy_cloud.sh                # build, migrate, deploy tools → agents → gateway
scripts/deploy_cloud.sh --only order   # redeploy one service
scripts/shutdown_cloud.sh              # pause: gateway private + Cloud SQL stopped
scripts/start_cloud.sh                 # resume
```

See [GCP_DEPLOY.md](./GCP_DEPLOY.md) for resources, IAM, secrets, environment variables, costs, verification, troubleshooting and rollback.

---

## Documentation

| File | Purpose |
|------|---------|
| [AGENTS.md](./AGENTS.md) | Architecture, ADK standards, workflow and handoffs, development workflow |
| [docs/agent-service-guide.md](./docs/agent-service-guide.md) | Building, serving and testing an agent service |
| [SuperAgent/README.md](./SuperAgent/README.md) | Gateway: workflow, API, environment variables, tests |
| [services/catalog/README.md](./services/catalog/README.md) | Catalog REST + MCP + RAG service |
| [services/serviceability/README.md](./services/serviceability/README.md) | Serviceability REST + MCP service |
| [db/README.md](./db/README.md) | Migrations, seed files, table ownership |
| [GCP_DEPLOY.md](./GCP_DEPLOY.md) | Multi-service Cloud Run deployment guide |
| [tests/integration/README.md](./tests/integration/README.md) | Multi-process integration test |
| [Scenarios.md](./Scenarios.md) | Test cases and end-to-end conversation flows |
| `openspec/changes/` | Design proposals, decisions and specs (`mcp-remaining-domains` is a planned follow-up) |
| Each `<Agent>/AGENTS.md` | Individual agent documentation |

