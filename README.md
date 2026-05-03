# B2B Conversational Sales Agent

A multi-agent orchestration system for end-to-end B2B telecom sales conversations, built on Google ADK with Gemini.

**Drexel University – Senior Design Project — Winter/Spring 2026**

---

## What This Project Is

This repository implements a **multi-agent orchestration system** — a hierarchical architecture where a central **SuperAgent** coordinates 10 specialized sub-agents to automate the full B2B telecom sales lifecycle, from initial prospect discovery through order fulfillment.

Built on **Google ADK (Agent Development Kit)** with **Google Gemini** as the backbone LLM, the system enforces a strict separation between:

- **LLM-driven reasoning** — intent classification, conversational routing, natural language generation
- **Deterministic tool execution** — database lookups, pricing calculations, address validation, payment processing

The LLM decides *what* to do; critical business data (addresses, prices, orders) is always sourced from deterministic tools, never hallucinated.

---

## Architecture

![System Architecture](./architecture-diagram.png)

*Interactive version: open [architecture.html](./architecture.html) in your browser*

```
User → React Client → FastAPI → ADK Runner → SuperAgent → Sub-Agent → Tools → Infrastructure
```

Responses stream back to the browser via Server-Sent Events (SSE).

### Architectural Layers

```
┌─────────────────────────────────────────────────────────┐
│  PRESENTATION    React 19 + FastAPI (SSE Streaming)     │
├─────────────────────────────────────────────────────────┤
│  ORCHESTRATION   SuperAgent (Router + Session State)    │
├───────────┬───────────┬─────────────────────────────────┤
│ DISCOVERY │   CONFIG  │  TRANSACTION                    │
│ Discovery │ Service-  │ Order · Payment · Fulfillment   │
│ Greeting  │ ability   │ Customer Communications         │
│ FAQ       │ Product   │                                 │
│           │ Offer Mgmt│                                 │
├───────────┴───────────┴─────────────────────────────────┤
│  INFRASTRUCTURE  SQLite · GIS API · Pricing · Scheduler │
└─────────────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Separation of concerns** | Each agent owns exactly one domain |
| **Zero-hallucination for critical data** | Addresses, prices, orders always come from deterministic tools |
| **Router-only orchestrator** | SuperAgent classifies intent and delegates — never generates user-facing text |
| **Temperature-stratified agents** | Conversational agents use temp 0.7; transactional agents use temp 0.0 |
| **Structured data contracts** | Tools return JSON (not prose) to prevent LLM rephrasing of critical values |
| **Shared session-state contracts** | Agents publish authoritative context into ADK session state so downstream agents consume structured facts instead of re-reading conversation text |
| **Importlib isolation** | Sub-agents loaded without triggering `__init__.py` to avoid ADK parent-binding conflicts |

### How Agents Communicate

```
User Message → SuperAgent (intent analysis)
                  │
                  ├─ SuperAgent → Sub-agent delegation
                  │    transfer_to_agent("discovery_agent")
                  │    transfer_to_agent("product_agent")
                  │    transfer_to_agent("payment_agent")
                  │
                  ├─ Sub-agent → Sub-agent workflow continuation
                  │    discovery_agent → serviceability_agent
                  │    order_agent → service_fulfillment_agent
                  │    service_fulfillment_agent → order_agent
                  │    order_agent → payment_agent
                  │    payment_agent → order_agent
                  │
                  └─ Shared ADK session state
                       customer_context → serviceability_context
                       order_context → payment_context
                       consumed by downstream agents/tools
