# 🤖 B2B Agentic Sales Orchestration System

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-19-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-teal.svg)](https://fastapi.tiangolo.com/)

> An autonomous, multi-agent system (MAS) designed to automate the complex lifecycle of B2B sales using cutting-edge AI orchestration.

---

## 📋 Table of Contents

- [Executive Summary](#-executive-summary)
- [System Architecture](#-system-architecture)
  - [Component Architecture](#component-architecture)
  - [Architecture Diagram](#architecture-diagram)
  - [Data Flow & Lifecycle](#data-flow--lifecycle)
- [Agent Catalog & Roles](#-agent-catalog--roles)
- [Core Design Principles](#-core-design-principles)
  - [Determinism vs. Autonomy](#determinism-vs-autonomy)
  - [Observability & Steering](#observability--steering)
- [Technology Stack](#-technology-stack)
- [Project Roadmap](#-project-roadmap)
- [Getting Started](#-getting-started)
- [Contributing](#-contributing)
- [License](#-license)

---

## 📌 Executive Summary

This project aims to build an **autonomous, multi-agent system (MAS)** designed to automate the complex lifecycle of B2B sales. Unlike traditional linear chatbots, this system utilizes a **Super Agent** to orchestrate a mesh of specialized sub-agents. These agents collaborate to handle:

- 🔍 **Prospect Discovery**
- ⚙️ **Product Configuration**
- 💰 **Quoting & Pricing**
- 📦 **Order Fulfillment**

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

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          🖥️  CLIENT LAYER (React)                               │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐            │
│  │    B2B Chat Interface       │◄──►│     WebSocket Client        │            │
│  └─────────────────────────────┘    └──────────────┬──────────────┘            │
└────────────────────────────────────────────────────┼────────────────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       🧠  ORCHESTRATION LAYER (Python)                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         🧠 SUPER AGENT                                   │   │
│  │                    (Orchestrator / Router / Guardrails)                  │   │
│  └─────────────────────────────────────┬───────────────────────────────────┘   │
└────────────────────────────────────────┼────────────────────────────────────────┘
                                         │
           ┌─────────────────────────────┼─────────────────────────────┐
           │                             │                             │
           ▼                             ▼                             ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  🔍 DISCOVERY       │    │  ⚙️ CONFIGURATION   │    │  💰 TRANSACTION     │
│                     │    │                     │    │                     │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ │ 👤 Prospect     │ │    │ │ 📦 Product      │ │    │ │ 💳 Payment      │ │
│ │    Agent        │ │    │ │    Agent        │ │    │ │    Agent        │ │
│ └─────────────────┘ │    │ └─────────────────┘ │    │ └─────────────────┘ │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ │ 📊 Lead Gen     │ │    │ │ 💰 Offer Mgmt   │ │    │ │ 🛒 Order        │ │
│ │    Agent        │ │    │ │    Agent        │ │    │ │    Agent        │ │
│ └─────────────────┘ │    │ └─────────────────┘ │    │ └─────────────────┘ │
│                     │    │                     │    │ ┌─────────────────┐ │
│                     │    │                     │    │ │ 🔧 Service      │ │
│                     │    │                     │    │ │ Fulfillment     │ │
│                     │    │                     │    │ └─────────────────┘ │
└──────────┬──────────┘    └──────────┬──────────┘    └──────────┬──────────┘
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      │ A2A Protocol
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       ⚙️  INFRASTRUCTURE & TOOLS (ADK/MCP)                      │
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Backend API  │  │ RAG Engine   │  │ Observability│  │    State     │        │
│  │   Gateway    │  │ (Vector DB)  │  │  & Logging   │  │  Database    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Mermaid Architecture Diagram

```mermaid
graph TB
    subgraph Client["CLIENT LAYER"]
        UI[B2B Chat Interface]
        WS[WebSocket Client]
    end

    subgraph Orchestration["ORCHESTRATION LAYER"]
        SA[SUPER AGENT]
        R[Intent Router]
        G[Guardrails]
    end

    subgraph Discovery["DISCOVERY AGENTS"]
        PA[Prospect Agent]
        LA[Lead Gen Agent]
    end

    subgraph Configuration["CONFIGURATION AGENTS"]
        ProdA[Product Agent]
        OA[Offer Mgmt Agent]
    end

    subgraph Transaction["TRANSACTION AGENTS"]
        PayA[Payment Agent]
        OrdA[Order Agent]
        SFA[Service Fulfillment Agent]
    end

    subgraph Infrastructure["INFRASTRUCTURE"]
        API[API Gateway]
        RAG[RAG Engine]
        DB[(Database)]
        LOG[Observability]
    end

    UI <--> WS
    WS <--> SA
    SA --> R
    G -.-> SA
    R --> Discovery
    R --> Configuration
    R --> Transaction
    
    PA --> API
    LA --> API
    ProdA --> RAG
    OA --> API
    PayA --> API
    OrdA --> DB
    SFA --> API
    
    Discovery -.-> LOG
    Configuration -.-> LOG
    Transaction -.-> LOG

    style SA fill:#ff6b6b,stroke:#333,stroke-width:2px,color:#fff
    style UI fill:#4ecdc4,stroke:#333,stroke-width:2px
    style DB fill:#95e1d3,stroke:#333,stroke-width:2px
```

---

### Detailed System Flow

```
                                    COMPLETE B2B SALES FLOW
    ═══════════════════════════════════════════════════════════════════════════

    👤 CUSTOMER                    🧠 SUPER AGENT                    ⚙️ BACKEND
         │                              │                                │
         │  "I need internet for       │                                │
         │   my Philadelphia office"   │                                │
         │ ─────────────────────────►  │                                │
         │                              │                                │
         │                              │  ┌─────────────────────────┐  │
         │                              │  │   DISCOVERY PHASE       │  │
         │                              │  ├─────────────────────────┤  │
         │                              │  │ 👤 Prospect Agent       │  │
         │                              │  │    → Extract details    │  │
         │                              │  │ 📊 Lead Gen Agent       │  │
         │                              │  │    → BANT scoring       │  │
         │                              │  └─────────────────────────┘  │
         │                              │               │                │
         │                              │               ▼                │
         │                              │  ┌─────────────────────────┐  │
         │                              │  │  CONFIGURATION PHASE    │  │
         │                              │  ├─────────────────────────┤  │
         │                              │  │ 🔧 Service Fulfillment  │──┼──► GIS API
         │                              │  │    → Check availability │◄─┼─── ✅ Serviceable
         │                              │  │ 📦 Product Agent        │──┼──► Vector DB
         │                              │  │    → Get products       │◄─┼─── Product Specs
         │                              │  │ 💰 Offer Mgmt Agent     │──┼──► Pricing API
         │                              │  │    → Calculate pricing  │◄─┼─── Quote
         │                              │  └─────────────────────────┘  │
         │                              │               │                │
         │                              │               ▼                │
         │                              │  ┌─────────────────────────┐  │
         │                              │  │   TRANSACTION PHASE     │  │
         │                              │  ├─────────────────────────┤  │
         │                              │  │ 💳 Payment Agent        │──┼──► Payment Gateway
         │                              │  │    → Credit check       │◄─┼─── ✅ Approved
         │                              │  │ 🛒 Order Agent          │──┼──► Order DB
         │                              │  │    → Generate contract  │◄─┼─── Order ID
         │                              │  │ 🔧 Service Fulfillment  │──┼──► Scheduler API
         │                              │  │    → Schedule install   │◄─┼─── Install Date
         │                              │  └─────────────────────────┘  │
         │                              │                                │
         │  "Great news! Your office   │                                │
         │   is serviceable..."        │                                │
         │ ◄─────────────────────────  │                                │
         │                              │                                │

    ═══════════════════════════════════════════════════════════════════════════
                            📊 All steps logged for auditability
```

### Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant C as Customer
    participant UI as Chat UI
    participant S as Super Agent
    participant P as Prospect Agent
    participant L as Lead Gen Agent
    participant Pr as Product Agent
    participant O as Offer Agent
    participant Pay as Payment Agent
    participant Ord as Order Agent
    participant SF as Service Fulfillment
    participant API as Backend APIs

    C->>UI: Request internet service
    UI->>S: WebSocket message
    
    Note over S: Intent Analysis
    
    rect rgb(200, 230, 200)
        Note over P,L: Discovery Phase
        S->>P: Extract details
        P-->>S: Company info
        S->>L: Qualify lead
        L-->>S: BANT score
    end
    
    rect rgb(230, 220, 200)
        Note over Pr,O: Configuration Phase
        S->>SF: Check serviceability
        SF->>API: Query GIS
        API-->>SF: Serviceable
        S->>Pr: Get products
        Pr->>API: Query RAG
        API-->>Pr: Specs
        S->>O: Calculate price
        O->>API: Pricing engine
        API-->>O: Quote
    end
    
    rect rgb(220, 200, 230)
        Note over Pay,SF: Transaction Phase
        S->>Pay: Credit check
        Pay->>API: Payment gateway
        API-->>Pay: Approved
        S->>Ord: Create order
        Ord->>API: Order DB
        API-->>Ord: Order ID
        S->>SF: Schedule install
        SF->>API: Scheduler
        API-->>SF: Date
    end
    
    S->>UI: Complete response
    UI->>C: Confirmation & details
```

### Agent Interaction Flow

```mermaid
flowchart LR
    subgraph D[DISCOVERY]
        A[Customer Intent] --> B[Prospect Agent]
        B --> C[Lead Gen Agent]
    end
    
    subgraph CF[CONFIGURATION]
        C --> D1[Product Agent]
        D1 --> E[Offer Mgmt Agent]
    end
    
    subgraph T[TRANSACTION]
        E --> F[Payment Agent]
        F --> G[Order Agent]
        G --> H[Service Fulfillment]
    end
    
    H --> I[Confirmed Order]

    style A fill:#e3f2fd
    style B fill:#c8e6c9
    style C fill:#c8e6c9
    style D1 fill:#fff9c4
    style E fill:#fff9c4
    style F fill:#e1bee7
    style G fill:#e1bee7
    style H fill:#e1bee7
    style I fill:#a5d6a7
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
    note right of AgentCollab: A2A Protocol between 7 agents
    note right of APIQuery: Deterministic data from APIs
```

| Stage | Description | Example |
|-------|-------------|---------|
| **1. Ingest** | B2B Customer interacts via the React Chat Interface. Message sent via WebSocket to backend | User types query |
| **2. Orchestration** | Super Agent analyzes the intent | *"I need internet for my new office in Philadelphia"* |
| **3. Routing** | Super Agent identifies required agents | Prospect Agent + Service Fulfillment Agent |
| **4. Agent Collaboration (A2A)** | Agents communicate via A2A protocol | Prospect Agent extracts data → Service Fulfillment Agent checks availability |
| **5. Synthesis** | Results returned to Super Agent for response formulation | Natural language response created |
| **6. Observability** | Every step, thought process, and tool output logged | Full auditability |

---

## 🤖 Agent Catalog & Roles

All agents are developed using **Google's ADK (Agent Development Kit)**, providing standardized agent lifecycle management, tool integration, memory persistence, and structured logging.

| Agent Name | Role | Type | Source of Truth |
|------------|------|------|-----------------|
| 🧠 **Super Agent** | Orchestrator. Manages user state, tone, and hands-off tasks to sub-agents | `Orchestrator` | Session Context |
| 👤 **Prospect Agent** | Identifies customer intent, company details, and contact persona | `Operational` | CRM Mock |
| 📊 **Lead Gen Agent** | Qualifies leads (BANT scoring) and determines sales readiness | `Operational` | Scoring Logic |
| 📦 **Product Agent** | Retrieves technical specs and hardware details | `Info/RAG` | Vector DB (Manuals) |
| 💰 **Offer Mgmt Agent** | Calculates pricing, bundles, and applies discounts | `Deterministic` | Pricing Engine API |
| 🛒 **Order Agent** | Manages the cart, contract generation, and final checkout | `Transactional` | Order DB |
| 💳 **Payment Agent** | Handles credit checks and payment processing | `Transactional` | Payment Gateway |
| 🔧 **Service Fulfillment Agent** | Validates address serviceability and schedules installation | `Deterministic` | GIS/Scheduler API |

### Agent Type Classification

```mermaid
pie showData
    title Agent Types Distribution
    "Orchestrator" : 1
    "Operational" : 2
    "Info/RAG" : 1
    "Deterministic" : 2
    "Transactional" : 2
```

---

## 🎯 Core Design Principles

### Determinism vs. Autonomy

To prevent **"hallucinations"** in critical business areas, we separate concerns:

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                    HYBRID COGNITIVE MODEL                              │
    ├────────────────────────────────────────────────────────────────────────┤
    │                                                                        │
    │   🤖 LLM FLOWS (Autonomous)          🔒 DETERMINISTIC FLOWS           │
    │   ─────────────────────────          ─────────────────────────        │
    │                                                                        │
    │   ┌─────────────────────┐            ┌─────────────────────┐          │
    │   │ • Conversation      │            │ • Pricing           │          │
    │   │ • Summarization     │ ────────►  │ • Inventory         │          │
    │   │ • Data Extraction   │  Context   │ • Serviceability    │          │
    │   │ • Intent Analysis   │  & Intent  │ • Credit Checks     │          │
    │   └─────────────────────┘            └──────────┬──────────┘          │
    │                                                 │                      │
    │           Creative & Flexible                   │ Fetch Only           │
    │                                                 ▼                      │
    │                                      ┌─────────────────────┐          │
    │                                      │  📊 SOURCES OF      │          │
    │                                      │     TRUTH           │          │
    │                                      │                     │          │
    │                                      │  • APIs             │          │
    │                                      │  • Databases        │          │
    │                                      │  • External Systems │          │
    │                                      └─────────────────────┘          │
    │                                                                        │
    │   ⚠️  Agents are "tool users" - they FETCH data, never INVENT it      │
    └────────────────────────────────────────────────────────────────────────┘
```

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

```
    ERROR HANDLING FLOW
    ═══════════════════════════════════════════════════════════════

    Agent Request → [Circuit Breaker] → External API
                          │
                    ┌─────┴─────┐
                    │  CLOSED   │ ← Normal operation
                    └─────┬─────┘
                          │ Failures exceed threshold
                          ▼
                    ┌───────────┐
                    │   OPEN    │ ← Fast-fail, no API calls
                    └─────┬─────┘
                          │ After cooldown period
                          ▼
                    ┌───────────┐
                    │ HALF-OPEN │ ← Test with single request
                    └───────────┘
```

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

### Test Pyramid

```
                    ┌─────────────┐
                    │   E2E Tests │  ← Full scenario flows (Scenario 1-6)
                    │    (10%)    │
                    ├─────────────┤
                    │ Integration │  ← Agent-to-Agent communication
                    │    (30%)    │     API mock validation
                    ├─────────────┤
                    │    Unit     │  ← Individual agent logic
                    │    (60%)    │     Intent classification
                    └─────────────┘     Data extraction
```

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

### Scalability Considerations

For production deployment, consider:

```
    HORIZONTAL SCALING ARCHITECTURE
    ═══════════════════════════════════════════════════════════════

    Load Balancer
         │
         ├──► FastAPI Instance 1 ──► Agent Pool 1
         ├──► FastAPI Instance 2 ──► Agent Pool 2
         └──► FastAPI Instance N ──► Agent Pool N
                      │
                      ▼
              Shared State (Redis)
              Vector DB (ChromaDB Cluster)
              Message Queue (RabbitMQ/Kafka)
```

---

## 🛠️ Technology Stack

### Frontend

| Technology | Purpose |
|------------|---------|
| ![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white) | Framework - Functional Components, Hooks |
| ![Tailwind](https://img.shields.io/badge/Tailwind_CSS-38B2AC?logo=tailwind-css&logoColor=white) | Styling - Rapid, clean UI |
| ![Context API](https://img.shields.io/badge/Context_API-State-purple) | State Management - Chat history |
| ![Socket.io](https://img.shields.io/badge/Socket.io-Client-black?logo=socket.io) | Communication - Real-time streaming |

### Backend & Agents

| Technology | Purpose |
|------------|---------|
| ![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white) | Language |
| ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) | Framework - WebSockets & REST endpoints |
| ![ADK](https://img.shields.io/badge/Google_ADK-Agent_Runtime-orange) | Google Agent Development Kit - Multi-agent orchestration framework |
| **A2A Protocol** | JSON-RPC style messaging for inter-agent communication |
| **MCP** | Model Context Protocol for connecting agents to local tools |
| ![Poetry](https://img.shields.io/badge/Poetry-Environment_Mgmt-blue) | Dependency isolation |

### Data & Infrastructure

| Technology | Purpose |
|------------|---------|
| **LLM Provider** | Agnostic (Abstracted via API Wrapper) |
| ![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-green) | RAG - Product Manuals |
| ![SQLite](https://img.shields.io/badge/SQLite-Dev-blue?logo=sqlite) / ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Prod-336791?logo=postgresql&logoColor=white) | Transactional DB - Orders/Users |

### Technology Architecture

```mermaid
graph TB
    subgraph FE[Frontend]
        React[React 19]
        Tailwind[Tailwind CSS]
        Socket[Socket.io]
    end
    
    subgraph BE[Backend]
        FastAPI[FastAPI]
        ADK[Google ADK]
        Python[Python 3.12+]
    end
    
    subgraph PROTO[Protocols]
        A2A[A2A JSON-RPC]
        MCP[MCP Protocol]
        REST[REST APIs]
    end
    
    subgraph DATA[Data Layer]
        LLM[LLM Provider]
        Chroma[ChromaDB]
        PG[PostgreSQL]
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

## 📅 Project Roadmap

### Timeline Overview (2 Quarters)

```
    2025 DEVELOPMENT ROADMAP
    ════════════════════════════════════════════════════════════════════════════
    
    Q1: FOUNDATION PHASE                    Q2: TRANSACTION PHASE
    ─────────────────────                   ───────────────────────
    
    Jan     Feb     Mar     Apr     May     Jun
    │       │       │       │       │       │
    ├───────┴───────┤       │       │       │
    │ Sprint 1-2    │       │       │       │
    │ Infrastructure│       │       │       │
    │ • React + FastAPI     │       │       │
    │ • WebSocket   │       │       │       │
    │ • ADK Base    │       │       │       │
    │               ├───────┴───────┤       │
    │               │ Sprint 3-4    │       │
    │               │ Super Agent   │       │
    │               │ • Routing     │       │
    │               │ • RAG Setup   │       │
    │               │ • Product Agent       │
    │               │               ├───────┴───────┤
    │               │               │ Sprint 5-6    │
    │               │               │ Discovery     │
    │               │               │ • Prospect    │
    │               │               │ • Svc Fulfill │
    │               │               │               │
    ▼               ▼               ▼               │
    ════════════════════════════════╪═══════════════╪═══════════════════════════
                              Q1 DELIVERABLE        │
                              Chat UI with          │
                              Product Q&A &         │
                              Serviceability        │
                                                    │       │       │
                                                    ├───────┴───────┤
                                                    │ Sprint 1-2    │
                                                    │ Deterministic │
                                                    │ • Offer Mgmt  │
                                                    │ • Payment     │
                                                    │               ├───────┴───────┐
                                                    │               │ Sprint 3-4    │
                                                    │               │ A2A Protocol  │
                                                    │               │ • Handshakes  │
                                                    │               │ • Inter-agent │
                                                    │               │               ├───────┐
                                                    │               │               │ Sprint│
                                                    │               │               │ 5-6   │
                                                    │               │               │ Order │
                                                    │               │               │ Telemetry
                                                    ▼               ▼               ▼
                                                    ═════════════════════════════════
                                                                        Q2 DELIVERABLE
                                                                        Full Autonomous
                                                                        Sales Demo
```

```mermaid
gantt
    title B2B Agentic Sales System Roadmap
    dateFormat YYYY-MM-DD
    
    section Q1 Foundation
    Infrastructure Setup    :a1, 2025-01-01, 4w
    Super Agent & RAG       :a2, after a1, 4w
    Discovery Agents        :a3, after a2, 4w
    Q1 Deliverable          :milestone, m1, after a3, 0d
    
    section Q2 Transaction
    Deterministic Agents    :b1, after a3, 4w
    A2A Orchestration       :b2, after b1, 4w
    Order & Observability   :b3, after b2, 4w
    Q2 Deliverable          :milestone, m2, after b3, 0d
```

### Quarter 1: Foundation & Discovery Phase

> **Goal:** A working "Sales Assistant" that can chat, identify users, and check service availability.

#### Sprint 1-2: Infrastructure Setup
- [x] Set up React Frontend + FastAPI Backend
- [x] Implement WebSocket streaming
- [x] Configure Google ADK: Agent base classes, logging, memory, and tool definitions

#### Sprint 3-4: The Super Agent & RAG
- [ ] Deploy Super Agent with basic routing capabilities
- [ ] Ingest Product PDFs into ChromaDB
- [ ] Build Product Agent (can answer *"What is the speed of Business Internet 1G?"*)

#### Sprint 5-6: Discovery Agents
- [ ] Build Prospect Agent (extracts Name, Address)
- [ ] Build Service Fulfillment Agent (Mock API for *"Is this address serviceable?"*)

#### 🎯 Q1 Deliverable
> A functional Chat UI where a user can ask about products and check if their address is eligible for service.

---

### Quarter 2: Transaction & Orchestration Phase

> **Goal:** A complete "End-to-End" autonomous sales cycle including pricing and ordering.

#### Sprint 1-2: Complex Deterministic Agents
- [ ] Build Offer Management Agent (Logic for bundles/pricing)
- [ ] Build Payment Agent (Mock credit check)

#### Sprint 3-4: Advanced Orchestration (A2A)
- [ ] Implement the "Handshake": `Prospect Agent → Lead Gen → Offer Agent`
- [ ] Enable agents to "talk" without user input
  - *Example: Offer Agent asking Payment Agent if customer has good credit before showing a price*

#### Sprint 5-6: Order Finalization & Observability
- [ ] Build Order Agent to generate a JSON contract
- [ ] Build the Telemetry Dashboard to visualize agent logic chains

#### 🎯 Q2 Deliverable
> A fully autonomous demo where a user enters an address, gets a validated offer, negotiates (within limits), and places a confirmed order.

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
   git clone https://github.com/your-org/b2b-agentic-sales.git
   cd b2b-agentic-sales
   ```

2. **Backend Setup**
   ```bash
   cd backend
   poetry install
   poetry run uvicorn main:app --reload
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Environment Variables**
   ```bash
   cp .env.example .env
   # Configure your LLM API keys and database connections
   ```

### Project Structure

```
b2b-agentic-sales/
├── 📁 frontend/
│   ├── 📁 src/
│   │   ├── 📁 components/
│   │   ├── 📁 hooks/
│   │   └── 📁 context/
│   └── package.json
├── 📁 backend/
│   ├── 📁 agents/
│   │   ├── super_agent.py
│   │   ├── prospect_agent.py
│   │   ├── lead_gen_agent.py
│   │   ├── product_agent.py
│   │   ├── offer_mgmt_agent.py
│   │   ├── payment_agent.py
│   │   ├── order_agent.py
│   │   └── service_fulfillment_agent.py
│   ├── 📁 adk/
│   │   └── base_agent.py
│   ├── 📁 tools/
│   └── main.py
├── 📁 data/
│   └── 📁 vector_db/
├── 📁 docs/
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

<p align="center">
  <img src="https://img.shields.io/badge/AI-Powered-purple?style=for-the-badge" alt="AI Powered">
  <img src="https://img.shields.io/badge/Multi--Agent-System-blue?style=for-the-badge" alt="Multi-Agent">
  <img src="https://img.shields.io/badge/Zero-Hallucination-green?style=for-the-badge" alt="Zero Hallucination">
</p>
