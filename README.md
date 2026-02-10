# 🤖 B2B Agentic Sales Orchestration System

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-19-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-teal.svg)](https://fastapi.tiangolo.com/)

> An autonomous, multi-agent system (MAS) designed to automate the complex lifecycle of B2B sales using cutting-edge AI orchestration.

**Drexel University – Senior Design Project**
**Winter Quarter (Jan – Mar 2026) | Spring Quarter (Apr – Jun 2026)**

---

## 📋 Table of Contents

- [Executive Summary](#-executive-summary)
- [System Architecture](#-system-architecture)
- [Agent Catalog & Roles](#-agent-catalog--roles)
- [Core Design Principles](#-core-design-principles)
- [Technology Stack](#-technology-stack)
- [Project Roadmap & Milestones](#-project-roadmap--milestones)
- [Testing Strategy](#-testing-strategy)
- [Security Considerations](#-security-considerations)
- [Limitations & Scope](#-limitations--scope)
- [Getting Started](#-getting-started)
- [Contributing](#-contributing)
- [License](#-license)

---

## 📌 Executive Summary

This project aims to build an **autonomous, multi-agent system (MAS)** designed to automate the complex lifecycle of B2B sales. Unlike traditional linear chatbots, this system utilizes a **Super Agent** to orchestrate a mesh of **10 specialized sub-agents**. These agents collaborate to handle:

- 🔍 **Prospect Discovery & Qualification**
- 🌐 **Address Validation & Serviceability**
- ⚙️ **Product Configuration**
- 💰 **Quoting & Pricing**
- 📦 **Order Fulfillment & Installation Scheduling**

### Hybrid Cognitive Model

The architecture strictly adheres to a **Hybrid Cognitive Model**:

| Model Type | Description |
|------------|-------------|
| **Autonomous Reasoning** | LLMs drive intent understanding, negotiation, and dynamic routing |
| **Deterministic Execution** | "Sources of Truth" (APIs, Databases) are used for pricing, serviceability, and inventory to ensure **zero-hallucination compliance** |

---

## 🏗️ System Architecture

### Component Architecture

The system is divided into **four distinct layers**:

| Layer | Name | Purpose |
|-------|------|---------|
| 1️⃣ | **Presentation Layer** | Client-facing React interface |
| 2️⃣ | **Orchestration Layer** | Brain - Super Agent coordination |
| 3️⃣ | **Agent Mesh** | Specialized sub-agents |
| 4️⃣ | **Infrastructure Layer** | Data, tools & APIs |

### Mermaid Architecture Diagram

```mermaid
graph TB
    subgraph Client["🖥️ CLIENT LAYER"]
        UI[B2B Chat Interface<br/>React + WebSocket]
    end

    subgraph Orchestration["🧠 ORCHESTRATION LAYER"]
        SA[SUPER AGENT<br/>Intent Router • Guardrails • Context Manager]
    end

    subgraph Discovery["🔍 DISCOVERY AGENTS"]
        PA[👤 Prospect Agent<br/>Customer Intent & Details]
        LA[📊 Lead Gen Agent<br/>BANT Qualification]
    end

    subgraph Configuration["⚙️ CONFIGURATION AGENTS"]
        SVA[🌐 Serviceability Agent<br/>Address Validation<br/>PRE-SALE]
        ProdA[📦 Product Agent<br/>Technical Specs & RAG]
        OA[💰 Offer Mgmt Agent<br/>Pricing & Bundles]
    end

    subgraph Transaction["💰 TRANSACTION AGENTS"]
        PayA[💳 Payment Agent<br/>Credit Checks]
        OrdA[🛒 Order Agent<br/>Contract Generation]
        SFA[🔧 Service Fulfillment<br/>Installation Scheduling<br/>POST-SALE]
        CommA[📧 Customer Comms Agent<br/>Notifications & Updates]
    end

    subgraph Infrastructure["⚙️ INFRASTRUCTURE LAYER"]
        GIS[(GIS/Coverage Map API)]
        RAG[(Vector DB<br/>ChromaDB)]
        PRICE[(Pricing Engine API)]
        DB[(Order Database<br/>SQLite)]
        LOG[📊 Observability & Logging]
    end

    UI <-->|WebSocket| SA
    SA -->|Routes Intent| Discovery
    SA -->|Routes Intent| Configuration
    SA -->|Routes Intent| Transaction

    PA -.->|Extract Details| SA
    LA -.->|BANT Score| SA

    SVA -->|Validate Address| GIS
    ProdA -->|Query Manuals| RAG
    OA -->|Calculate Price| PRICE

    PayA -->|Credit Check| PRICE
    OrdA -->|Store Order| DB
    SFA -->|Schedule Install| GIS    CommA -.->|Send Notifications| DB
    Discovery -.->|Logs| LOG
    Configuration -.->|Logs| LOG
    Transaction -.->|Logs| LOG

    style SA fill:#ff6b6b,stroke:#333,stroke-width:3px,color:#fff
    style UI fill:#4ecdc4,stroke:#333,stroke-width:2px
    style SVA fill:#ffd93d,stroke:#333,stroke-width:2px
    style SFA fill:#a8e6cf,stroke:#333,stroke-width:2px
    style GIS fill:#95e1d3,stroke:#333,stroke-width:2px
    style RAG fill:#95e1d3,stroke:#333,stroke-width:2px
    style DB fill:#95e1d3,stroke:#333,stroke-width:2px
    style LOG fill:#dfe4ea,stroke:#333,stroke-width:2px
```

### Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant C as 👤 Customer
    participant UI as 🖥️ Chat UI
    participant S as 🧠 Super Agent
    participant P as 👤 Prospect
    participant L as 📊 Lead Gen
    participant SV as 🌐 Serviceability
    participant Pr as 📦 Product
    participant O as 💰 Offer Mgmt
    participant Pay as 💳 Payment
    participant Ord as 🛒 Order
    participant SF as 🔧 Fulfillment
    participant Comm as 📧 Customer Comms
    participant GIS as GIS API
    participant RAG as Vector DB
    participant PRICE as Pricing API
    participant DB as Order DB
    participant SCHED as Scheduler

    C->>UI: "I need internet for my Philadelphia office"
    UI->>S: WebSocket message

    Note over S: Analyze Intent & Route

    rect rgb(200, 230, 200)
        Note over P,L: PHASE 1: DISCOVERY
        S->>P: Extract customer details
        P-->>S: Company: Acme Corp, Address: 123 Market St
        S->>L: Qualify lead (BANT)
        L-->>S: Score: 85/100 Qualified
    end

    rect rgb(255, 250, 200)
        Note over SV,O: PHASE 2: CONFIGURATION
        S->>SV: Validate address & check coverage (PRE-SALE)
        SV->>GIS: Query coverage map
        GIS-->>SV: Serviceable - Available: Fiber 1G, 5G, 10G
        SV-->>S: Address valid + Product list

        S->>Pr: Get product specs for "Fiber 5G"
        Pr->>RAG: Query technical docs
        RAG-->>Pr: Specs, SLAs, Features
        Pr-->>S: Product details

        S->>O: Calculate pricing for Fiber 5G
        O->>PRICE: Request quote + Apply discounts
        PRICE-->>O: $599/mo - 10% = $539/mo
        O-->>S: Final quote
    end

    Note over S: Present offer to customer
    S->>UI: "Your office is serviceable! Fiber 5G: $539/mo"
    UI->>C: Display offer

    C->>UI: "I'll take it!"
    UI->>S: Confirm purchase

    rect rgb(220, 200, 230)
        Note over Pay,SF: PHASE 3: TRANSACTION
        S->>Pay: Run credit check
        Pay->>PRICE: Query payment gateway
        PRICE-->>Pay: Approved (Score: 720)
        Pay-->>S: Payment authorized

        S->>Ord: Generate contract & create order
        Ord->>DB: Store order record
        DB-->>Ord: Order ID: #12345
        Ord-->>S: Contract ready

        S->>SF: Schedule installation (POST-SALE)
        SF->>SCHED: Query available slots
        SCHED-->>SF: Available: Feb 15, 9 AM
        SF-->>S: Install date confirmed
        
        S->>Comm: Send order confirmation
        Comm-->>C: Email/SMS: Order #12345 confirmed
        Comm-->>C: Email/SMS: Installation scheduled Feb 15, 9 AM
    end

    S->>UI: Order #12345 confirmed, Installation: Feb 15
    UI->>C: Display confirmation

    Note over C,Comm: Complete autonomous sale with notifications executed!
```

### Agent Interaction Flow

```mermaid
flowchart LR
    START([👤 Customer Request])

    subgraph DISC[🔍 DISCOVERY PHASE]
        direction TB
        PA2[👤 Prospect Agent<br/>Extract Details]
        LG[📊 Lead Gen Agent<br/>BANT Scoring]
        PA2 --> LG
    end

    subgraph CONFIG[⚙️ CONFIGURATION PHASE]
        direction TB
        SVA2[🌐 Serviceability Agent<br/>Address Validation<br/>PRE-SALE]
        PROD[📦 Product Agent<br/>Tech Specs]
        OFFER[💰 Offer Mgmt Agent<br/>Pricing & Bundles]
        SVA2 --> PROD
        PROD --> OFFER
    end

    subgraph TRANS[💰 TRANSACTION PHASE]
        direction TB
        PAY[💳 Payment Agent<br/>Credit Check]
        ORD[🛒 Order Agent<br/>Contract Generation]
        SF2[🔧 Service Fulfillment<br/>Installation Scheduling<br/>POST-SALE]
        PAY --> ORD
        ORD --> SF2
    end

    ENDNODE([✅ Confirmed Order<br/>Scheduled Install])

    START --> DISC
    DISC --> CONFIG
    CONFIG --> TRANS
    TRANS --> ENDNODE

    style START fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style PA2 fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
    style LG fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
    style SVA2 fill:#ffd93d,stroke:#f57c00,stroke-width:3px
    style PROD fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    style OFFER fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    style PAY fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px
    style ORD fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px
    style SF2 fill:#a8e6cf,stroke:#00897b,stroke-width:3px
    style ENDNODE fill:#a5d6a7,stroke:#388e3c,stroke-width:2px
    style DISC fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style CONFIG fill:#fff8e1,stroke:#ffc107,stroke-width:2px
    style TRANS fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
```

### Data Flow & Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Ingest
    Ingest --> Orchestration
    Orchestration --> Routing
    Routing --> AgentCollab
    AgentCollab --> APIQuery
    APIQuery --> Synthesis
    Synthesis --> Response
    Response --> [*]

    note right of Orchestration: Super Agent analyzes intent
    note right of AgentCollab: A2A Protocol between 9 specialized agents
    note right of APIQuery: Deterministic data from APIs/DBs
```

| Stage | Description | Example |
|-------|-------------|---------|
| **1. Ingest** | B2B Customer interacts via the React Chat Interface. Message sent via WebSocket to backend | User types query |
| **2. Orchestration** | Super Agent analyzes the intent | *"I need internet for my new office in Philadelphia"* |
| **3. Routing** | Super Agent identifies required agents for the request | Prospect Agent -> Lead Gen -> Serviceability Agent -> Product Agent -> Offer Agent |
| **4. Agent Collaboration (A2A)** | Agents communicate via A2A protocol in sequence | Prospect Agent extracts data -> Serviceability Agent validates address -> Product Agent fetches specs -> Offer Agent calculates price |
| **5. Synthesis** | Results returned to Super Agent for response formulation | Natural language response created with all details |
| **6. Observability** | Every step, thought process, API call, and tool output logged | Full auditability and replay capability |

---

## 🤖 Agent Catalog & Roles

All agents are developed using **Google's ADK (Agent Development Kit)**, providing standardized agent lifecycle management, tool integration, memory persistence, and structured logging.

### Complete Agent Roster (10 Agents)

| Agent Name | Role | Type | Source of Truth | Phase |
|------------|------|------|-----------------|-------|
| 🧠 **Super Agent** | Orchestrator. Manages user state, tone, routing, and hands-off tasks to sub-agents | `Orchestrator` | Session Context | All |
| 👤 **Prospect Agent** | Identifies customer intent, company details, and contact persona | `Operational` | CRM Mock | Discovery |
| 📊 **Lead Gen Agent** | Qualifies leads (BANT scoring) and determines sales readiness | `Operational` | Scoring Logic | Discovery |
| 🌐 **Serviceability Agent** | **PRE-SALE**: Validates address, checks service coverage, returns available products by location | `Deterministic` | GIS/Coverage Map API | Configuration |
| 📦 **Product Agent** | Retrieves technical specs, hardware details, and feature documentation | `Info/RAG` | Vector DB (Manuals) | Configuration |
| 💰 **Offer Mgmt Agent** | Calculates pricing, applies bundles, and manages promotional discounts | `Deterministic` | Pricing Engine API | Configuration |
| 💳 **Payment Agent** | Handles credit checks, payment authorization, and financial validation | `Transactional` | Payment Gateway | Transaction |
| 🛒 **Order Agent** | Manages cart, contract generation, order creation, and final checkout | `Transactional` | Order DB | Transaction |
| 🔧 **Service Fulfillment Agent** | **POST-SALE**: Schedules installation appointments and coordinates technician dispatch | `Transactional` | Scheduler API | Transaction |
| 📧 **Customer Comms Agent** | Sends automated notifications for order placement, payment status, installation reminders, abandoned cart, and delivery updates | `Operational` | Notification Service, Email/SMS Gateway | Transaction |

### Agent Development Timeline

| Agent | Winter Qtr | Spring Qtr | Owner |
|-------|------------|------------|-------|
| 🧠 Super Agent | ✅ Basic routing | ✅ Full orchestration | Sudhaman |
| 👤 Prospect Agent | ✅ Complete | — | Aubin |
| 📊 Lead Gen Agent | ✅ Basic BANT | ✅ Enhanced scoring | Aubin |
| 📦 Product Agent | ✅ Complete | — | Raja |
| 💰 Offer Mgmt Agent | ✅ Basic routing | ✅ Complete | Sudhaman |
| 🛒 Order Agent | ✅ Basic routing | ✅ Complete | Raja |
| 💳 Payment Agent | ✅ Basic routing | ✅ Complete | Arun |
| 🌐 Serviceability Agent | ✅ Basic routing | ✅ Complete | Raja |
| 🔧 Service Fulfillment Agent | ✅ Basic routing | ✅ Scheduling | Arun |
| 📧 Customer Comms Agent | ⏳ Basic notifications | ⏳ Complete | TBD |

### Key Agent Distinction

**🌐 Serviceability Agent vs 🔧 Service Fulfillment Agent:**

| Aspect | 🌐 Serviceability Agent | 🔧 Service Fulfillment Agent |
|--------|-------------------------|------------------------------|
| **Timing** | PRE-SALE (before quote) | POST-SALE (after order confirmation) |
| **Purpose** | Address validation & coverage check | Installation scheduling & coordination |
| **Input** | Customer address | Confirmed order + Customer availability |
| **Output** | Boolean (serviceable?) + Available products list | Installation date + Technician assignment |
| **Data Source** | GIS/Coverage Map API | Scheduler/Workforce Management API |
| **Decision** | "Can we serve this address?" | "When can we install?" |

### Agent Type Classification

```mermaid
pie showData
    title Agent Types Distribution (10 Total Agents)
    "Orchestrator" : 1
    "Operational" : 3
    "Info/RAG" : 1
    "Deterministic" : 2
    "Transactional" : 3
```

### Agent Interaction Map

```mermaid
graph TB
    SA3[🧠 Super Agent] --> PA3[👤 Prospect Agent]
    SA3 --> LA3[📊 Lead Gen Agent]
    SA3 --> ProdA3[📦 Product Agent]
    SA3 --> SrvA3[🌐 Serviceability Agent]
    SA3 --> OA3[💰 Offer Agent]
    SA3 --> PayA3[💳 Payment Agent]
    SA3 --> OrdA3[🛒 Order Agent]
    SA3 --> SFA3[🔧 Service Fulfillment]
    SA3 --> CommA3[📧 Customer Comms]

    PA3 -.-> SrvA3
    SrvA3 -.-> ProdA3
    ProdA3 -.-> OA3
    OA3 -.-> PayA3
    PayA3 -.-> OrdA3
    OrdA3 -.-> SFA3

    SrvA3 --> GIS3[(GIS API)]
    ProdA3 --> VDB3[(Vector DB)]
    OA3 --> PE3[(Pricing Engine)]
    PayA3 --> PG3[(Payment Gateway)]
    OrdA3 --> DB3[(Order DB)]
    SFA3 --> SCH3[(Scheduler)]
    CommA3 --> NOTIF3[(Email/SMS Gateway)]

    style SA3 fill:#ff6b6b,stroke:#333,stroke-width:3px,color:#fff
    style SrvA3 fill:#4ecdc4,stroke:#333,stroke-width:3px
    style GIS3 fill:#95e1d3,stroke:#333
```

### Spotlight: The Serviceability Agent 🌐

The **Serviceability Agent** is a critical PRE-SALE deterministic agent that prevents wasted effort by validating address eligibility BEFORE any quote is generated.

#### Why It's Essential

In B2B telecommunications sales, not all addresses can receive all services. The Serviceability Agent acts as a gatekeeper to ensure:

1. **Address Validation**: Confirms the physical address exists and is correctly formatted
2. **Coverage Verification**: Checks GIS/coverage maps to determine if service infrastructure reaches the location
3. **Technology Availability**: Returns which specific products (Fiber 1G, 5G, 10G, Coax, etc.) are available at that address
4. **Zone Classification**: Identifies service zones for routing to appropriate regional teams

#### Key Responsibilities

| Function | Description | Data Source |
|----------|-------------|-------------|
| **Address Validation** | Parses and validates street address, city, state, ZIP | GIS/Address API |
| **Coverage Check** | Determines if address is within serviceable territory | Coverage Map API |
| **Technology Assessment** | Identifies infrastructure type (FTTP, HFC, DOCSIS 3.1) | Network Inventory |
| **Product Filtering** | Returns only products available for that location/technology | Product Catalog + Coverage DB |

#### Technical Implementation

| Aspect | Details |
|--------|---------|
| **Trigger** | Invoked after address extraction, before product recommendations |
| **Input** | Structured address object (street, city, state, zip) |
| **API Call** | GIS/Coverage Map API (deterministic lookup) |
| **Output Schema** | `{ serviceable: boolean, availableProducts: string[], serviceZone: string }` |
| **Error Handling** | If API fails, gracefully inform user to contact sales team |
| **Caching** | Address results cached for 24 hours to reduce API load |

#### Example Interaction

```
Customer: "I need internet for 123 Market Street, Philadelphia, PA 19107"

Prospect Agent: Extracts address
Lead Gen Agent: Qualifies lead (BANT: 85/100)

Serviceability Agent:
    -> Query GIS API with address
    <- Response: {
        serviceable: true,
        availableProducts: ["Fiber 1G", "Fiber 5G", "Fiber 10G"],
        serviceZone: "Metro-East-PA"
      }
    Result: Proceed to Product Agent for "Fiber 5G" specs

--- ALTERNATIVE SCENARIO ---

Serviceability Agent:
    -> Query GIS API with address
    <- Response: {
        serviceable: false,
        reason: "No fiber infrastructure at location"
      }
    Result: "I apologize, but we don't currently service that address.
             Would you like us to notify you when coverage expands to your area?"
```

#### Business Impact

- **Reduces Churn**: Prevents customers from going through entire sales process only to discover service isn't available
- **Saves Time**: Eliminates wasted effort on quotes for non-serviceable addresses
- **Improves CX**: Sets accurate expectations upfront
- **Data-Driven**: Uses authoritative GIS data, not LLM guesses

---

## 🎯 Core Design Principles

### Determinism vs. Autonomy

To prevent **"hallucinations"** in critical business areas, we separate concerns:

```mermaid
graph LR
    subgraph LLM[LLM Flows - Autonomous]
        A1[Conversation]
        A2[Summarization]
        A3[Data Extraction]
    end
    
    subgraph DET[Deterministic Flows]
        D1[Pricing]
        D2[Inventory]
        D3[Serviceability]
    end
    
    subgraph SRC[Sources of Truth]
        S1[(APIs)]
        S2[(Databases)]
    end
    
    LLM -->|Context| DET
    DET -->|Fetch| SRC
    SRC -->|Data| DET

    style LLM fill:#fff3cd
    style DET fill:#d4edda
    style SRC fill:#cce5ff
```

| Flow Type | Use Cases | Key Principle |
|-----------|-----------|---------------|
| **LLM Flows (Autonomous)** | Conversation, Summarization, Extracting structured data from unstructured text | Creative & Flexible |
| **Deterministic Flows** | Pricing, Inventory, Serviceability | **MUST** come from rigid APIs - agents are "tool users" that fetch data, not invent it |

### Observability & Steering

| Feature | Description |
|---------|-------------|
| **Agent Steering** | "System Prompts" and "Guardrails" at Super Agent level prevent discussion of competitors or sensitive topics |
| **Structured Logging** | All A2A communication logged in structured JSON format, enabling "replay" of sales to understand agent decisions |

### Error Handling & Resilience

The system implements defensive patterns to ensure graceful degradation:

| Pattern | Implementation | Purpose |
|---------|----------------|---------|
| **Circuit Breaker** | Wraps all external API calls | Prevents cascade failures when downstream services are unavailable |
| **Retry with Backoff** | Exponential backoff on transient failures | Handles temporary network issues without user impact |
| **Fallback Responses** | Graceful degradation per agent | If Product Agent fails, Super Agent can still provide basic info |
| **Timeout Management** | Configurable per-agent timeouts | Prevents hung conversations from blocking resources |
| **Dead Letter Queue** | Failed transactions logged for retry | Ensures no orders are lost due to transient failures |

---

## 🔐 Security Considerations

> **Note:** This is an academic demo project using mock data. The considerations below outline what a production system would require.

| Area | Demo Implementation | Production Requirement |
|------|---------------------|------------------------|
| **Authentication** | Basic session handling | JWT tokens, OAuth 2.0 |
| **API Credentials** | Environment variables | Secret management (Vault, AWS Secrets) |
| **Data Privacy** | Mock customer data only | Encryption at rest/transit, PII handling |
| **Payment Data** | Simulated credit checks | PCI-DSS compliance, tokenization |

---

## 🧪 Testing Strategy

### Testing by Layer

| Layer | Test Type | Tools | Coverage Target |
|-------|-----------|-------|-----------------|
| **Agents** | Unit Tests | pytest, unittest.mock | 80%+ per agent |
| **A2A Protocol** | Integration Tests | pytest-asyncio | All handshake paths |
| **API Mocks** | Contract Tests | Pact/Schema validation | 100% of mock APIs |
| **Full System** | E2E Scenarios | Playwright + pytest | All 6 scenarios |

### Key Test Scenarios

1. **Happy Path**: All 6 sales scenarios execute successfully
2. **Agent Failure**: Super Agent handles downstream agent unavailability
3. **Invalid Input**: Malformed addresses, non-existent products
4. **Concurrent Users**: Multiple simultaneous conversations (load testing)
5. **State Recovery**: Session resumption after connection drop

> 📄 For comprehensive positive and negative test cases for each agent, see [Scenarios.md](Scenarios.md).

---

## ⚠️ Limitations & Scope

### Current Limitations

| Limitation | Rationale | Future Consideration |
|------------|-----------|----------------------|
| **Mock APIs Only** | Academic project scope | Production would integrate real CRM, GIS, Payment systems |
| **Single LLM Provider** | Simplified implementation | Could add provider abstraction for failover |
| **No Multi-language Support** | English-only for demo | i18n framework ready for extension |
| **Limited Concurrent Users** | Not load-tested at scale | Horizontal scaling via Kubernetes |
| **No Voice/Omnichannel** | Text chat only | Architecture supports future voice integration |

### Out of Scope (Academic Project)

- Real payment processing (PCI compliance)
- Production CRM/ERP integrations
- Mobile native applications
- Multi-tenant SaaS deployment
- Real-time inventory synchronization

---

## 🛠️ Technology Stack

### Frontend

| Technology | Purpose |
|------------|---------|
| React 19 | Framework - Functional Components, Hooks |
| Tailwind CSS | Styling - Rapid, clean UI |
| Context API | State Management - Chat history |
| Socket.io | Communication - Real-time streaming |

### Backend & Agents

| Technology | Purpose |
|------------|---------|
| Python 3.12+ | Language |
| FastAPI | Framework - WebSockets & REST endpoints |
| Google ADK | Agent Development Kit - Multi-agent orchestration framework |
| A2A Protocol | JSON-RPC style messaging for inter-agent communication |
| MCP | Model Context Protocol for connecting agents to local tools |
| Poetry | Dependency isolation |

### Data & Infrastructure

| Technology | Purpose |
|------------|---------|
| LLM Provider | Agnostic (Abstracted via API Wrapper) |
| ChromaDB | RAG - Product Manuals |
| SQLite | Transactional DB - Orders/Users |

### Technology Architecture

```mermaid
graph TB
    subgraph FE[Frontend]
        React[React 19]
        Tailwind[Tailwind CSS]
        Socket[Socket.io]
    end
    
    subgraph BE[Backend]
        FastAPI2[FastAPI]
        ADK2[Google ADK]
        Python2[Python 3.12+]
    end
    
    subgraph PROTO[Protocols]
        A2A2[A2A JSON-RPC]
        MCP2[MCP Protocol]
        REST2[REST APIs]
    end
    
    subgraph DATA[Data Layer]
        LLM2[LLM Provider]
        Chroma2[ChromaDB]
        PG2[SQLite]
    end
    
    FE -->|WebSocket| BE
    BE --> PROTO
    PROTO --> DATA

    style FE fill:#e1f5fe
    style BE fill:#fff3e0
    style PROTO fill:#f3e5f5
    style DATA fill:#e8f5e9
```

---

## 🚀 Getting Started

### Prerequisites

```bash
# Python 3.12+
python --version

# Node.js 18+
node --version

# Poetry (recommended)
pip install poetry
```

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sudhamanc/ConversationalSalesAgent.git
   cd ConversationalSalesAgent
   ```

2. **Backend Setup**
   ```bash
   cd SuperAgent/server
   pip install -r requirements.txt
   cp .env.example .env
   # Configure your LLM API keys and database connections
   uvicorn main:app --reload
   ```

3. **Frontend Setup**
   ```bash
   cd SuperAgent/client
   npm install
   npm run dev
   ```

### Project Structure

```
ConversationalSalesAgent/
├── SuperAgent/
│   ├── client/                          # React Frontend
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── utils/
│   │   └── package.json
│   └── server/                          # FastAPI Backend
│       ├── agent/
│       │   ├── agent.py                 # Super Agent
│       │   ├── prompts.py
│       │   ├── sub_agents/
│       │   │   ├── greeting_agent.py
│       │   │   ├── faq_agent.py
│       │   │   └── product_agent.py
│       │   └── tools/
│       │       └── sales_tools.py
│       ├── api/
│       │   ├── chat.py
│       │   └── session.py
│       ├── middleware/
│       │   ├── auth.py
│       │   └── rate_limiter.py
│       ├── utils/
│       │   └── logger.py
│       ├── config.py
│       ├── main.py
│       └── requirements.txt
├── BootStrapAgent/                      # Bootstrap/Template Agent
├── docs/
│   ├── AI_AGENT_CATALOG.md
│   └── Sales Scenarios.txt
├── MilestonePlan.md
├── Scenarios.md                         # Test scenarios (positive & negative)
└── README.md
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

For questions or support, please open an issue or contact the team.

---

<p align="center">
  <strong>Built with ❤️ for the future of B2B Sales</strong>
</p>