```

- **SuperAgent → sub-agent routing** is ADK-native. SuperAgent declares `sub_agents=[...]` and always calls `transfer_to_agent(...)` rather than producing customer text.
- **Sub-agent → sub-agent progression** is also ADK-native. Once a specialist finishes a step, it can call `transfer_to_agent(...)` itself to hand control to the next specialist without waiting for the root orchestrator to re-interpret the workflow.
- **Shared session state is the data plane.** Agents exchange authoritative facts through ADK session keys such as `customer_context`, `serviceability_context`, `order_context`, and `payment_context`.
- **Deterministic tools publish state; conversational agents consume it.** This prevents downstream agents from reconstructing addresses, order IDs, or payment results from natural-language history.
- **Wrapper callbacks stabilize brittle handoffs.** Where Gemini occasionally fails to emit text plus transfer reliably, SuperAgent wrappers use `after_agent_callback` logic to enforce the intended next step without abandoning ADK's delegation model.

### ADK Session State Implementation

The system uses **ADK session state as a shared structured memory layer** across the entire sales workflow. This is not just generic chat memory; it is a deliberate contract for moving critical business context between agents without re-parsing free-form conversation.

**Current state contracts in use:**

- `customer_context` — published by DiscoveryAgent after prospect registration or company lookup so downstream agents know the authoritative customer identity and service address.
- `serviceability_context` — published by ServiceabilityAgent after GIS validation so ProductAgent and OfferManagementAgent can reason over confirmed access technology, serviceability status, and infrastructure details.
- `order_context` — published by OrderAgent after quote-to-order conversion so PaymentAgent and Fulfillment can consume the exact `order_id`, `customer_id`, selected services, and commercial payload.
- `payment_context` — published by PaymentAgent after successful processing so downstream confirmation, activation, and notification logic can consume the exact payment outcome and transaction identifiers.

**Why this was implemented:**

- **To prevent hallucinated handoff data.** Exact values like zip codes, order IDs, offer IDs, and transaction IDs should not be regenerated from conversation text.
- **To support multi-turn workflows.** Payment, scheduling, activation, and notifications often happen on later turns; session state preserves authoritative context across those boundaries.
- **To decouple reasoning from transaction semantics.** The LLM can decide what step comes next, while deterministic tools remain the source of truth for what already happened.
- **To make recovery and retries safe.** If an agent transfer is retried or a model turn is empty, the next component can resume from state instead of guessing from chat history.

**Benefits of this approach:**

- **Higher reliability** for agent-to-agent workflows because downstream steps consume machine-written state instead of model-written prose.
- **Cleaner prompt design** because prompts can assume structured context exists instead of repeatedly extracting the same facts.
- **Safer transactional chaining** across quote → order → payment → fulfillment → activation.
- **Better observability** because state reads and writes can be logged at each boundary.

**Current implementation pattern:**

1. A deterministic tool completes a business step.
2. That tool writes a compact structured payload into `tool_context.state[...]`.
3. The next agent reads the state key instead of inferring the result from prior messages.
4. If the conversational handoff is brittle, a wrapper-level `after_agent_callback` can use that same state to enforce the next transfer or synthesize the next deterministic opener.

This is why the current design still uses agents: the LLM remains responsible for conversational flexibility and routing, while **ADK session state provides the structured continuity layer** needed for exact business workflows.

---

## Agent Architecture

### Super Agent / Sub-Agent Hierarchy

The system implements a **hierarchical orchestration pattern** where a root SuperAgent delegates to 10 specialized sub-agents using ADK's native `sub_agents=[]` mechanism:

```
                         ┌─────────────────────┐
                         │     SuperAgent       │
                         │  (Root Orchestrator) │
                         │                      │
                         │  • Intent Analysis   │
                         │  • Routing Rules     │
                         │  • Session State     │
                         │  • Guardrails        │
                         └──────────┬───────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
   ┌───────▼────────┐     ┌────────▼────────┐     ┌────────▼─────────┐
   │   DISCOVERY     │     │  CONFIGURATION  │     │   TRANSACTION    │
   │   CLUSTER       │     │  CLUSTER        │     │   CLUSTER        │
   ├─────────────────┤     ├─────────────────┤     ├──────────────────┤
   │ GreetingAgent   │     │ Serviceability  │     │ OrderAgent       │
   │  └ phone script │     │  Agent          │     │  └ carts, orders │
   │                 │     │  └ GIS/coverage  │     │                  │
   │ DiscoveryAgent  │     │                 │     │ PaymentAgent     │
   │  └ prospect DB  │     │ ProductAgent    │     │  └ credit, auth  │
   │                 │     │  └ catalog+RAG   │     │                  │
   │ FAQAgent        │     │                 │     │ ServiceFulfill.  │
   │  └ knowledge    │     │ OfferManagement │     │  └ scheduling    │
   │    base         │     │  └ pricing,     │     │  └ dispatch      │
   │                 │     │    quotes       │     │  └ activation    │
   │                 │     │                 │     │                  │
   │                 │     │                 │     │ CustomerComms    │
   │                 │     │                 │     │  └ notifications │
   └─────────────────┘     └─────────────────┘     └──────────────────┘
