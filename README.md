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

<div align="center">

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '18px', 'fontFamily': 'arial'}, 'flowchart': {'nodeSpacing': 30, 'rankSpacing': 50, 'curve': 'basis'}}}%%
graph TD
    subgraph Client ["<br/>🖥️ CLIENT LAYER - React<br/><br/>"]
        UI["<br/>B2B Chat Interface<br/><br/>"]
        Socket["<br/>WebSocket Client<br/><br/>"]
    end

    subgraph Orchestrator ["<br/>🧠 ORCHESTRATION LAYER - Python<br/><br/>"]
        SuperAgent["<br/>🧠 SUPER AGENT<br/>Orchestrator<br/><br/>"]
        Router["<br/>Intent Router<br/><br/>"]
        Steer["<br/>Steering & Guardrails<br/><br/>"]
    end

    subgraph Mesh ["<br/>🤝 AGENT MESH - A2A Protocol<br/><br/>"]
        subgraph Discovery ["Discovery"]
            P_Agent["<br/>👤 Prospect Agent<br/><br/>"]
            L_Agent["<br/>📊 Lead Gen Agent<br/><br/>"]
        end
        subgraph Config ["Configuration"]
            Prod_Agent["<br/>📦 Product Agent<br/><br/>"]
            Off_Agent["<br/>💰 Offer Mgmt Agent<br/><br/>"]
        end
        subgraph Transaction ["Transaction"]
            Pay_Agent["<br/>💳 Payment Agent<br/><br/>"]
            Ord_Agent["<br/>🛒 Order Agent<br/><br/>"]
            Svc_Agent["<br/>🔧 Service Fulfillment Agent<br/><br/>"]
        end
    end

    subgraph Tools ["<br/>⚙️ INFRASTRUCTURE & TOOLS - ADK/MCP<br/><br/>"]
        API_GW["<br/>Backend API Gateway<br/><br/>"]
        RAG["<br/>RAG Engine<br/>Vector DB<br/><br/>"]
        Obs["<br/>Observability<br/>& Logging<br/><br/>"]
        DB[("<br/>State<br/>Database<br/><br/>")]
    end

    UI <--> Socket
    Socket <--> SuperAgent
    SuperAgent --> Router
    Router --> Discovery
    Router --> Config
    Router --> Transaction
    Discovery -- "A2A" --> Config
    Config -- "A2A" --> Transaction
    P_Agent -- "MCP/REST" --> API_GW
    Prod_Agent -- "MCP/REST" --> RAG
    Off_Agent -- "MCP/REST" --> API_GW
    Pay_Agent -- "MCP/REST" --> API_GW
    Ord_Agent -- "MCP/REST" --> DB
    Svc_Agent -- "MCP/REST" --> API_GW
    Steer -.-> SuperAgent
    Mesh -.-> Obs

    style SuperAgent fill:#ff6b6b,stroke:#333,stroke-width:3px,color:#fff
    style UI fill:#4ecdc4,stroke:#333,stroke-width:2px
    style DB fill:#95e1d3,stroke:#333,stroke-width:2px
    style P_Agent fill:#a8e6cf,stroke:#333,stroke-width:2px
    style L_Agent fill:#a8e6cf,stroke:#333,stroke-width:2px
    style Prod_Agent fill:#ffd93d,stroke:#333,stroke-width:2px
    style Off_Agent fill:#ffd93d,stroke:#333,stroke-width:2px
    style Pay_Agent fill:#c9b1ff,stroke:#333,stroke-width:2px
    style Ord_Agent fill:#c9b1ff,stroke:#333,stroke-width:2px
    style Svc_Agent fill:#c9b1ff,stroke:#333,stroke-width:2px
