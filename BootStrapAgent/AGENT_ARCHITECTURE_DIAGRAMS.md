# Agent Architecture Diagram

## Architecture Pattern Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT IMPLEMENTATION PATTERNS                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PATTERN 1: BaseAgent Pattern (BootStrapAgent)                               │
│ Used by: Payment Agent, Service Fulfillment Agent                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                    Custom BaseAgent Class                         │      │
│  │  ┌────────────────────────────────────────────────────────────┐  │      │
│  │  │ __init__(agent_id, context)                                │  │      │
│  │  │ • status: AgentStatus                                       │  │      │
│  │  │ • tools: Dict[str, Tool]                                    │  │      │
│  │  │ • memory: List[Dict]                                        │  │      │
│  │  │ • logger: Logger                                            │  │      │
│  │  └────────────────────────────────────────────────────────────┘  │      │
│  │                                                                   │      │
│  │  ┌────────────────────────────────────────────────────────────┐  │      │
│  │  │ Methods                                                     │  │      │
│  │  │ • register_tool(tool)                                       │  │      │
│  │  │ • execute_tool(name, **kwargs) → Dict                       │  │      │
│  │  │ • async process(input_data) → Dict                          │  │      │
│  │  │ • async send_message(receiver, content)                     │  │      │
│  │  │ • async receive_message(message)                            │  │      │
│  │  │ • add_to_memory(entry)                                      │  │      │
│  │  │ • get_memory(filter_type) → List                            │  │      │
│  │  └────────────────────────────────────────────────────────────┘  │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                    ▲                                         │
│                                    │ inherits                               │
│                        ┌───────────┴───────────┬──────────────┐            │
│                        │                       │              │            │
│          ┌─────────────────────┐   ┌──────────────────┐ ┌──────────────┐  │
│          │   PaymentAgent      │   │ ServiceFulfill   │ │  TestAgent   │  │
│          │                     │   │ Agent            │ │              │  │
│          │ Tools:              │   │ Tools:           │ │ (simple)     │  │
│          │ • check_credit      │   │ • check_service  │ └──────────────┘  │
│          │ • validate_method   │   │ • check_capacity │                    │
│          │ • assess_fraud      │   │ • get_slots      │                    │
│          │ • authorize         │   │ • schedule       │                    │
│          │ • process           │   │ • provision      │                    │
│          │                     │   │ • check_status   │                    │
│          │ State:              │   │ State:           │                    │
│          │ • Authorizations    │   │ • Installations  │                    │
│          │ • History           │   │ • Queue          │                    │
│          │ • Risk Config       │   │ • Coverage Map   │                    │
│          └─────────────────────┘   └──────────────────┘                    │
│                                                                              │
│  Features: Stateful ✓ Async ✓ A2A Communication ✓ Memory ✓                │
│  Complexity: HIGH (500-1000 LOC per agent)                                  │
│  Integration: Standalone within BootStrapAgent                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ PATTERN 2: Google ADK Direct (SuperAgent)                                   │
│ Used by: FAQ Agent, Greeting Agent, Simple Product Agent                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │              Google ADK Agent (Framework-provided)               │      │
│  │  ┌────────────────────────────────────────────────────────────┐  │      │
│  │  │ Agent(                                                      │  │      │
│  │  │   name: str                                                 │  │      │
│  │  │   model: str                                                │  │      │
│  │  │   instruction: str                                          │  │      │
│  │  │   description: str                                          │  │      │
│  │  │   tools: List[Tool]                                         │  │      │
│  │  │   generate_content_config: GenerateContentConfig            │  │      │
│  │  │ )                                                           │  │      │
│  │  └────────────────────────────────────────────────────────────┘  │      │
│  │                                                                   │      │
│  │  No additional state, memory, or A2A support built-in            │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐            │
│  │  FAQ Agent      │  │ Greeting Agent   │  │ Product Agent  │            │
│  │                 │  │                  │  │                │            │
│  │ tools: []       │  │ tools: []        │  │ tools: []      │            │
│  │ (minimal)       │  │ (minimal)        │  │ (minimal)      │            │
│  │                 │  │                  │  │                │            │
│  │ Temperature: .7 │  │ Temperature: .7  │  │ Temperature: .7│            │
│  │ Max tokens: 2K  │  │ Max tokens: 2K   │  │ Max tokens: 2K │            │
│  └─────────────────┘  └──────────────────┘  └────────────────┘            │
│                                                                              │
│  Features: Stateless ✓ LLM-centric ✓ Simple ✓ Embeddable ✓                │
│  Complexity: MINIMAL (20-40 LOC per agent)                                  │
│  Integration: Composable in SuperAgent root agent                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ PATTERN 3: Google ADK Extended (ProductAgent, ServiceabilityAgent)          │
│ Used by: Complex domain agents with rich tool sets                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │              Google ADK Agent + Tool Modules                     │      │
│  │  ┌────────────────────────────────────────────────────────────┐  │      │
│  │  │ Agent(                                                      │  │      │
│  │  │   name, model, instruction, description,                   │  │      │
│  │  │   tools=[                                                   │  │      │
│  │  │      query_documentation,   ┐                              │  │      │
│  │  │      search_specs,           ├─ From external modules       │  │      │
│  │  │      list_products,          ┤                              │  │      │
│  │  │      compare_products        ┘                              │  │      │
│  │  │   ]                                                         │  │      │
│  │  │ )                                                           │  │      │
│  │  └────────────────────────────────────────────────────────────┘  │      │
│  │                                                                   │      │
│  │  ┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐│      │
│  │  │ prompts.py     │  │ tools/           │  │ utils/           ││      │
│  │  │                │  │ ├── rag_tools.py │  │ ├── logger.py     ││      │
│  │  │ • Instruction  │  │ ├── product_...  │  │ ├── cache.py      ││      │
│  │  │ • Description  │  │ └── comparison... │  │ └── vector_db.py  ││      │
│  │  └────────────────┘  └──────────────────┘  └──────────────────┘│      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌─────────────────────────────┐  ┌────────────────────────────┐            │
│  │  ProductAgent               │  │ ServiceabilityAgent        │            │
│  │                             │  │                            │            │
│  │ Tools: 10+                  │  │ Tools: 6                   │            │
│  │ • RAG tools (docs)          │  │ • Address validation       │            │
│  │ • Catalog queries           │  │ • GIS coverage checks      │            │
│  │ • Comparisons               │  │ • Product availability     │            │
│  │                             │  │                            │            │
│  │ Temperature: 0.1 (accurate) │  │ Temperature: 0.0 (fact)    │            │
│  │ Modules: 3+                 │  │ Modules: 2+                │            │
│  │ LOC: 100-150                │  │ LOC: 100-150               │            │
│  │                             │  │                            │            │
│  │ State: None (Vector DB)     │  │ State: None                │            │
│  └─────────────────────────────┘  └────────────────────────────┘            │
│                                                                              │
│  Features: Modular ✓ Tool-rich ✓ Professional ✓ Scalable ✓                │
│  Complexity: MEDIUM (100-150 LOC + tool modules)                            │
│  Integration: Part of SuperAgent orchestration                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration Hierarchy

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER (SuperAgent)                        │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      Root Agent (Orchestrator)                       │ │
│  │                                                                      │ │
│  │  Intent: Route to appropriate sub-agent                            │ │
│  │  Model: Gemini 2.0-Flash                                           │ │
│  │  Temperature: 0.7 (conversational)                                 │ │
│  │                                                                      │ │
│  │           ┌──────────────┬───────────────┬──────────────┐           │ │
│  │           ▼              ▼               ▼              ▼           │ │
│  │   ┌────────────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────┐ │ │
│  │   │ Greeting Agent │ │ FAQ Agent   │ │Product Agent │ │Serviceab │ │ │
│  │   │                │ │             │ │              │ │lity Agent│ │ │
│  │   │ (ADK Direct)   │ │(ADK Direct) │ │ (ADK Extended)│ │(ADK Exte │ │ │
│  │   │ Simple LLM     │ │ Simple LLM  │ │ 10+ RAG tools│ │nded) GIS │ │ │
│  │   │ response       │ │ response    │ │ Vector DB    │ │tools     │ │ │
│  │   └────────────────┘ └─────────────┘ └──────────────┘ └──────────┘ │ │
│  │                                                                      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│     vs. (NOT integrated in SuperAgent, but standalone)                     │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                  BootStrapAgent Root Agent                            │ │
│  │                                                                      │ │
│  │  Intent: Orchestrate complex B2B sales workflows                   │ │
│  │  Model: Gemini 2.5-Flash                                           │ │
│  │  Pattern: Google ADK                                               │ │
│  │                                                                      │ │
│  │           ┌──────────────┬─────────────────────┬──────────────┐    │ │
│  │           ▼              ▼                     ▼              ▼    │ │
│  │   ┌────────────────┐ ┌──────────────────┐ ┌──────────────┐ ┌────┐ │ │
│  │   │  Test Agent    │ │ Payment Agent    │ │ Service Agent│ │(TBD)│ │
│  │   │                │ │ (BaseAgent)      │ │(BaseAgent)   │ │Order │ │
│  │   │ (ADK Direct)   │ │ 5 tools, Stateful│ │6 tools, State│ │Mgmt  │ │
│  │   │ Simple test    │ │ Credit, Payment  │ │Scheduling    │ │Agent │ │
│  │   │ agent          │ │ Fraud detection  │ │Provisioning  │ │      │ │
│  │   └────────────────┘ └──────────────────┘ └──────────────┘ └────┘ │ │
│  │                                                                      │ │
│  │  A2A Communication Enabled ─────────────────────────────────────┐  │ │
│  │  (Payment ←→ Service ←→ Offer Management)                       │  │ │
│  │                                                                      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Tool Complexity Spectrum

