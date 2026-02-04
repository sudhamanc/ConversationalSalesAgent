

# B2B Agentic Sales Orchestration System
## Sales Scenarios &amp; Academic Milestone Plan

**Drexel University – Senior Design Project**  
**Winter Quarter (Jan – Mar 2026) | Spring Quarter (Apr – Jun 2026)**


## Project Overview

This document outlines the sales scenarios and milestone plan for the B2B Conversational Sales Agent multi-agent system. The scope is designed for an academic senior design project demonstrating a functional Multi-Agent System (MAS) with the following 8 agents:

| Agent | Type | Purpose |
|-------|------|---------|
| 🧠 **Super Agent** | Orchestrator | Routes intents, manages conversation flow |
| 👤 **Prospect Agent** | Operational | Extracts customer/company details |
| 📊 **Lead Gen Agent** | Operational | BANT scoring &amp; lead qualification |
| 📦 **Product Agent** | Info/RAG | Retrieves product specs from vector DB |
| 💰 **Offer Mgmt Agent** | Deterministic | Calculates pricing &amp; bundles |
| 🛒 **Order Agent** | Transactional | Manages cart &amp; contract generation |
| 💳 **Payment Agent** | Transactional | Mock credit checks |
| 🔧 **Service Fulfillment Agent** | Deterministic | Address serviceability &amp; scheduling |


## Agent Development Timeline

| Agent | Winter Qtr | Spring Qtr |
|-------|------------|------------|
| 🧠 Super Agent | ✅ Basic routing | ✅ Full orchestration |
| 👤 Prospect Agent | ✅ Complete | — |
| 📊 Lead Gen Agent | ✅ Basic BANT | ✅ Enhanced scoring |
| 📦 Product Agent | ✅ Complete | — |
| 💰 Offer Mgmt Agent | ✅ Basic routing | ✅ Complete |
| 🛒 Order Agent | ✅ Basic routing | ✅ Complete |
| 💳 Payment Agent | ✅ Basic routing| ✅ Complete |
| 🔧 Service Fulfillment Agent | ✅ Serviceability | ✅ Scheduling |

---

## Sales Scenarios (Expanded)

### Scenario 1: Address-Based Lookup (New Prospect)

**User Input:** Agent types an address into the chatbot  
**Example:** *"Check serviceability for 123 Main Street, Philadelphia, PA 19104"*

**Flow:**
1. **Super Agent** → Receives input, identifies intent as "serviceability check"
2. **Prospect Agent** → Extracts address details (street, city, zip)
3. **Service Fulfillment Agent** → Calls mock GIS API to check serviceability
4. **Decision Point:**
   - **NOT Serviceable** → Return "Address not in service area" message
   - **Serviceable** → Continue to step 5
5. **Product Agent** → Retrieves available products for that location (via RAG/Vector DB)
6. **Offer Mgmt Agent** → Creates a product offering with pricing
7. **Super Agent** → Returns formatted response with available products and pricing

**Agents Demonstrated:** Super Agent, Prospect Agent, Service Fulfillment Agent, Product Agent, Offer Mgmt Agent

---

### Scenario 2: Address-Based Lookup (Existing Customer)

**User Input:** Agent types an address that matches an existing customer  
**Example:** *"Look up 456 Market Street, Philadelphia, PA 19103"*

**Flow:**
1. **Super Agent** → Receives input, identifies intent as "customer lookup"
2. **Prospect Agent** → Extracts address, queries mock CRM for existing customer
3. **Decision Point:**
   - **Existing Customer Found** → Continue to step 4
   - **Not Found** → Follow Scenario 1 flow (new prospect)
4. **Product Agent** → Retrieves customer's current products/services
5. **Offer Mgmt Agent** → Identifies upsell/cross-sell opportunities, creates upgrade offer
6. **Super Agent** → Returns current services + recommended upgrades with pricing

**Agents Demonstrated:** Super Agent, Prospect Agent, Product Agent, Offer Mgmt Agent

---

### Scenario 3: Business Name Lookup (New Prospect)

**User Input:** Agent types a business name into the chatbot  
**Example:** *"Find services for Acme Corporation"*

**Flow:**
1. **Super Agent** → Receives input, identifies intent as "business lookup"
2. **Prospect Agent** → Searches mock CRM by business name
3. **Decision Point:**
   - **Business NOT Found** → Continue to step 4
   - **Business Found** → Follow Scenario 4 flow
4. **Super Agent** → Prompts for business address
5. **Prospect Agent** → Extracts provided address
6. **Service Fulfillment Agent** → Checks address serviceability
7. **Lead Gen Agent** → Performs basic BANT qualification (mock scoring)
8. **Product Agent** → Retrieves product catalog
9. **Offer Mgmt Agent** → Creates tailored product offering
10. **Super Agent** → Returns serviceability status + product offering

**Agents Demonstrated:** Super Agent, Prospect Agent, Service Fulfillment Agent, Lead Gen Agent, Product Agent, Offer Mgmt Agent

---

### Scenario 4: Business Name Lookup (Existing Customer)

**User Input:** Agent types a business name that exists in the system  
**Example:** *"Look up TechStart Inc"*

**Flow:**
1. **Super Agent** → Receives input, identifies intent as "customer lookup"
2. **Prospect Agent** → Searches mock CRM, finds existing customer record
3. **Product Agent** → Retrieves current services for the customer
4. **Lead Gen Agent** → Assesses expansion potential (additional locations, upgrades)
5. **Offer Mgmt Agent** → Generates upsell/bundle recommendations
6. **Super Agent** → Returns customer profile + current services + recommended offerings