```

</div>

### Detailed System Flow Diagram

The following sequence diagram shows a complete sales flow involving multiple agents:

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '16px'}, 'sequence': {'width': 200, 'height': 60, 'boxMargin': 20, 'mirrorActors': false}}}%%
sequenceDiagram
    autonumber
    
    box rgb(230, 245, 255) Customer Interface
        participant Customer as 👤 B2B Customer
        participant UI as 🖥️ Chat Interface
    end
    
    box rgb(255, 235, 235) Orchestration
        participant Super as 🧠 Super Agent
    end
    
    box rgb(235, 255, 235) Discovery Agents
        participant Prospect as 👤 Prospect Agent
        participant LeadGen as 📊 Lead Gen Agent
    end
    
    box rgb(255, 250, 230) Configuration Agents
        participant Product as 📦 Product Agent
        participant Offer as 💰 Offer Mgmt Agent
    end
    
    box rgb(240, 235, 255) Transaction Agents
        participant Payment as 💳 Payment Agent
        participant Order as 🛒 Order Agent
        participant ServiceFulfill as 🔧 Service Fulfillment Agent
    end
    
    box rgb(245, 245, 245) Infrastructure
        participant API as ⚙️ Backend APIs
        participant Log as 📊 Observability
    end

    Customer->>UI: "I need internet for my new office in Philadelphia"
    UI->>Super: WebSocket Message
    
    Note over Super: Intent Analysis & Routing
    
    rect rgb(235, 255, 235)
        Note over Prospect,LeadGen: Discovery Phase
        Super->>Prospect: Extract company details
        Prospect->>Super: Context (Company, Address, Contact)
        Super->>LeadGen: Qualify lead
        LeadGen->>Super: BANT Score & Readiness
    end
    
    rect rgb(255, 250, 230)
        Note over Product,Offer: Configuration Phase
        Super->>ServiceFulfill: Check address serviceability
        ServiceFulfill->>API: Query GIS/Serviceability API
        API-->>ServiceFulfill: Deterministic Response
        ServiceFulfill->>Super: ✅ Address Serviceable
        
        Super->>Product: Get product recommendations
        Product->>API: Query Vector DB (RAG)
        API-->>Product: Product Specs
        Product->>Super: Recommended Products
        
        Super->>Offer: Calculate pricing
        Offer->>API: Query Pricing Engine
        API-->>Offer: Pricing & Bundles
        Offer->>Super: Custom Quote
    end
    
    rect rgb(240, 235, 255)
        Note over Payment,ServiceFulfill: Transaction Phase
        Super->>Payment: Run credit check
        Payment->>API: Query Payment Gateway
        API-->>Payment: Credit Approved
        Payment->>Super: ✅ Credit Approved
        
        Super->>Order: Generate contract
        Order->>API: Create Order in DB
        API-->>Order: Order Confirmed
        Order->>Super: Contract & Order ID
        
        Super->>ServiceFulfill: Schedule installation
        ServiceFulfill->>API: Query Scheduler API
        API-->>ServiceFulfill: Installation Date
        ServiceFulfill->>Super: ✅ Installation Scheduled
    end
    
    Super->>UI: Natural Language Response with Full Quote
    UI->>Customer: "Great news! Your Philadelphia office is serviceable..."
    
    Note over Log: All steps logged for auditability
```

### Agent Interaction Flow

<div align="center">

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '16px'}, 'flowchart': {'nodeSpacing': 40, 'rankSpacing': 60, 'curve': 'basis', 'padding': 20}}}%%
flowchart LR
    subgraph Discovery["<br/>🔍 DISCOVERY PHASE<br/><br/>"]
        A["<br/>💬 Customer Intent<br/><br/>"] --> B["<br/>👤 Prospect Agent<br/>Extract Details<br/><br/>"]
        B --> C["<br/>📊 Lead Gen Agent<br/>BANT Scoring<br/><br/>"]
    end
    
    subgraph Configuration["<br/>⚙️ CONFIGURATION PHASE<br/><br/>"]
        C --> D["<br/>📦 Product Agent<br/>Tech Specs & RAG<br/><br/>"]
        D --> E["<br/>💰 Offer Mgmt Agent<br/>Pricing & Bundles<br/><br/>"]
    end
    
    subgraph Transaction["<br/>💰 TRANSACTION PHASE<br/><br/>"]
        E --> F["<br/>💳 Payment Agent<br/>Credit Check<br/><br/>"]
        F --> G["<br/>🛒 Order Agent<br/>Contract & Checkout<br/><br/>"]
        G --> H["<br/>🔧 Service Fulfillment Agent<br/>Schedule Installation<br/><br/>"]
    end
    
    subgraph Output["<br/>✅ OUTPUT<br/><br/>"]
        H --> I["<br/>📋 Confirmed Order<br/>& Installation Date<br/><br/>"]
    end

    style A fill:#e8f4f8,stroke:#333,stroke-width:2px
    style B fill:#a8e6cf,stroke:#333,stroke-width:2px
    style C fill:#a8e6cf,stroke:#333,stroke-width:2px
    style D fill:#ffd93d,stroke:#333,stroke-width:2px
    style E fill:#ffd93d,stroke:#333,stroke-width:2px
    style F fill:#c9b1ff,stroke:#333,stroke-width:2px
    style G fill:#c9b1ff,stroke:#333,stroke-width:2px
    style H fill:#c9b1ff,stroke:#333,stroke-width:2px
    style I fill:#d4edda,stroke:#333,stroke-width:3px
