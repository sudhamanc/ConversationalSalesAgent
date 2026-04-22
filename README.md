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
| **Importlib isolation** | Sub-agents loaded without triggering `__init__.py` to avoid ADK parent-binding conflicts |

### How Agents Communicate

```
User Message → SuperAgent (intent analysis)
                  │
                  ├─ transfer_to_agent("discovery_agent")
                  │       └─ Discovery calls tools → returns JSON → responds to user
                  │
                  ├─ transfer_to_agent("serviceability_agent")
                  │       └─ Serviceability validates address via GIS → responds
                  │
                  └─ transfer_to_agent("offer_management_agent")
                          └─ Offer Mgmt computes pricing → returns quote JSON
```

- **Delegation is ADK-native** — SuperAgent declares `sub_agents=[...]` and ADK handles the handoff
- **No custom protocol** — ADK's built-in delegation replaces A2A or message queues
- **Session state is shared** — all agents read/write to ADK's session context, enabling multi-turn flows
- **Chained handoffs** — after DiscoveryAgent registers a company, the orchestrator auto-routes to ServiceabilityAgent

---

## Agent Registry

| Agent | Status | Responsibility | Infrastructure |
|-------|--------|---------------|----------------|
| **SuperAgent** | ✅ Active | Root orchestration and routing | — |
| **DiscoveryAgent** | ✅ Active | Prospect/company identification and BANT qualification | SQLite (Prospect DB) |
| **ServiceabilityAgent** | ✅ Active | PRE-SALE address validation and infrastructure capability | GIS API |
| **ProductAgent** | ✅ Active | Deterministic product catalog lookup and technical comparison | JSON Catalog |
| **OfferManagementAgent** | ✅ Active | Deterministic quote/pricing/discount computation | Pricing Engine API |
| **OrderAgent** | ✅ Active | Cart-first ordering, contract generation, order lifecycle | SQLite (Orders DB) |
| **PaymentAgent** | ✅ Active | Credit checks and payment authorization | Payment Gateway |
| **ServiceFulfillmentAgent** | ✅ Active | POST-SALE installation scheduling and activation | Scheduler API |
| **CustomerCommunicationAgent** | ✅ Active | Notification dispatch and communication history | Order DB |
| **GreetingAgent** | ✅ Active | Initial contact and conversational handling | Static content |
| **FAQAgent** | ✅ Active | Policy, support, and general product FAQ handling | Knowledge base |

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

The **ProductAgent** uses a vector database (ChromaDB) to answer deep product questions — SLAs, installation details, technology explanations, use-case fit, compliance — that are not captured in the structured product catalog.

### How It Works

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

> **Note:** `ProductAgent/data/embeddings/` is in `.gitignore` — each developer runs ingestion locally after checkout.

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
| Database | SQLite |
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
