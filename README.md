# 🤖 B2B Conversational Sales Agent

**A Multi-Agent Orchestration System for B2B Telecom Sales**

ADK-powered multi-agent orchestration for end-to-end B2B telecom sales conversations.

**Drexel University – Senior Design Project**  
**Winter/Spring 2026**

---

## 📌 What This Project Is

This repository implements a **multi-agent orchestration system** — a hierarchical architecture where a central **SuperAgent** coordinates 10 specialized sub-agents to automate the full B2B telecom sales lifecycle, from initial prospect discovery through order fulfillment.

Built on **Google ADK (Agent Development Kit)** with **Google Gemini** as the backbone LLM, the system enforces a strict separation between:

- **LLM-driven reasoning** — intent classification, conversational routing, natural language generation
- **Deterministic tool execution** — database lookups, pricing calculations, address validation, payment processing

This separation is the core architectural principle: the LLM decides *what* to do, but *critical business data* (addresses, prices, orders) is always sourced from deterministic tools, never hallucinated.

---

## 🧠 Multi-Agent Orchestration Architecture

### What Makes This a Multi-Agent System?

Unlike a single-agent chatbot with many tools, this system decomposes the sales domain into **10 autonomous agents**, each with:

- Its own **system prompt** (domain-specific instructions)
- Its own **tools** (deterministic functions for its domain)
- Its own **model configuration** (temperature, sampling parameters)
- **Independent reasoning** within its delegated scope

A central **SuperAgent** acts as the orchestrator — it never answers the user directly. Instead, it analyzes each message, determines which sub-agent should handle it, and delegates via ADK's native `transfer_to_agent` mechanism.

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
| **Separation of concerns** | Each agent owns exactly one domain (e.g., pricing is *only* in OfferManagementAgent) |
| **Zero-hallucination for critical data** | Addresses, prices, orders always come from deterministic tools, never LLM generation |
| **Router-only orchestrator** | SuperAgent classifies intent and delegates — it never generates user-facing text |
| **Temperature-stratified agents** | Conversational agents use temp 0.7; deterministic agents use temp 0.0 |
| **Structured data contracts** | Tools return JSON (not prose) to prevent LLM rephrasing of critical values |
| **Importlib isolation** | Sub-agents loaded without triggering their `__init__.py` to avoid ADK parent-binding conflicts |

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
- **No custom protocol** — we don't implement A2A or message queues; ADK's built-in delegation is sufficient
- **Session state is shared** — all agents read/write to ADK's session context, enabling multi-turn flows
- **Chained handoffs** — after DiscoveryAgent registers a company, the orchestrator auto-routes to ServiceabilityAgent on the next user turn

---

## 🤖 Active Agent Registry

| Agent | Status | Primary Responsibility |
|---|---|---|
| SuperAgent | ✅ Active | Root orchestration and routing |
| DiscoveryAgent | ✅ Active | Prospect/company identification and qualification context |
| ServiceabilityAgent | ✅ Active | PRE-SALE address validation and infrastructure capability |
| ProductAgent | ✅ Active | Deterministic product catalog lookup and technical comparison |
| OfferManagementAgent | ✅ Active | Deterministic quote/pricing/discount computation |
| OrderAgent | ✅ Active | Cart-first ordering, contract generation, order lifecycle |
| PaymentAgent | ✅ Active | Credit checks and payment authorization |
| ServiceFulfillmentAgent | ✅ Active | POST-SALE installation scheduling and activation workflow |
| CustomerCommunicationAgent | ✅ Active | Notification dispatch and communication history |
| GreetingAgent | ✅ Active | Greeting/intro conversational handling |
| FAQAgent | ✅ Active | Policy/support/general product FAQ handling |

---

## 🔄 Sales Conversation Flow

Typical production-intent flow:

1. Discovery: collect business/location context
2. Serviceability: verify address + infra constraints
3. Product: recommend technically compatible products
4. Offer Management: compute quote JSON (pricing + discounts + totals)
5. Order: cart/checkout and contract creation
6. Payment: credit + authorization
7. Fulfillment: schedule/install activation
8. Customer Comms: confirmation/reminder notifications


## 🧰 Technology Stack

### Core
- Python 3.12+
- FastAPI
- Google ADK (multi-agent runtime)
- Google Gemini models (configured via `GEMINI_MODEL`)
- React 19 + Vite + Tailwind CSS
- SQLite

### Runtime/Integration
- SSE for token streaming between backend and frontend
- ADK sub-agent delegation (no custom A2A protocol implementation required)
- MCP-style deterministic tool integration for local/external data sources

---

## 📁 Repository Layout (High-Level)

```text
ConversationalSalesAgent/
├── AGENTS.md
├── CLAUDE.md
├── Scenarios.md
├── SuperAgent/
│   ├── client/                    # React UI
│   ├── server/                    # FastAPI backend
│   └── super_agent/               # ADK orchestrator + sub-agent wrappers
├── DiscoveryAgent/
├── ServiceabilityAgent/
├── ProductAgent/
├── OfferManagement/
├── OrderAgent/
├── PaymentAgent/
├── ServiceFulfillmentAgent/
├── CustomerCommunicationAgent/
└── BootStrapAgent/
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Gemini API key (for model access)

### 1) Backend

```bash
cd SuperAgent/server
pip install -e ..
cp .env.example .env
# set GOOGLE_API_KEY and GEMINI_MODEL in .env
uvicorn main:app --reload
```

### 2) Frontend

```bash
cd SuperAgent/client
npm install
npm run dev
```

### 3) Open App

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`

---

## 🧪 Testing

Run focused suites from repo root with your virtualenv Python.

Examples:

```bash
# ProductAgent focused tests
GEMINI_MODEL=gemini-2.0-flash ./venv/bin/python -m pytest ProductAgent/tests/test_tools.py ProductAgent/tests/test_agent.py -q

# SuperAgent routing/integration smoke tests
./venv/bin/python -m pytest SuperAgent/test_routing.py -q
```

For end-to-end positive/negative scenario coverage, see:
- `Scenarios.md`

---

## 🔐 Security Notes (Demo Scope)

This is an academic/demo environment:
- Uses mock/test data patterns in several flows
- Not production-hardened for PCI/PII requirements

For production, implement full authN/authZ, secret management, encryption, compliance controls, and operational observability.

---

## 📚 Project Documentation

- Root architecture and standards: `AGENTS.md`
- SuperAgent implementation/runtime details: `SuperAgent/README.md`
- Agent-specific guidance: each `<Agent>/AGENTS.md`
- Validation scenarios: `Scenarios.md`

---

## 📄 License

MIT (see `LICENSE` if present in your distribution).

---

<p align="center"><strong>Built for deterministic, multi-agent B2B sales orchestration.</strong></p>

---

## 🎨 Presentation Slides (Optional)

The `Slidev/` directory contains a [Slidev](https://sli.dev) presentation for the project progress report. This is **optional** and not required to run the sales agent system.

### Setup

```bash
cd Slidev
npm install
```

### Run (local preview)

```bash
cd Slidev
npm run dev
# Opens at http://localhost:3030
```

### Export to PPTX

```bash
cd Slidev
npx slidev export --format pptx --output ./progress-report.pptx
```

> **Note:** Exporting to PPTX requires `playwright-chromium`. Install it with `npm i -D playwright-chromium` if not already present.