```

</div>

### Data Flow & Lifecycle

The complete data flow follows these stages:

<div align="center">

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '16px'}, 'state': {'padding': 20}}}%%
stateDiagram-v2
    direction LR
    [*] --> Ingest: Customer Message
    
    state "📥 INGEST" as Ingest
    state "🧠 ORCHESTRATION" as Orchestration
    state "🔀 ROUTING" as Routing
    state "🤝 AGENT COLLABORATION" as AgentCollaboration
    state "🔒 DETERMINISTIC QUERY" as DeterministicQuery  
    state "✨ SYNTHESIS" as Synthesis
    state "💬 RESPONSE" as Response
    
    Ingest --> Orchestration: WebSocket
    Orchestration --> Routing: Intent Analysis
    Routing --> AgentCollaboration: Task Distribution
    AgentCollaboration --> DeterministicQuery: API Calls
    DeterministicQuery --> Synthesis: Results Aggregation
    Synthesis --> Response: Natural Language
    Response --> [*]: Customer Receives Answer
    
    note right of Orchestration
        Super Agent analyzes intent
        and determines which agents to invoke
    end note
    
    note right of AgentCollaboration
        A2A Protocol communication between:
        • Prospect Agent
        • Lead Gen Agent  
        • Product Agent
        • Offer Mgmt Agent
        • Payment Agent
        • Order Agent
        • Service Fulfillment Agent
    end note
    
    note right of DeterministicQuery
        Zero-hallucination APIs:
        • Pricing Engine
        • GIS/Serviceability
        • Payment Gateway
        • Order Database
    end note
```

</div>

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

All agents are developed using a custom **ADK (Agent Development Kit)** ensuring standardized logging and error handling.

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

<div align="center">

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '18px', 'pieTitleTextSize': '20px', 'pieSectionTextSize': '16px', 'pieLegendTextSize': '16px'}}}%%
pie showData
    title Agent Types Distribution (8 Total Agents)
    "Orchestrator (Super Agent)" : 1
    "Operational (Prospect, Lead Gen)" : 2
    "Info/RAG (Product)" : 1
    "Deterministic (Offer Mgmt, Service Fulfillment)" : 2
    "Transactional (Order, Payment)" : 2
```

</div>

---

## 🎯 Core Design Principles

### Determinism vs. Autonomy

To prevent **"hallucinations"** in critical business areas, we separate concerns:

<div align="center">

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '16px'}, 'flowchart': {'nodeSpacing': 40, 'rankSpacing': 50, 'padding': 20}}}%%
graph LR
    subgraph Autonomous["<br/>🤖 LLM FLOWS - Autonomous<br/><br/>"]
        A1["<br/>💬 Conversation<br/><br/>"]
        A2["<br/>📝 Summarization<br/><br/>"]
        A3["<br/>🔍 Data Extraction<br/><br/>"]
    end
    
    subgraph Deterministic["<br/>🔒 DETERMINISTIC FLOWS - Zero Hallucination<br/><br/>"]
        D1["<br/>💰 Pricing<br/>(Offer Mgmt Agent)<br/><br/>"]
        D2["<br/>📦 Inventory<br/>(Product Agent)<br/><br/>"]
        D3["<br/>📍 Serviceability<br/>(Service Fulfillment Agent)<br/><br/>"]
    end
    
    subgraph Sources["<br/>📊 SOURCES OF TRUTH<br/><br/>"]
        S1[("🔗 APIs")]
        S2[("🗄️ Databases")]
    end
    
    Autonomous --> |"Context & Intent"| Deterministic
    Deterministic --> |"Fetch Data"| Sources
    Sources --> |"Rigid Data"| Deterministic

    style Autonomous fill:#fff3cd,stroke:#333,stroke-width:2px
    style Deterministic fill:#d4edda,stroke:#333,stroke-width:2px
    style Sources fill:#cce5ff,stroke:#333,stroke-width:2px
    style A1 fill:#ffeaa7,stroke:#333
    style A2 fill:#ffeaa7,stroke:#333
    style A3 fill:#ffeaa7,stroke:#333
    style D1 fill:#55efc4,stroke:#333
    style D2 fill:#55efc4,stroke:#333
    style D3 fill:#55efc4,stroke:#333
```

</div>

| Flow Type | Use Cases | Key Principle |
|-----------|-----------|---------------|
| **LLM Flows (Autonomous)** | Conversation, Summarization, Extracting structured data from unstructured text | Creative & Flexible |
| **Deterministic Flows** | Pricing, Inventory, Serviceability | **MUST** come from rigid APIs - agents are "tool users" that fetch data, not invent it |

### Observability & Steering