```
LOW COMPLEXITY                     MEDIUM COMPLEXITY                 HIGH COMPLEXITY
(Simple LLM)                       (Light tool wrapping)            (Complex business logic)

┌──────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│   FAQ Agent              │   │  Product Agent (RAG)     │   │  Payment Agent           │
│   Greeting Agent         │   │  Serviceability Agent    │   │  Service Fulfillment Ag  │
│                          │   │                          │   │                          │
│ • Static knowledge       │   │ • Tool-based lookup      │   │ • Complex state machine  │
│ • Minimal instruction    │   │ • Vector DB queries      │   │ • Business logic rules   │
│ • Pure LLM reasoning     │   │ • Modular tools          │   │ • Risk assessment        │
│ • 0 lines of tool code   │   │ • Utility modules        │   │ • Integration with APIs  │
│ • 20-40 LOC              │   │ • Professional logging   │   │ • A2A communication      │
│ • Temperature: 0.7       │   │ • 100-150 LOC            │   │ • Async processing       │
│ • Max tokens: 2K         │   │ • Temperature: 0.0-0.1   │   │ • 800-1000 LOC           │
│                          │   │ • Caching layers         │   │ • Temperature: N/A       │
└──────────────────────────┘   └──────────────────────────┘   └──────────────────────────┘
    ADK Direct                        ADK Extended                   BaseAgent Pattern
   (Simplest)                        (Balanced)                    (Most Complex)
```