```

### Agent Registry

| Agent | Cluster | DB Tables Owned | Infrastructure |
|-------|---------|----------------|----------------|
| **SuperAgent** | Orchestrator | — (routes only) | ADK Runner |
| **GreetingAgent** | Discovery | — | Static content |
| **DiscoveryAgent** | Discovery | `accounts`, `contacts`, `spend`, `opportunities`, `insights`, `actions` | Unified SQLite |
| **FAQAgent** | Discovery | — | Knowledge base |
| **ServiceabilityAgent** | Configuration | — (stateless) | GIS API (mock) |
| **ProductAgent** | Configuration | — | JSON Catalog + ChromaDB |
| **OfferManagementAgent** | Configuration | `quotes` | Unified SQLite |
| **OrderAgent** | Transaction | `carts`, `cart_items`, `orders`, `order_items` | Unified SQLite |
| **PaymentAgent** | Transaction | `payments` | Unified SQLite + hardened payment pipeline (idempotency, state machine, audit trail, rate limiting) |
| **ServiceFulfillmentAgent** | Transaction | `fulfillments`, `customer_master` | Unified SQLite + Scheduler |
| **CustomerCommunicationAgent** | Transaction | `notifications`, `dedup_cache` | Unified SQLite + SMTP |

### Agent Routing Priority

SuperAgent routes user messages in this priority order:

| Priority | Intent Pattern | Target Agent |
|----------|---------------|--------------|
| 1 | Company/business identification | DiscoveryAgent |
| 2 | Address validation, coverage check | ServiceabilityAgent |
| 3 | Product catalog, specs, SLA questions | ProductAgent |
| 4 | Pricing, quotes, discounts | OfferManagementAgent |
| 5 | Cart, checkout, order placement | OrderAgent |
| 6 | Payment, credit check | PaymentAgent |
| 7 | Installation, scheduling, activation | ServiceFulfillmentAgent |
| 8 | Send notification, show history | CustomerCommunicationAgent |
| 9 | Greetings ("Hi", "Hello") | GreetingAgent |
| 10 | Policy, SLA, general questions | FAQAgent |

---

## Unified Database Architecture

All agents share a **single SQLite database** (`sales_agent.db`) with WAL mode and foreign key enforcement. This replaces the earlier per-agent database design (separate `discover_prospecting_clean.db`, `orders.db`, `quotes.db`, `notifications.db`) with a consolidated schema of **17 tables across 7 domains**.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     sales_agent.db  (SQLite + WAL)                       │
├──────────────┬───────────┬───────────┬──────────┬────────┬──────────────┤
│  DISCOVERY   │   OFFER   │   ORDER   │ PAYMENT  │FULFILL │    COMMS     │
│  (6 tables)  │ (1 table) │ (4 tables)│(1 table) │(1 tbl) │  (2 tables)  │
│              │           │           │          │        │              │
│ accounts     │ quotes    │ carts     │ payments │fulfill-│ notifications│
│ contacts     │           │ cart_items│          │ ments  │ dedup_cache  │
│ spend        │           │ orders    │          │        │              │
│ opportunities│           │ order_    │          │        │              │
│ insights     │           │   items   │          │        │              │
│ actions      │           │           │          │        │              │
├──────────────┴───────────┴───────────┴──────────┴────────┴──────────────┤
│                 CUSTOMER DOMAIN (1 table — post-fulfillment only)        │
│                              customer_master                             │
└──────────────────────────────────────────────────────────────────────────┘
```

**Configuration:** Set `SALES_AGENT_DB_PATH` environment variable to override the default path (`SuperAgent/data/sales_agent.db`).

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
        text status "pending/authorized/captured/failed"
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
        text status "pending/sent/failed"
        text channels_json
    }

    dedup_cache {
        text dedup_key PK
        text sent_at
    }