**Agents Demonstrated:** Super Agent, Prospect Agent, Product Agent, Lead Gen Agent, Offer Mgmt Agent

---

### Scenario 5: Product Information Query

**User Input:** Agent asks about a specific product  
**Example:** *"What speeds are available with Business Internet Pro?"*

**Flow:**
1. **Super Agent** → Identifies intent as "product inquiry"
2. **Product Agent** → Queries ChromaDB (RAG) for product specifications
3. **Super Agent** → Returns detailed product information

**Agents Demonstrated:** Super Agent, Product Agent

---

### Scenario 6: End-to-End Order Flow (Demo Scenario)

**User Input:** Complete sales cycle from inquiry to order  
**Example:** *"I need internet service for my new office at 789 Tech Park Drive"*

**Flow:**
1. **Super Agent** → Orchestrates full sales flow
2. **Prospect Agent** → Extracts business details and address
3. **Lead Gen Agent** → Qualifies the lead (BANT scoring)
4. **Service Fulfillment Agent** → Confirms serviceability
5. **Product Agent** → Retrieves matching products
6. **Offer Mgmt Agent** → Creates pricing quote
7. **Payment Agent** → Performs mock credit check
8. **Order Agent** → Generates order/contract JSON
9. **Service Fulfillment Agent** → Schedules mock installation date
10. **Super Agent** → Returns complete order confirmation

**Agents Demonstrated:** ALL 8 AGENTS

---

## Academic Milestone Plan

### WINTER QUARTER (January – March 2026)
**Focus: Foundation &amp; Core Agent Development**

#### Weeks 1-3: Infrastructure &amp; Setup
| Task | Deliverable |
|------|-------------|
| Set up React Frontend with chat interface | Working chat UI |
| Set up FastAPI Backend with WebSocket | Real-time message streaming |
| Implement ADK Base Class | Logging, memory, tool framework |
| Set up ChromaDB for RAG | Vector database initialized |
| Create mock APIs (CRM, GIS) | JSON-based mock data services |

#### Weeks 4-6: Core Agents (Phase 1)
| Task | Deliverable |
|------|-------------|
| Build **Super Agent** with basic routing | Intent classification working |
| Build **Prospect Agent** | Address/name extraction functional |
| Build **Product Agent** with RAG | Can answer product questions |
| Ingest sample product PDFs into ChromaDB | Product Q&amp;A working |

#### Weeks 7-9: Discovery &amp; Serviceability Agents
| Task | Deliverable |
|------|-------------|
| Build **Service Fulfillment Agent** | Mock GIS serviceability check working |
| Build **Lead Gen Agent** | Basic BANT scoring logic |
| Implement Scenario 1 (Address lookup - new) | End-to-end flow functional |
| Implement Scenario 5 (Product inquiry) | Product Q&amp;A demo ready |

#### Week 10: Winter Quarter Deliverable
| Task | Deliverable |
|------|-------------|
| Integration testing | All Q1 agents working together |
| Demo preparation | **Scenario 1 &amp; 5 fully functional** |
| Documentation | Technical documentation updated |

**🎯 Winter Quarter Demo:**  
*A functional Chat UI where a sales agent can:*
- *Ask product questions and get RAG-powered answers*
- *Enter an address and check serviceability*
- *See available products for serviceable addresses*

---

### SPRING QUARTER (April – June 2026)
**Focus: Transaction Agents &amp; Full Orchestration**

#### Weeks 1-3: Deterministic Agents
| Task | Deliverable |
|------|-------------|
| Build **Offer Mgmt Agent** | Pricing/bundle logic working |
| Build **Payment Agent** | Mock credit check functional |
| Implement Scenario 2 (Existing customer address) | Upsell flow working |
| Implement Scenario 4 (Existing customer by name) | Customer lookup working |

#### Weeks 4-6: Transaction &amp; Orchestration
| Task | Deliverable |
|------|-------------|
| Build **Order Agent** | JSON contract generation |
| Implement A2A Protocol handshakes | Agents communicate without user input |
| Implement Scenario 3 (New business by name) | Full qualification flow |
| Enable inter-agent communication | Offer Agent ↔ Payment Agent working |

#### Weeks 7-9: Integration &amp; Observability
| Task | Deliverable |
|------|-------------|
| Implement Scenario 6 (End-to-end order) | Complete sales cycle demo |
| Build basic logging/telemetry dashboard | Agent decision chain visible |
| Full system integration testing | All 8 agents orchestrated |
| Edge case handling | Error handling &amp; guardrails |

#### Week 10: Spring Quarter Final Deliverable
| Task | Deliverable |
|------|-------------|
| Final integration &amp; bug fixes | Production-ready demo |
| Final demo preparation | **All 6 scenarios functional** |
| Final documentation | Complete project documentation |
| Presentation preparation | Senior design presentation |

**🎯 Spring Quarter Final Demo:**  
*A fully autonomous demo showcasing:*
- *All 6 sales scenarios working end-to-end*
- *All 8 agents collaborating via A2A protocol*
- *Complete sales cycle: inquiry → serviceability → quote → order*
- *Basic observability showing agent decision chains*

---

## Summary: Scenarios by Quarter

| Scenario | Description | Quarter |
|----------|-------------|---------|
| **1** | Address lookup (new prospect) → Serviceability → Offer | Winter |
| **5** | Product information query (RAG) | Winter |
| **2** | Address lookup (existing customer) → Upsell | Spring |
| **3** | Business name lookup (new) → Full qualification | Spring |
| **4** | Business name lookup (existing) → Upsell | Spring |
| **6** | End-to-end order flow (all agents) | Spring |

---


*Document prepared for Drexel University Senior Design Project*  
*B2B Agentic Sales Orchestration System*