---

## Decision Tree: Which Pattern to Use?

```
                          Need Agent?
                               │
                ┌──────────────┴──────────────┐
                │                             │
           Is stateless?                 Needs state?
                │                             │
                YES                          NO
                │                             │
    ┌───────────┴────────────┐      ┌────────┴──────────┐
    │                        │      │                   │
Single tool/  Multiple tools  Use BaseAgent        Needs A2A
simple?       or complex?     Pattern              communication?
    │              │                 │                   │
   YES            NO               YES             ┌─────┴──NO
    │              │                 │            │
    │         Use ADK Extended        │       Consider
    │         Pattern                │       external state
    │         • RAG tools            │       management
    │         • Org. modules         │
    │         • Professional         │
    │         • Logging/cache        │
    │                                │
 Use ADK Direct Pattern      ┌────────┴─────────────────┐
 • Minimal config            │                         │
 • Lightweight               │ (Payment, Service       │
 • Embeddable               │  Fulfillment Agents)     │
                            │                         │
                     BaseAgent Pattern:
                     ✓ Stateful design
                     ✓ Tool registration
                     ✓ Memory & history
                     ✓ A2A messaging
                     ✓ Async support
                     ✓ Error handling
```

---

## Data Flow Comparison

### BaseAgent Pattern (Payment Agent):