```

### How Entities Are Updated Along the Sales Conversation

The table below maps each conversation stage to the database operations performed. Each row represents a user turn that triggers one or more agent actions:

| Stage | Conversation Trigger | Agent | Tables Written | Operation |
|-------|---------------------|-------|---------------|-----------|
| **1. Greeting** | "Hi, I need internet for my office" | GreetingAgent | — | No DB writes. Returns phone script. |
| **2. Discovery** | "We're VoiceStream Networks at 123 Main St, Boston" | DiscoveryAgent | `accounts` | **INSERT** new company record with address, zip code, customer_id (UUID). |
| | *(agent asks for contact info)* | DiscoveryAgent | `contacts` | **INSERT** contact with name, title, email (required), phone (required). |
| | *(agent runs BANT qualification)* | DiscoveryAgent | `opportunities`, `insights` | **INSERT** opportunity with BANT scores; **INSERT** buying signals and pain points. |
| **3. Serviceability** | "Yes, check if we're serviceable" | ServiceabilityAgent | — | No DB writes. Stateless GIS/coverage lookup returns available infrastructure. |
| **4. Product** | "Show me Fiber 5G specs" | ProductAgent | — | No DB writes. Catalog tools read from hardcoded `PRODUCT_CATALOG` dict; RAG (`search_product_knowledge`) reads from ChromaDB vector store for documentation-level questions only. |
| **5. Quote** | "Give me pricing for Fiber 5G + SD-WAN" | OfferManagementAgent | `quotes` | **INSERT** quote with offer_id, items_json, pricing breakdown, term, discounts, totals. Status: `active`. Expires in 30 days. |
| **6. Order** | "Proceed with this quote" | OrderAgent | `carts`, `cart_items`, `orders`, `order_items` | **INSERT** cart + cart items from quote. **INSERT** order + order items. **UPDATE** `quotes.status` → `ordered`. Order status: `pending_payment`. Expires in 48h. |
| **7. Payment** | "Process payment" | PaymentAgent | `payments`, `orders` | **INSERT** payment record with credit score, authorization. **UPDATE** `orders.status` → `paid`. |
| **8. Scheduling** | "Schedule installation" | ServiceFulfillmentAgent | `fulfillments` | **INSERT** fulfillment record with appointment date. Status: `scheduled`. |
| **9. Dispatch** | *(triggered by scheduling)* | ServiceFulfillmentAgent | `fulfillments` | **UPDATE** dispatch_id, status → `dispatched`. |
| **10. Installation** | *(technician completes)* | ServiceFulfillmentAgent | `fulfillments` | **UPDATE** status → `installed`. |
| **11. Activation** | "Activate service" | ServiceFulfillmentAgent | `fulfillments`, `customer_master`, `accounts`, `orders` | **UPDATE** fulfillment with circuit_id, account_id, status → `activated`. **INSERT** `customer_master` record. **UPDATE** `accounts.Existing_Customer` → `Y`. **UPDATE** `orders.status` → `fulfilled`. |
| **Cross-cutting** | *(after each lifecycle event)* | CustomerCommunicationAgent | `notifications`, `dedup_cache` | **INSERT** notification (order confirmation, payment receipt, install reminder, activation notice). **INSERT** dedup key to prevent duplicates. |

### Entity Lifecycle State Machines

```
Quote:      active ──→ ordered ──→ (done)
                 └──→ expired (TTL: 30 days)

Cart:       active ──→ (consumed by order)
                 └──→ expired (TTL: 24 hours)

Order:      draft ──→ pending_payment ──→ paid ──→ fulfilled
                 │                    └──→ cancelled (TTL: 48h)
                 └──→ escalated (stuck >7 days)

Payment:    pending ──→ authorized ──→ captured
                 └──→ failed

Fulfillment: scheduled ──→ dispatched ──→ installed ──→ activated

