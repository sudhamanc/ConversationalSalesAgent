# 🤖 B2B Conversational Sales Agent

ADK-powered multi-agent orchestration for end-to-end B2B telecom sales conversations.

**Drexel University – Senior Design Project**  
**Winter/Spring 2026**

---

## 📌 What This Project Is

This repository implements a **Super Agent + Sub-Agent** architecture using **Google ADK**.
The system routes each customer turn to specialized agents for discovery, serviceability, product fit, pricing, order creation, payment, fulfillment, and customer communications.

The core design principle is:
- **LLM reasoning for orchestration and conversation**
- **Deterministic tools/APIs for critical business data** (coverage, pricing, order/payment/fulfillment 

## 🏗️ Architecture

### Layers

1. **Presentation Layer**
   - React 19 + Vite client
   - SSE streaming chat UI

2. **Orchestration Layer**
   - `SuperAgent` root orchestrator (`super_sales_agent`)
   - Intent routing, context/state, guardrails

3. **Sub-Agent Layer**
   - Specialized ADK agents loaded into SuperAgent

4. **Infrastructure Layer**
   - SQLite data stores
   - Deterministic tool modules and external API wrappers (GIS, pricing/payment/scheduler stubs)

### Orchestration Pattern

- SuperAgent declares sub-agents in `sub_agents=[...]`.
- ADK performs native delegation based on orchestrator instructions.
- Sub-agents execute tools for deterministic operations.

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

### Quote Payload Shape (Offer Management)

```json
{
  "offer_id": "OFF-XXXXXXXXXX",
  "items": [
    {
      "product_id": "FIB-5G",
      "price_points": { "unit_price": 599.0, "extended_price": 599.0 },
      "discount": 59.9,
      "final_price": 539.1
    }
  ],
  "subtotal": 599.0,
  "total_discount": 59.9,
  "total_price": 539.1
}
```

---

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