```
User Input
    │
    ▼
┌─────────────────────┐
│  PaymentAgent       │
│  process()          │
└─────────────────────┘
    │
    ├─ Log to memory
    │
    ├─► execute_tool("check_credit_score")
    │        │
    │        ├─► Private: _check_credit_score()
    │        │     • Hash EIN
    │        │     • Calc score
    │        │     • Return Dict
    │        │
    │        └─► Store in memory
    │
    ├─► execute_tool("validate_payment_method")
    │        │
    │        └─► Private: _validate_payment_method()
    │              • Parse input
    │              • Validate card/ACH/Wire
    │              • Generate payment_method_id
    │
    ├─► execute_tool("assess_fraud_risk")
    │        │
    │        └─► Complex ML scoring logic
    │
    ├─► execute_tool("authorize_payment")
    │        │
    │        └─► Store in pending_authorizations
    │
    └─► execute_tool("process_payment")
             │
             ├─► Call payment gateway
             └─► Update payment_history

Output: Full result with state updates
```

### ADK Extended Pattern (Product Agent):

```
User Input
    │
    ▼
┌──────────────────────┐
│  ADK Agent           │
│  (LLM-powered)       │
└──────────────────────┘
    │
    ├─ LLM decides which tool(s) to call
    │
    ├─► query_product_documentation()
    │     └─► ChromaDB vector search
    │
    ├─► search_technical_specs()
    │     └─► Structured query
    │
    ├─► compare_products()
    │     └─► Light wrapper function
    │
    └─► get_product_features()
          └─► API call or DB lookup

Output: LLM-formatted response with tool results
```

---

## Deployment Readiness

```
                    BootStrapAgent                SuperAgent
                  (BaseAgent Pattern)          (ADK Pattern)

Development         ██████████ (100%)           ██████████ (100%)
Testing             ████████░░ (80%)            ██████░░░░ (60%)
Production Ready    ██████░░░░ (60%)            ██████████ (100%)
Scalability         ████░░░░░░ (40%)            ██████████ (100%)
Monitoring          ██████░░░░ (60%)            ████░░░░░░ (40%)
Documentation       ██████████ (100%)           ████░░░░░░ (40%)
Deployment Ease     ████░░░░░░ (40%)            ██████████ (100%)
Integration         ██░░░░░░░░ (20%)            ██████████ (100%)


Recommendation:
┌──────────────────────────────────────────────────────────────────┐
│ BootStrapAgent (Payment/Service):                                │
│ ✓ Use for: Internal B2B workflows, complex state management      │
│ ✗ Avoid for: Customer-facing APIs, high-scale deployments       │
│                                                                  │
│ SuperAgent (Product/Serviceability):                            │
│ ✓ Use for: Customer-facing, scalable, orchestrated workflows     │
│ ✗ Avoid for: Complex stateful operations, A2A communication     │
└──────────────────────────────────────────────────────────────────┘
```