Account:    Existing_Customer=N ──→ Existing_Customer=Y (on activation)
```

### Table-to-Agent Access Matrix

| Table | Discovery | Offer | Order | Payment | Fulfillment | Comms | DB Lifecycle |
|-------|:---------:|:-----:|:-----:|:-------:|:-----------:|:-----:|:------------:|
| **accounts** | R/W | — | — | — | R/W | — | R |
| **contacts** | R/W | — | — | — | — | — | R |
| **spend** | R | — | — | — | — | — | — |
| **opportunities** | R | — | — | — | — | — | — |
| **insights** | R/W | — | — | — | — | — | — |
| **actions** | R | — | — | — | — | — | — |
| **quotes** | — | R/W | W | — | — | — | W |
| **carts** | — | — | R/W | — | — | — | W |
| **cart_items** | — | — | R/W | — | — | — | — |
| **orders** | — | — | R/W | R/W | R/W | — | R/W |
| **order_items** | — | — | R/W | — | R | — | — |
| **payments** | — | — | — | R/W | — | — | R |
| **fulfillments** | — | — | — | — | R/W | — | R |
| **customer_master** | — | — | — | — | W | — | R |
| **notifications** | — | — | — | — | — | R/W | — |
| **dedup_cache** | — | — | — | — | — | R/W | — |

> **R** = SELECT, **W** = INSERT/UPDATE. **DB Lifecycle** = background `cleanup_stale_records()` for TTL enforcement.

### PaymentAgent Hardening

The PaymentAgent is implemented as a **deterministic, defense-in-depth payment workflow** rather than a simple "charge card" wrapper. The current design assumes payment is a critical transaction boundary and hardens the flow accordingly.

**Built-in safeguards include:**

- **Idempotency keys** on `process_payment()` so client retries return the original result instead of creating duplicate charges.
- **Duplicate-payment protection** that checks whether an order already has a completed payment before inserting a new one.
- A **payment state machine** with explicit transitions (`initiated → processing → completed/failed`) instead of writing a final status in one step.
- **Per-customer rate limiting** for payment attempts to reduce brute-force or accidental repeated submissions.
- **Velocity-aware approval checks** that simulate transaction-count and cumulative-spend controls before approval.
- An **immutable `payment_events` audit trail** so every status transition is recorded append-only for traceability.
- **Cryptographically random tokens and transaction identifiers** rather than predictable derived values.
- **CVV discard behavior** after validation so sensitive verification data is never stored.
- **Order-linked payment persistence** in unified SQLite, with `orders.status` updated to `paid` only after successful completion.
- **Session-state propagation** back into the ADK workflow so downstream agents can consume authoritative `payment_context` without re-inferring payment results from conversation text.

This means the PaymentAgent is designed as a **transaction-safe orchestration component**: the LLM handles conversational collection and routing, while the actual payment semantics are enforced through deterministic code paths, persisted state, and auditable transitions.

---

## Example Conversation Flows

### Discovery → Serviceability

```
User: "We're Crane.io at 123 Main St, Philadelphia PA"
  ↓ SuperAgent routes to DiscoveryAgent
  ↓ Discovery looks up company → adds to database (JSON)
  ↓ "Welcome! Would you like a serviceability check?"

User: "Yes"
  ↓ SuperAgent routes to ServiceabilityAgent
  ↓ Serviceability validates address via GIS API
  ↓ "✅ Serviceable with Fiber 1G/5G/10G"
```

### Product → Offer → Order

```
User: "Fiber 5G pricing with SD-WAN?"
  ↓ ProductAgent → Catalog lookup
  ↓ OfferAgent → Pricing calculation (JSON quote)
  ↓ "Quote #12345: $X,XXX/month"

User: "Proceed"
  ↓ OrderAgent → Create cart + order
  ↓ PaymentAgent → Credit check + authorization
  ↓ FulfillmentAgent → Schedule installation
  ↓ "Order confirmed! Install: Feb 20, 9 AM"
```

---

## 🗃️ RAG / ChromaDB Knowledge Base

The **ProductAgent** has **two independent data sources** — it is important to understand which is used when:

| Data Source | Tools | When Used |
|-------------|-------|-----------|
| **`PRODUCT_CATALOG` dict** (hardcoded in `product_tools.py`) | `get_product_by_id`, `list_available_products`, `compare_products`, `search_products_by_criteria`, `suggest_alternatives`, `get_best_value_product` | Product lookups, comparisons, filtering by speed/category |
| **ChromaDB vector store** (RAG) | `search_product_knowledge` | Documentation-level questions: SLA specifics, installation requirements, codec details, use-case fit |

> **Key nuance:** "Compare Fiber 1G vs 5G" or "Show me Fiber 5G details" → reads from the **hardcoded catalog dict**, NOT RAG. RAG is only invoked when the LLM determines the question needs documentation-level depth beyond the structured catalog (e.g., "What codec does Business Voice use?" or "Is coax suitable for a medical practice?").

### How RAG Works

When a customer asks a question like *"What is the uptime SLA for Business Fiber 10G?"* or *"Is coax suitable for a medical practice?"*, the ProductAgent calls the `search_product_knowledge` tool instead of a catalog tool. That tool performs a semantic similarity search over the vector store and returns the most relevant documentation chunks as context, which the agent uses to compose a grounded, accurate answer.

```
User question
  → ProductAgent decides: call search_product_knowledge()
  → Query encoded to 384-dim vector (sentence-transformers)
  → ChromaDB cosine similarity search → top 3 matching chunks
  → Formatted as [Source N: filename — section] context block
  → Agent reads context → composes natural-language response