| Feature | Description |
|---------|-------------|
| **Agent Steering** | "System Prompts" and "Guardrails" at Super Agent level prevent discussion of competitors or sensitive topics |
| **Structured Logging** | All A2A communication logged in structured JSON format, enabling "replay" of sales to understand agent decisions |

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
| ![ADK](https://img.shields.io/badge/Custom_ADK-Agent_Runtime-orange) | Agent Development Kit |
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

<div align="center">

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '16px'}, 'flowchart': {'nodeSpacing': 40, 'rankSpacing': 50, 'padding': 20}}}%%
graph TB
    subgraph Frontend["<br/>🎨 FRONTEND<br/><br/>"]
        React["<br/>React 19<br/>Functional Components<br/><br/>"]
        Tailwind["<br/>Tailwind CSS<br/>Rapid UI<br/><br/>"]
        SocketClient["<br/>Socket.io Client<br/>Real-time Streaming<br/><br/>"]
    end
    
    subgraph Backend["<br/>⚙️ BACKEND & AGENTS<br/><br/>"]
        FastAPI["<br/>FastAPI<br/>WebSockets & REST<br/><br/>"]
        ADK["<br/>Custom ADK<br/>Agent Development Kit<br/><br/>"]
        Python["<br/>Python 3.12+<br/><br/>"]
    end
    
    subgraph Protocols["<br/>🔗 PROTOCOLS<br/><br/>"]
        A2A["<br/>A2A Protocol<br/>JSON-RPC Messaging<br/><br/>"]
        MCP["<br/>MCP Protocol<br/>Tool Connections<br/><br/>"]
        REST["<br/>REST APIs<br/>External Services<br/><br/>"]
    end
    
    subgraph Data["<br/>💾 DATA LAYER<br/><br/>"]
        LLM["<br/>LLM Provider<br/>Agnostic/Abstracted<br/><br/>"]
        Chroma["<br/>ChromaDB<br/>Vector DB for RAG<br/><br/>"]
        SQLite["<br/>SQLite / PostgreSQL<br/>Transactional DB<br/><br/>"]
    end
    
    Frontend --> |"WebSocket"| Backend
    Backend --> Protocols
    Protocols --> Data

    style Frontend fill:#e1f5fe,stroke:#333,stroke-width:2px
    style Backend fill:#fff3e0,stroke:#333,stroke-width:2px
    style Protocols fill:#f3e5f5,stroke:#333,stroke-width:2px
    style Data fill:#e8f5e9,stroke:#333,stroke-width:2px
    style React fill:#61dafb,stroke:#333
    style FastAPI fill:#009688,stroke:#333,color:#fff
    style Python fill:#3776ab,stroke:#333,color:#fff
```

</div>

---

## 📅 Project Roadmap

### Timeline Overview (2 Quarters)

<div align="center">

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '14px'}, 'gantt': {'titleTopMargin': 25, 'barHeight': 30, 'barGap': 10, 'topPadding': 50, 'leftPadding': 100, 'gridLineStartPadding': 35, 'fontSize': 14, 'sectionFontSize': 16}}}%%
gantt
    title 📅 B2B Agentic Sales System - Development Roadmap
    dateFormat YYYY-MM-DD
    
    section 🛠️ Q1: Foundation Phase
    Infrastructure Setup (React + FastAPI + WebSocket)    :a1, 2025-01-01, 4w
    Build ADK Base Class (Logging, Memory, Tools)         :a1b, 2025-01-01, 4w
    Super Agent with Basic Routing                        :a2, after a1, 2w
    RAG Setup - Ingest Product PDFs to ChromaDB           :a2b, after a1, 2w
    Product Agent (RAG-based Q&A)                         :a2c, after a2, 2w
    Prospect Agent (Extract Name, Address)                :a3, after a2c, 2w
    Service Fulfillment Agent (Serviceability Check)      :a3b, after a2c, 2w
    Q1 Deliverable - Functional Sales Chat                :milestone, m1, after a3b, 0d
    
    section 💰 Q2: Transaction Phase
    Offer Management Agent (Pricing & Bundles)            :b1, after a3b, 2w
    Payment Agent (Credit Check)                          :b1b, after a3b, 2w
    A2A Handshake Implementation                          :b2, after b1, 2w
    Inter-Agent Communication (Without User Input)        :b2b, after b1, 2w
    Order Agent (Contract Generation)                     :b3, after b2, 2w
    Telemetry Dashboard (Agent Logic Visualization)       :b3b, after b2, 2w
    Q2 Deliverable - Full Autonomous Sales Demo           :milestone, m2, after b3b, 0d
```

</div>

### Quarter 1: Foundation & Discovery Phase

> **Goal:** A working "Sales Assistant" that can chat, identify users, and check service availability.

#### Sprint 1-2: Infrastructure Setup
- [x] Set up React Frontend + FastAPI Backend
- [x] Implement WebSocket streaming
- [x] Build the ADK (Base Class): Logging, Memory, and Tool definitions

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
│   │   ├── product_agent.py
│   │   └── ...
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
