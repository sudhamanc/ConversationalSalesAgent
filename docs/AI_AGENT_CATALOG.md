# 🤖 AI Agent Catalog & Architecture

> Comprehensive documentation of all AI agents in the B2B Agentic Sales Orchestration System

---

## 📋 Table of Contents

- [Agent Catalog](#-agent-catalog)
  - [Orchestration Layer](#orchestration-layer)
  - [Discovery Agents](#discovery-agents)
  - [Configuration Agents](#configuration-agents)
  - [Transaction Agents](#transaction-agents)
  - [Support Agents (New)](#support-agents-new)
- [Agent Architecture](#-agent-architecture)
  - [Super Agent & Sub-Agent Hierarchy](#super-agent--sub-agent-hierarchy)
  - [Agent Communication Matrix](#agent-communication-matrix)
- [Sales Flow Integration](#-sales-flow-integration)
  - [End-to-End Sales Journey](#end-to-end-sales-journey)
  - [Agent Activation by Sales Stage](#agent-activation-by-sales-stage)
- [Implementation Specifications](#-implementation-specifications)
- [Agent State Management](#-agent-state-management)

---

## 📚 Agent Catalog

### Orchestration Layer

| # | Agent Name | Role | Type | Source of Truth | Implementation | Status |
|---|------------|------|------|-----------------|----------------|--------|
| 1 | **🧠 Super Agent** | Central orchestrator; manages user state, intent routing, tone, guardrails; delegates tasks to sub-agents | `Orchestrator` | Session Context, Conversation Memory | **ADK** (Custom) | Existing |

---

### Discovery Agents

| # | Agent Name | Role | Type | Source of Truth | Implementation | Status |
|---|------------|------|------|-----------------|----------------|--------|
| 2 | **👤 Prospect Agent** | Identifies customer intent, extracts company details, contact persona, and business context | `Operational` | CRM System | **ADK** (Custom) | Existing |
| 3 | **📊 Lead Gen Agent** | Qualifies leads using BANT scoring (Budget, Authority, Need, Timeline); determines sales readiness | `Operational` | Scoring Logic, CRM | **ADK** (Custom) | Existing |

---

### Configuration Agents

| # | Agent Name | Role | Type | Source of Truth | Implementation | Status |
|---|------------|------|------|-----------------|----------------|--------|
| 4 | **📦 Product Agent** | Retrieves technical specifications, product features, hardware details, and compatibility info | `Info/RAG` | Vector DB (Product Manuals) | **ADK** (Custom) | Existing |
| 5 | **💰 Offer Mgmt Agent** | Calculates pricing, configures bundles, applies discounts, generates quotes | `Deterministic` | Pricing Engine API | **ADK** (Custom) | Existing |
| 6 | **🔧 Service Fulfillment Agent** | Validates address serviceability, checks network availability, schedules installation | `Deterministic` | GIS API, Scheduler API | **ADK** (Custom) | Existing |

---

### Transaction Agents

| # | Agent Name | Role | Type | Source of Truth | Implementation | Status |
|---|------------|------|------|-----------------|----------------|--------|
| 7 | **💳 Payment Agent** | Handles credit checks, payment method validation, billing setup | `Transactional` | Payment Gateway, Credit Bureau API | **ADK** (Custom) | Existing |
| 8 | **🛒 Order Agent** | Manages cart, generates contracts, processes final checkout, creates order records | `Transactional` | Order Database | **ADK** (Custom) | Existing |

---

### Support Agents (New)

| # | Agent Name | Role | Type | Source of Truth | Implementation | Status |
|---|------------|------|------|-----------------|----------------|--------|
| 9 | **❓ FAQ Agent** | Handles common pre-sales/post-sales questions; deflects routine queries from sales flow | `Info/RAG` | Knowledge Base Vector DB, FAQ Database | **ADK** (Custom) | Recommended |
| 10 | **🆘 Escalation Agent** | Detects escalation triggers; summarizes conversation context; transfers to human agents | `Orchestrator` | Agent Availability System, Ticket Queue | **ADK** (Custom) | Recommended |
| 11 | **📅 Scheduling Agent** | Books demos, consultations, site surveys, installations; manages calendar availability | `Transactional` | Calendar API (Google, Microsoft 365, Calendly) | **ADK** (Custom) | Recommended |
| 12 | **📧 Nurture Agent** | Manages automated follow-ups for stalled deals, quote reminders, lead warming campaigns | `Operational` | CRM, Email Gateway, SMS API, Quote Database | **LangGraph** | Recommended |
| 13 | **🤝 Retention Agent** | Proactive renewal handling, churn prevention, upsell recommendations based on usage | `Operational` | CRM, Usage Analytics, Billing System | **LangGraph** | Recommended |
| 14 | **📊 Insights Agent** | Provides usage analytics, ROI summaries, optimization recommendations | `Info/RAG` | Analytics Platform, Billing API, Usage Database | **ADK** (Custom) | Recommended |

---

## 🏗️ Agent Architecture

### Super Agent & Sub-Agent Hierarchy

```
                                    ┌─────────────────────────────────────┐
                                    │         🧠 SUPER AGENT              │
                                    │    (Orchestrator / Router / Guard)  │
                                    └──────────────────┬──────────────────┘
                                                       │
                                                       │ Delegates & Coordinates
                                                       │
         ┌─────────────────┬─────────────────┬─────────┴─────────┬─────────────────┬─────────────────┐
         │                 │                 │                   │                 │                 │
         ▼                 ▼                 ▼                   ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│   DISCOVERY     │ │ CONFIGURATION│ │  TRANSACTION   │ │    SUPPORT      │ │  ENGAGEMENT │ │   ANALYTICS     │
│   CLUSTER       │ │   CLUSTER   │ │    CLUSTER     │ │    CLUSTER      │ │   CLUSTER   │ │    CLUSTER      │
├─────────────────┤ ├─────────────┤ ├─────────────────┤ ├─────────────────┤ ├─────────────┤ ├─────────────────┤
│ 👤 Prospect     │ │ 📦 Product  │ │ 💳 Payment      │ │ ❓ FAQ          │ │ 📧 Nurture  │ │ 📊 Insights     │
│ 📊 Lead Gen     │ │ 💰 Offer Mgmt│ │ 🛒 Order        │ │ 🆘 Escalation   │ │ 🤝 Retention│ │                 │
│                 │ │ 🔧 Svc Fulfill│ │                │ │ 📅 Scheduling   │ │             │ │                 │
└─────────────────┘ └─────────────┘ └─────────────────┘ └─────────────────┘ └─────────────┘ └─────────────────┘
```

### Agent Communication Matrix

| From \ To | Super | Prospect | Lead Gen | Product | Offer Mgmt | Svc Fulfill | Payment | Order | FAQ | Escalation | Scheduling | Nurture | Retention | Insights |
|-----------|:-----:|:--------:|:--------:|:-------:|:----------:|:-----------:|:-------:|:-----:|:---:|:----------:|:----------:|:-------:|:---------:|:--------:|
| **Super Agent** | - | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Prospect** | ✅ | - | ✅ | - | - | - | - | - | - | ✅ | ✅ | ✅ | - | - |
| **Lead Gen** | ✅ | ✅ | - | - | ✅ | - | - | - | - | ✅ | - | ✅ | - | - |
| **Product** | ✅ | - | - | - | ✅ | ✅ | - | - | ✅ | ✅ | - | - | - | ✅ |
| **Offer Mgmt** | ✅ | - | ✅ | ✅ | - | ✅ | ✅ | ✅ | - | ✅ | - | ✅ | ✅ | - |
| **Svc Fulfill** | ✅ | ✅ | - | ✅ | ✅ | - | - | ✅ | - | ✅ | ✅ | - | - | - |
| **Payment** | ✅ | - | - | - | ✅ | - | - | ✅ | - | ✅ | - | - | ✅ | - |
| **Order** | ✅ | - | - | - | ✅ | ✅ | ✅ | - | - | ✅ | ✅ | - | ✅ | ✅ |
| **FAQ** | ✅ | - | - | ✅ | - | - | - | - | - | ✅ | - | - | - | - |
| **Escalation** | ✅ | - | - | - | - | - | - | - | - | - | - | - | - | - |
| **Scheduling** | ✅ | ✅ | - | - | - | ✅ | - | - | - | ✅ | - | - | - | - |
| **Nurture** | ✅ | ✅ | ✅ | - | ✅ | - | - | - | - | ✅ | ✅ | - | - | - |
| **Retention** | ✅ | - | - | - | ✅ | - | ✅ | ✅ | - | ✅ | - | - | - | ✅ |
| **Insights** | ✅ | - | - | ✅ | - | - | - | ✅ | - | ✅ | - | - | - | - |

---

## 🔄 Sales Flow Integration

### End-to-End Sales Journey

```
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                         B2B SMB SALES JOURNEY WITH AGENTS
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

    STAGE 1              STAGE 2              STAGE 3              STAGE 4              STAGE 5              STAGE 6
    AWARENESS            DISCOVERY            CONFIGURATION        TRANSACTION          FULFILLMENT          RETENTION
    ─────────            ─────────            ─────────────        ───────────          ───────────          ─────────

    ┌─────────┐         ┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐
    │ Customer│         │ Customer│          │ Customer│          │ Customer│          │ Customer│          │ Customer│
    │ Inquiry │         │ Details │          │ Solution│          │ Purchase│          │ Onboard │          │ Renew   │
    └────┬────┘         └────┬────┘          └────┬────┘          └────┬────┘          └────┬────┘          └────┬────┘
         │                   │                    │                    │                    │                    │
         ▼                   ▼                    ▼                    ▼                    ▼                    ▼
    ┌─────────┐         ┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐
    │❓ FAQ   │         │👤Prospect│          │📦Product │          │💳Payment │          │🔧Svc     │          │🤝Retain │
    │  Agent  │         │  Agent  │          │  Agent  │          │  Agent  │          │ Fulfill  │          │  Agent  │
    └────┬────┘         └────┬────┘          └────┬────┘          └────┬────┘          └────┬────┘          └────┬────┘
         │                   │                    │                    │                    │                    │
         │                   ▼                    ▼                    ▼                    ▼                    │
         │              ┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐               │
         │              │📊Lead   │          │💰Offer  │          │🛒 Order │          │📅Sched  │               │
         │              │  Gen    │          │  Mgmt   │          │  Agent  │          │  Agent  │               │
         │              └────┬────┘          └────┬────┘          └─────────┘          └─────────┘               │
         │                   │                    │                                                              │
         │                   │                    ▼                                                              │
         │                   │               ┌─────────┐                                                         │
         │                   │               │🔧Svc    │                                                         │
         │                   │               │ Fulfill │                                                         │
         │                   │               └─────────┘                                                         │
         │                   │                                                                                   │
         ▼                   ▼                    ▼                    ▼                    ▼                    ▼
    ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                                        │
                                              📧 NURTURE AGENT
                                         (Parallel - Stalled Deal Recovery)
                                                        │
                                              📊 INSIGHTS AGENT
                                           (Parallel - Usage Analytics)
                                                        │
                                              🆘 ESCALATION AGENT
                                            (On-Demand - Human Handoff)
    ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

### Agent Activation by Sales Stage

| Sales Stage | Primary Agents | Supporting Agents | Trigger Events |
|-------------|----------------|-------------------|----------------|
| **1. Awareness** | ❓ FAQ Agent | 🆘 Escalation | Customer lands on chat, asks general questions |
| **2. Discovery** | 👤 Prospect Agent, 📊 Lead Gen Agent | 📅 Scheduling Agent | Customer expresses interest, provides business context |
| **3. Configuration** | 📦 Product Agent, 💰 Offer Mgmt Agent, 🔧 Service Fulfillment Agent | ❓ FAQ Agent | Customer asks about products, requests quote, address check |
| **4. Transaction** | 💳 Payment Agent, 🛒 Order Agent | 🆘 Escalation Agent | Customer ready to purchase, credit check, contract generation |
| **5. Fulfillment** | 🔧 Service Fulfillment Agent, 📅 Scheduling Agent | 🛒 Order Agent | Order confirmed, installation scheduling |
| **6. Retention** | 🤝 Retention Agent, 📊 Insights Agent | 💰 Offer Mgmt Agent | Contract nearing expiry, usage patterns, upsell triggers |
| **Parallel (Always Active)** | 📧 Nurture Agent | 📊 Lead Gen Agent, 💰 Offer Mgmt | Quote sent but no response, lead gone cold |

---

## ⚙️ Implementation Specifications

### Framework Selection by Agent

| Agent | Framework | Justification |
|-------|-----------|---------------|
| 🧠 Super Agent | **ADK** (Custom) | Central orchestration requires tight control over routing, guardrails, and session management |
| 👤 Prospect Agent | **ADK** (Custom) | Simple extraction pattern; tool-based CRM lookups |
| 📊 Lead Gen Agent | **ADK** (Custom) | Rule-based BANT scoring; deterministic logic |
| 📦 Product Agent | **ADK** (Custom) | RAG-based retrieval; fits ADK tool pattern |
| 💰 Offer Mgmt Agent | **ADK** (Custom) | Deterministic pricing API calls; no complex state |
| 🔧 Service Fulfillment Agent | **ADK** (Custom) | Deterministic GIS/scheduler API calls |
| 💳 Payment Agent | **ADK** (Custom) | Deterministic payment gateway integration |
| 🛒 Order Agent | **ADK** (Custom) | Transactional database operations; tool-centric |
| ❓ FAQ Agent | **ADK** (Custom) | RAG-based retrieval; simple request-response |
| 🆘 Escalation Agent | **ADK** (Custom) | State handoff; integrates with Super Agent |
| 📅 Scheduling Agent | **ADK** (Custom) | Calendar API tool calls; deterministic |
| 📧 Nurture Agent | **LangGraph** | Complex state machine with delays, conditional branching, multi-channel sequencing |
| 🤝 Retention Agent | **LangGraph** | Cyclical negotiation flows; multi-turn reasoning with loops |
| 📊 Insights Agent | **ADK** (Custom) | Data retrieval and summarization; tool-centric |

### ADK Base Class Contract

All ADK agents must implement:

```python
class BaseAgent:
    name: str                    # Unique agent identifier
    role: str                    # Agent role description
    type: AgentType              # Orchestrator | Operational | Info/RAG | Deterministic | Transactional
    tools: List[Tool]            # Available tools for this agent
    source_of_truth: str         # Primary data source
    
    def process(self, context: Context) -> AgentResponse
    def log_structured(self, event: Event) -> None
    def handle_error(self, error: Exception) -> FallbackResponse
```

### LangGraph State Machine Contract

Nurture and Retention agents implement:

```python
class StatefulAgent:
    graph: StateGraph            # LangGraph state machine
    nodes: List[Node]            # Processing nodes
    edges: List[Edge]            # Conditional transitions
    checkpointer: Checkpointer   # State persistence
    
    def invoke(self, state: AgentState) -> AgentState
    def stream(self, state: AgentState) -> Iterator[AgentState]
```

---

## 📊 Agent State Management

### State Ownership

| Agent | State Owned | State Format | Persistence |
|-------|-------------|--------------|-------------|
| 🧠 Super Agent | Conversation context, user session, routing history | JSON | Redis (Session) |
| 👤 Prospect Agent | Extracted customer profile | JSON | CRM Sync |
| 📊 Lead Gen Agent | BANT scores, qualification status | JSON | CRM Sync |
| 📦 Product Agent | None (stateless) | - | - |
| 💰 Offer Mgmt Agent | Active quote, bundle configuration | JSON | Quote DB |
| 🔧 Service Fulfillment Agent | Serviceability cache | JSON | TTL Cache |
| 💳 Payment Agent | Credit check result, payment method | JSON | Session |
| 🛒 Order Agent | Cart, contract draft | JSON | Order DB |
| ❓ FAQ Agent | None (stateless) | - | - |
| 🆘 Escalation Agent | Handoff context summary | JSON | Ticket System |
| 📅 Scheduling Agent | Pending appointments | JSON | Calendar DB |
| 📧 Nurture Agent | Campaign state, touchpoint history | JSON | LangGraph Checkpointer (SQLite) |
| 🤝 Retention Agent | Negotiation state, offer history | JSON | LangGraph Checkpointer (SQLite) |
| 📊 Insights Agent | None (stateless) | - | - |

### A2A Protocol Message Format

```json
{
  "message_id": "uuid",
  "timestamp": "ISO8601",
  "from_agent": "agent_name",
  "to_agent": "agent_name",
  "action": "request | response | notify",
  "payload": {
    "intent": "string",
    "context": {},
    "data": {}
  },
  "trace_id": "uuid",
  "correlation_id": "uuid"
}
```

---

## 🔒 Guardrails & Constraints

| Agent | Guardrails |
|-------|------------|
| 🧠 Super Agent | No competitor mentions; no pricing without Offer Mgmt confirmation; escalation on low confidence |
| 💰 Offer Mgmt Agent | Maximum discount limits; approval workflow for exceptions |
| 💳 Payment Agent | PCI compliance; no card data in logs |
| 🛒 Order Agent | Contract terms validation; legal clause requirements |
| 🤝 Retention Agent | Discount authority limits; manager approval for high-value exceptions |
| 🆘 Escalation Agent | Mandatory human handoff on legal/compliance queries |

---

## 📈 Agent Metrics & Observability

| Metric Category | Metrics Tracked | Agents |
|-----------------|-----------------|--------|
| **Latency** | Response time (p50, p95, p99) | All |
| **Throughput** | Requests per minute | All |
| **Error Rate** | Failures / Total requests | All |
| **Deflection Rate** | Queries handled without escalation | FAQ, Super Agent |
| **Conversion** | Quotes → Orders | Offer Mgmt, Order |
| **BANT Score Distribution** | Lead quality | Lead Gen |
| **Churn Prevention** | Retention saves | Retention |
| **Follow-up Effectiveness** | Re-engagement rate | Nurture |

---

## 📎 Appendix: Agent Tool Inventory

| Agent | Tools |
|-------|-------|
| 🧠 Super Agent | `route_intent`, `get_session`, `apply_guardrail`, `log_trace` |
| 👤 Prospect Agent | `extract_entity`, `crm_lookup`, `crm_upsert` |
| 📊 Lead Gen Agent | `calculate_bant`, `get_scoring_rules`, `update_lead_status` |
| 📦 Product Agent | `vector_search`, `get_product_specs`, `compare_products` |
| 💰 Offer Mgmt Agent | `calculate_price`, `apply_discount`, `generate_quote`, `get_bundles` |
| 🔧 Service Fulfillment Agent | `check_serviceability`, `get_install_slots`, `schedule_install` |
| 💳 Payment Agent | `run_credit_check`, `validate_payment_method`, `setup_billing` |
| 🛒 Order Agent | `add_to_cart`, `generate_contract`, `submit_order`, `get_order_status` |
| ❓ FAQ Agent | `search_knowledge_base`, `get_faq_answer` |
| 🆘 Escalation Agent | `summarize_context`, `check_agent_availability`, `create_ticket`, `transfer_session` |
| 📅 Scheduling Agent | `get_availability`, `book_appointment`, `send_confirmation`, `reschedule` |
| 📧 Nurture Agent | `get_stalled_leads`, `send_email`, `send_sms`, `update_touchpoint`, `check_engagement` |
| 🤝 Retention Agent | `get_expiring_contracts`, `analyze_usage`, `generate_retention_offer`, `process_renewal` |
| 📊 Insights Agent | `get_usage_summary`, `calculate_roi`, `generate_report`, `get_benchmarks` |

---

*Document Version: 1.0*  
*Last Updated: February 2, 2026*