```

### Initial Setup — Populate the Vector Store

```bash
pip install chromadb>=0.5.0 sentence-transformers>=2.7.0
cd ProductAgent
python scripts/ingest_knowledge.py
```

> **Note:** `ProductAgent/data/embeddings/` is in `.gitignore` — each developer runs ingestion locally after checkout. The embedding model (`all-MiniLM-L6-v2`, ~87MB) is auto-downloaded from HuggingFace on first run and cached at `~/.cache/huggingface/hub/`.

### RAG Pipeline — Detailed Flow

#### Files on Disk

```
ProductAgent/
├── data/
│   ├── product_docs/              ← 5 markdown knowledge files (858 lines total)
│   │   ├── fiber_internet.md      (SLAs, install process, use cases)
│   │   ├── coax_internet.md
│   │   ├── voice_services.md
│   │   ├── sd_wan.md
│   │   └── mobile_services.md
│   └── embeddings/                ← ChromaDB vector store output (3.2 MB, gitignored)
│       ├── chroma.sqlite3
│       └── <uuid>/                (HNSW binary vector data)
│
.hf_models/                        ← Embedding model (87 MB, gitignored, project root)
└── sentence-transformers/
    └── all-MiniLM-L6-v2/
        ├── model.safetensors      (neural network weights)
        ├── tokenizer.json         (WordPiece tokenizer)
        └── config.json            (architecture)
```

#### Local Development

1. **Model download** (one-time): `SentenceTransformer('all-MiniLM-L6-v2')` auto-downloads 87 MB to `~/.cache/huggingface/hub/` on first use
2. **Ingestion** (one-time or when docs change): `python ProductAgent/scripts/ingest_knowledge.py`
   - Reads `.md` files → splits by `##`/`###` headings → encodes chunks to 384-dim vectors → stores in ChromaDB
3. **Runtime**: First `search_product_knowledge()` call loads model from HF cache + opens ChromaDB. Subsequent calls reuse the singleton.

#### Docker / Cloud Run

1. **Build time**: `COPY ProductAgent/ ./ProductAgent/` brings pre-built embeddings. `COPY .hf_models/... /app/.hf_models/...` brings model files. **No Python/ingestion runs at build.**
2. **Runtime**: Model loads from `/app/.hf_models/all-MiniLM-L6-v2` (disk), ChromaDB opens from `/app/ProductAgent/data/embeddings/`. No network needed.

#### Why COPY Instead of RUN at Build Time?

Running `SentenceTransformer(...)` during `docker build` requires PyTorch initialization. On ARM Macs building linux/amd64 images via QEMU, this takes **10+ minutes**. COPY'ing raw files is instant.

| Step | Local Dev | Docker |
|------|-----------|--------|
| Model source | `~/.cache/huggingface/hub/` | `/app/.hf_models/all-MiniLM-L6-v2` (COPY'd) |
| Embeddings created | `python scripts/ingest_knowledge.py` | Never — COPY'd from local |
| Network needed | First model download only | Never |

### Embedding Model — Docker vs Local

The embedding model loading is environment-aware to avoid slow QEMU emulation during Docker builds:

| Environment | Model Source | Latency |
|-------------|-------------|---------|
| **Docker (Cloud Run)** | Pre-copied files at `/app/.hf_models/all-MiniLM-L6-v2` | 0s (COPY'd at build) |
| **Local dev** | HuggingFace cache (`~/.cache/huggingface/hub/`) | 0s (already cached) |
| **Fresh clone** | Auto-download from HuggingFace Hub | ~10s (one-time) |

**For Docker deployments:** The `.hf_models/` directory must exist locally (gitignored, 87MB). Set it up once:
```bash
mkdir -p .hf_models/sentence-transformers/all-MiniLM-L6-v2
cp -RLp ~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/*/* \
  .hf_models/sentence-transformers/all-MiniLM-L6-v2/
```

This avoids running Python/PyTorch under QEMU during `docker build` (which takes 10+ min on ARM Macs building linux/amd64 images).

---

## Sales Conversation Flow

Typical end-to-end flow:

1. **Discovery** — collect business/location context
2. **Serviceability** — verify address + infrastructure constraints
3. **Product** — recommend technically compatible products
4. **Offer Management** — compute quote JSON (pricing + discounts + totals)
5. **Order** — cart/checkout and contract creation
6. **Payment** — credit check + authorization
7. **Fulfillment** — schedule installation and activation
8. **Customer Comms** — confirmation and reminder notifications

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + Tailwind CSS |
| Backend | FastAPI + Python 3.12+ |
| Agent Framework | Google ADK 1.20.0+ |
| LLM | Gemini 3 Flash Preview (configured via `GEMINI_MODEL`) |
| Streaming | Server-Sent Events (SSE) |
| Database | SQLite (unified `sales_agent.db` — 17 tables, WAL mode) |
| Deployment | GCP Cloud Run |

---

## Repository Layout

```
ConversationalSalesAgent/
├── AGENTS.md                        # Complete architecture and standards guide
├── CLAUDE.md                        # Claude Code instructions
├── Scenarios.md                     # Test cases and conversation flows
├── GCP_DEPLOY.md                    # GCP Cloud Run deployment guide
├── Dockerfile                       # Multi-stage container build
├── entrypoint.sh                    # Container startup + GCS DB sync
├── SuperAgent/
│   ├── client/                      # React frontend
│   ├── server/                      # FastAPI backend
│   ├── super_agent/                 # ADK orchestrator + sub-agent wrappers
│   ├── start_servers.sh             # Local dev startup script
│   ├── start_cloud.sh               # Scale Cloud Run service up
│   ├── shutdown_cloud.sh            # Scale Cloud Run service to zero
│   └── deploy_cloud.sh              # Build, push, and redeploy to Cloud Run
├── DiscoveryAgent/
├── ServiceabilityAgent/
├── ProductAgent/
├── OfferManagement/
├── OrderAgent/
├── PaymentAgent/
├── ServiceFulfillmentAgent/
└── CustomerCommunicationAgent/
```

---

## Getting Started (Local)

### Prerequisites

- Python 3.12+
- Node.js 18+
- Gemini API key

### Using the Startup Script (Recommended)

```bash
# 1. Configure environment
cd SuperAgent/server
cp .env.example .env
# Edit .env: set GOOGLE_API_KEY and GEMINI_MODEL

# 2. Run both servers
cd ..
./start_servers.sh
```

The script auto-detects your `.venv`, cleans up stale processes on ports 8000 and 3000, starts the FastAPI backend and React frontend, and sets up per-agent log splitting.

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`

### View Logs

```bash
tail -f SuperAgent/logs/backend.log
tail -f SuperAgent/logs/agents/discovery_agent.log
tail -f SuperAgent/logs/agents/serviceability_agent.log
```

### Stop Servers

```bash
pkill -9 -f 'uvicorn main:app'
pkill -9 -f 'vite'
```

### Manual Startup

```bash
# Backend
cd SuperAgent/server
pip install -e ..
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd SuperAgent/client
npm install
npm run dev
```

---

## GCP Cloud Run Deployment

See [GCP_DEPLOY.md](./GCP_DEPLOY.md) for the full deployment guide including:

- One-time GCP project setup (project, APIs, bucket, secrets, IAM)
- Building and pushing the Docker image
- Deploying to Cloud Run
- Day-to-day operations (`start_cloud.sh`, `shutdown_cloud.sh`, `deploy_cloud.sh`)
- Estimated cost (~$6–21/month with min-instances=0)

---

## Documentation

| File | Purpose |
|------|---------|
| [AGENTS.md](./AGENTS.md) | Complete multi-agent system guide and ADK standards |
| [SuperAgent/README.md](./SuperAgent/README.md) | Runtime, API reference, and orchestration details |
| [GCP_DEPLOY.md](./GCP_DEPLOY.md) | GCP Cloud Run deployment guide |
| [Scenarios.md](./Scenarios.md) | Test cases and end-to-end conversation flows |
| Each `<Agent>/AGENTS.md` | Individual agent documentation |
