# B2B Conversational Sales Agent

A multi-agent system for end-to-end B2B telecom sales conversations, built on Google ADK 2.x with Gemini: an orchestration **workflow** in a gateway, **10 domain agents as independent A2A services**, **REST + MCP tool services**, and an **A2UI generative UI** that turns every step of the journey into interactive cards in the chat, all backed by PostgreSQL.

---

## What This Project Is

This repository implements a **multi-agent system** that automates the full B2B telecom sales lifecycle, from prospect discovery through order fulfillment. A **gateway** (`SuperAgent/`) runs an ADK 2.x `Workflow` that routes each customer turn to one of 10 specialized agents. Each agent is its own **A2A (Agent2Agent) service**, deployable and scalable on its own.

Built on **Google ADK 2.10 (Agent Development Kit)** with **Google Gemini**, the system enforces a strict separation between:

- **LLM-driven reasoning:** intent classification and natural-language conversation
- **Deterministic execution:** database lookups, pricing, address validation, payment processing, and the business-mandatory handoffs between agents

The LLM decides *what* the customer wants; critical business data (addresses, prices, orders) always comes from deterministic tools, never from generated text.

The conversation is also **visual and clickable**. Tool results reach the browser as **[A2UI 1.0](https://a2ui.org) surfaces** (coverage, plans, quotes, cart, order, installation times, payment, receipt) rendered with **CopilotKit's** standard component catalog. Card buttons send the customer's next message, payment details are entered in a secure form that bypasses the model, and agents keep their replies to one or two sentences because the card shows the data. See [A2UI Generative UI](#a2ui-generative-ui).

| Protocol | Role in this system |
|---|---|
| **A2A** | Gateway ⇄ 10 agent services (one agent per turn plus deterministic handoffs) |
| **MCP** | Agents ⇄ catalog and serviceability tool services |
| **A2UI** | Gateway → browser: interactive UI built from tool results |

---

## Architecture

```mermaid
graph TD
    USER["Browser<br/>React 19 UI + CopilotKit<br/>A2UI renderer"] -->|HTTPS SSE<br/>text + A2UI surfaces| GW["Gateway :8000<br/>FastAPI + sales_journey Workflow<br/>+ A2UI surface builders"]
    USER -->|secure payment form| GW
    GW -->|POST /payment-methods<br/>no LLM| PAYS["payment service<br/>(payment_agent :8206)"]
    GW -->|A2A JSON-RPC| AG["10 agent services :8201-8210<br/>ADK agents served with to_a2a"]
    AG -->|MCP streamable HTTP| TS["Tool services<br/>catalog :8101, serviceability :8102<br/>REST /api/v1 + MCP /mcp/"]
    GW --> PG[("PostgreSQL 16<br/>sessions, memory, A2A tasks,<br/>business tables")]
    AG --> PG
    TS --> PG
    GW -->|router| GEM(("Gemini API"))
    AG -->|agents| GEM
    GW -.->|OTLP traces, optional| LF(("Langfuse"))
    AG -.-> LF
    TS -.-> LF
```

```
User → React UI → Gateway (FastAPI → ADK Runner → sales_journey Workflow)
     → RemoteA2aAgent → Agent service (ADK agent → tools / MCP) → PostgreSQL
```

Responses stream back to the browser via Server-Sent Events (SSE): the agents' text, plus an `a2ui` event with an A2UI surface for every tool result that has a card ([A2UI Generative UI](#a2ui-generative-ui)). When Langfuse keys are set, every service also exports OpenTelemetry traces, one trace per turn across all hops ([Agent Observability](#agent-observability-langfuse)). A per-service overview with the full node graph is in [AGENTS.md](AGENTS.md#system-architecture).

### Architectural Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  PRESENTATION    React 19 + Vite + Tailwind  ⇄  FastAPI SSE gateway │
│  GENERATIVE UI   A2UI 1.0 surfaces (gateway builders, deterministic) │
│                  → CopilotKit renderer, standard catalog, actions   │
├─────────────────────────────────────────────────────────────────────┤
│  ORCHESTRATION   sales_journey Workflow: router LLM, dispatch,      │
│                  deterministic handoffs, sessions, memory           │
├──────────────┬───────────────────┬──────────────────────────────────┤
│ DISCOVERY    │ CONFIGURATION     │ TRANSACTION    (A2A services)    │
│ Discovery    │ Serviceability    │ Order · Payment · Fulfillment    │
│ Greeting     │ Product           │ Customer Communication           │
│ FAQ          │ Offer Management  │                                  │
├──────────────┴───────────────────┴──────────────────────────────────┤
│  TOOL SERVICES   catalog: REST+MCP+RAG · serviceability: REST+MCP   │
├─────────────────────────────────────────────────────────────────────┤
│  DATA            PostgreSQL 16 (Cloud SQL in GCP) · SMTP · Gemini   │
├─────────────────────────────────────────────────────────────────────┤
│  OBSERVABILITY   OpenTelemetry → Langfuse (optional, all services)  │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Separation of concerns** | Each agent owns one domain and runs as its own service |
| **Zero-hallucination for critical data** | Addresses, prices, orders always come from deterministic tools |
| **Router-only orchestrator** | The gateway classifies intent and dispatches; it never writes customer-facing domain answers |
| **Deterministic handoffs** | Mandatory next steps (Discovery → Serviceability, Scheduling → Payment) are Python rules in the workflow |
| **Temperature-stratified agents** | Greeting 0.7, fulfillment 0.3, FAQ 0.2; the router and all other agents 0.0 |
| **Structured data contracts** | Tools return JSON (not prose) to prevent LLM rephrasing of critical values |
| **Shared journey-state contracts** | Agents publish authoritative context into ADK session state; it crosses the A2A boundary through metadata and `_context_update` |
| **A2A service per agent** | No in-process coupling: no `importlib` loading or `sys.modules` calls between agents (see [Agent Service Guide](#agent-service-guide)) |
| **Deterministic generative UI** | A2UI surfaces are built by the gateway from tool results and journey state, never written by a model; card buttons send customer-voice messages |
| **Payment data never touches a model** | Card and bank details go from the secure form to a model-free REST route; numbers typed into chat are masked before routing |

### How Agents Communicate

```
User message → Gateway workflow (sales_journey)
                 │
                 ├─ prepare_turn → route_intent (router LLM, RouteDecision)
                 │     pure greetings skip the router (fast path)
                 │
                 ├─ dispatch → RemoteA2aAgent("<agent>")  ── A2A JSON-RPC ──►  agent service
                 │     sends: directed message (a2a_outbound_message)
                 │            + metadata: journey context, transcript, user profile
                 │
                 ├─ agent tools change journey keys → "_context_update" in tool responses
                 │     ContextBridgePlugin merges them into gateway session state
                 │
                 ├─ HandoffPolicyNode (deterministic, same turn, ≤ 2 hops)
                 │     discovery_agent           → serviceability_agent   (address not yet checked)
                 │     discovery_agent           → order_agent            (contact saved for a waiting order)
                 │     order_agent               → service_fulfillment_agent (order created: show slots)
                 │     service_fulfillment_agent → payment_agent          (installation booked)
                 │
                 └─ EventMapper → SSE: token text + one `a2ui` surface per tool result with a card
```

- **Gateway → agent** is A2A. Each domain node in the workflow is a `RemoteA2aAgent` that fetches the agent's card (`/.well-known/agent-card.json`) and sends only the directed message for that agent, with the gateway session id as the A2A context id.
- **Shared journey state is the data plane.** The five journey keys (`customer_context`, `serviceability_context`, `offer_context`, `order_context`, `payment_context`) travel to the agent as A2A request metadata. `import_forwarded_context` (a `before_agent_callback`) copies them into the agent's session state so its tools and templated instructions can use them.
- **Agent → gateway.** A2A does not return remote state changes, so `export_context_delta` (an `after_tool_callback`) adds `_context_update` to a tool's response. The gateway's `ContextBridgePlugin` merges it into the session before the handoff node runs.
- **Deterministic handoffs.** `HandoffPolicyNode` checks the merged state after each agent and routes to the next agent within the same turn.
- **Cross-domain side effects** do not call other agents. Notifications are written to a transactional **outbox** (`notifications` rows with `status='pending'`) that the customer communication service dispatches; quote status updates and customer-state lookups use shared SQL helpers (`sales_common.repositories`).

### Session State, Sessions and Memory

The system uses **ADK session state as a shared, structured memory layer** across the sales journey. It is a deliberate contract for moving exact business facts between agents without re-parsing free-form conversation.

| Scope | Keys | Written by |
|---|---|---|
| Session (journey) | `customer_context` (incl. `contact: {name, email, phone}`) | discovery tools after registration, lookup or saving a contact |
| | `serviceability_context` | serviceability agent callback after a coverage check |
| | `offer_context` | offer management tools after a quote |
| | `order_context` | order tools after order creation |
| | `payment_context` | payment tools after processing |
| Session (workflow) | `last_agent`, `last_reply`, `transcript`, `turn_user_message`, `handoff_hops`, `a2a_outbound_message`, `appointment_confirmed_order`, `order_created_order`, `order_waiting_for_contact` | gateway workflow nodes and `ContextBridgePlugin` |
| User (`user:`) | `user:customer_id`, `user:company_name` | `finish_turn`, so a returning browser is recognized in a new session |

- **Sessions** are durable: ADK `DatabaseSessionService` on PostgreSQL in the gateway and in every agent service. They survive restarts and are shared by all instances.
- **Identity:** the browser generates an anonymous `csa_uid` (UUIDv4); the ADK user id is `web:<uuid>`. Chat tokens are signed with `SESSION_SECRET_KEY` and can be revoked.
- **Long-term memory:** `sales_common.memory.PostgresMemoryService` stores user and agent turns in `adk_memories` (PostgreSQL full-text search, scoped per app and user). The session is saved to memory after each turn, and relevant memories are given to the router.
- **Context management:** every ADK `App` uses events compaction (every 8 invocations with overlap 2, or above 60k tokens) and Gemini context caching (TTL 30 min, min 4096 tokens).

**Why:** exact values (zip codes, order ids, offer ids, transaction ids) are never regenerated from conversation text; multi-turn steps (payment, scheduling, activation) resume from state; retries and restarts are safe; and each state write is observable in logs.

---

## A2UI Generative UI

The chat does not only stream text. Every step of the sales journey that produces structured data (coverage result, plans, quote, cart, order, installation times, payment, receipt) appears **inside the conversation as an interactive card** built with **[A2UI 1.0](https://a2ui.org)**, the open, declarative format for agent-generated UI, and rendered by **CopilotKit's generative UI renderer** with its standard component catalog. Buttons on the cards drive the conversation: a click sends a customer message, so the customer can complete a purchase almost entirely by clicking.

A2UI is the third pillar of the system next to **A2A** (agents talk to each other) and **MCP** (agents use tools):

| Protocol | Between | Carries |
|---|---|---|
| A2A | gateway ⇄ agent services | messages, journey context, tool results |
| MCP | agent ⇄ tool services | tool calls (catalog, serviceability) |
| **A2UI** | gateway → browser | **UI as data**: components, data model, actions |

### Why A2UI, and why the gateway builds it

- **No parsing of prose.** Before A2UI, cards were recovered by regular expressions from the agent's reply text and broke whenever an agent reworded a reply. A2UI surfaces are built from the **tool results** themselves.
- **Zero hallucination in the UI.** The gateway builds every surface **deterministically** in `SuperAgent/server/api/a2ui.py` from the JSON a tool returned (prices, speeds, slots, ids) plus the journey state. No model writes UI, so a card can never show a price or a time slot the tools did not return. This follows the same rule as the rest of the system: critical data comes from tools, never from generated text.
- **Short replies.** Because the card shows the data, agents answer in one or two sentences (the shared "Cards in the chat" instruction in `sales_common/prompts.py`) instead of repeating lists, prices and ids.
- **A standard, portable format.** Surfaces use only components of CopilotKit's standard catalog (69 components: Card, Row, Column, Text, Table, Button, TextField, Badge, …) plus one app component. The catalog is exported as an A2UI 1.0 document, so another renderer, a validator or a future LLM-authored surface can use the same contract.

### Architecture

```mermaid
graph LR
    subgraph Agents["A2A agent services"]
      T["tool result JSON<br/>(quote, slots, payment methods, ...)"]
    end
    subgraph Gateway["Gateway :8000"]
      CB["ContextBridgePlugin<br/>journey state"]
      EM["EventMapper<br/>(api/sse.py)"]
      B["A2UI builders<br/>(api/a2ui.py)"]
      PM["POST /api/payment-methods"]
    end
    subgraph Browser["React UI :3000"]
      API["streamChat (utils/api.js)"]
      CTX["ChatContext<br/>message.a2uiSurfaces"]
      SURF["A2UISurface<br/>manager.ingest + GenerativeUISurface"]
      RT["CopilotKitProvider<br/>generativeUI = salesUI + theme"]
      FORM["SecurePaymentForm"]
    end
    PAY["payment service<br/>POST /payment-methods (no LLM)"]

    T -->|function_response over A2A| EM
    CB -->|state at turn start + _context_update| EM
    EM --> B
    B -->|A2UI 1.0 operations| EM
    EM -->|"SSE a2ui event"| API
    API --> CTX --> SURF
    SURF --> RT
    RT -->|"Button → sendChatMessage(message)"| CTX
    CTX -->|"POST /api/chat (next turn)"| Gateway
    FORM -->|card / bank details| PM --> PAY
```

The whole loop for one click:

```mermaid
sequenceDiagram
    participant C as Customer
    participant UI as React + CopilotKit renderer
    participant G as Gateway (sales_journey)
    participant A as Agent (A2A)
    C->>UI: clicks "Place my order" on the cart card
    UI->>G: POST /api/chat "That's everything. Please place my order."
    G->>A: order_agent (A2A) → create_order
    A-->>G: function_response {order_id, status, ...} + _context_update
    G-->>UI: SSE a2ui {kind: order, operations: [createSurface …]}
    G->>A: handoff → service_fulfillment_agent → check_availability
    A-->>G: function_response {available_slots: [...]}
    G-->>UI: SSE a2ui {kind: scheduling, one Button per slot}
    G-->>UI: SSE token "Please pick an installation time below."
    C->>UI: clicks "8 AM–12 PM" on Fri, Nov 27
    UI->>G: POST /api/chat "Please book my installation for Friday, November 27, 2026, 8 AM–12 PM (morning)."
```

### Components

| Piece | Where | Role |
|---|---|---|
| Surface builders | `SuperAgent/server/api/a2ui.py` | `build_surface(tool, response, state)` → `{surface_id, kind, operations}` or `None`. Pure functions, no model; unwraps MCP results (`sales_common.mcp_client.mcp_result_payload`); whole numbers shown without `.0` (A2A carries ints as floats) |
| Event mapping | `SuperAgent/server/api/sse.py` (`EventMapper`) | Calls the builders for every remote `function_response`, sends each surface once per turn, keeps a journey-state copy (session state at turn start + each tool's `_context_update`), strips payment tokens from every browser-bound payload |
| Exported catalog | `SuperAgent/server/a2ui/catalog.json` | A2UI 1.0 catalog document of `salesUI` (70 components, 17 functions) produced by `npm run export:a2ui-catalog`; the gateway tests validate every surface against it |
| Generative UI | `SuperAgent/client/src/a2ui/salesUI.js` | `createGenerativeUI({ extends: [standardUI], components: { SecurePaymentForm }, functions: { sendChatMessage } })` |
| Provider | `SuperAgent/client/src/a2ui/GenerativeUIProvider.jsx` | `CopilotKitProvider` with `generativeUI={{ ui: salesUI, theme: salesTheme }}`. The app has no CopilotKit runtime: replies come from the ADK gateway, so the provider gets one inert local agent (`InertAgent.js`, never run, no keys) |
| Renderer | `SuperAgent/client/src/components/A2UISurface.jsx` | Ingests a surface's operations into the generative UI runtime (`useGenerativeUIRuntime().manager.ingest`, thread `sales-chat`, target = `surface_id`) and draws it with `<GenerativeUISurface id>` inside the assistant message |
| Actions | `SuperAgent/client/src/contexts/ChatContext.jsx` | `useGenerativeUIFunction(salesUI, "sendChatMessage", …)` sends the button's message as the customer's next turn |
| Theme | `SuperAgent/client/src/a2ui/theme.js` | `--a2ui-*` CSS variables mapped to the app's Tailwind palette (primary blue, slate text, rounded corners) |
| Secure payment form | `SuperAgent/client/src/a2ui/SecurePaymentForm.jsx` | App component in the catalog; card/ACH entry that never reaches a model (below) |

### Surface catalog

| `kind` | Built from (tool) | Shows | Buttons → message sent |
|---|---|---|---|
| `contact` | `add_new_company` (new company, no contact on file); `create_order` refused with `contact_email_required` | Name, email, phone fields (data model `/contact/*`); Save disabled until the email is valid (`email` / `required` checks) | Save → `My contact details: name …, email …, phone ….` (built with `formatString`; at order time `… Please place my order.`) |
| `serviceability` | `check_service_availability` (MCP) | Serviceable badge, address, network type, max speed, install lead time, services | Show plans · Get a quote (or Other options · Try another address) |
| `products` | `list_available_products`, `search_products_by_criteria` (MCP) | Plans table (name, technology, download, upload); internet plans filtered to the address's `available_products`; **no prices** | Quote *plan* · About *plan* |
| `products` | `compare_products` | Side-by-side table, recommendation | Quote *fastest* · Quote *other* |
| `products` | `get_product_by_id` | Description, speeds, included features | Quote *plan* · Compare plans |
| `quote` | `generate_offer_quote`, `find_best_bundle_offer`, `get_quote_details` | Items (qty, unit price, price), term, discount, monthly and yearly totals, quote id and expiry | Accept quote → `I'll take quote OFF-… (24 months). Please place my order.` · **12 / 24 / 36 months** (the other terms) → `Please re-quote OFF-… on a 36-month term.` · Add a service · Email it to me |
| `cart` | `add_to_cart`, `remove_from_cart`, `get_cart` | Items and monthly total | Place my order · Add another service |
| `order` | `create_order`, `get_order` | Order id, status badge, service, address, total, next step | — |
| `scheduling` | `check_availability` | One row per day, one button per window (earliest highlighted) | `8 AM–12 PM` → `Please book my installation for Friday, November 27, 2026, 8 AM–12 PM (morning).` |
| `scheduling` | `schedule_installation` | Confirmed badge, date, window, appointment id, address | — |
| `payment` | `get_payment_methods` (+ `order_context` total) | Amount due, saved methods, `SecurePaymentForm` | Pay with *Visa ending 1111* → `Pay for my order with my Visa ending 1111.` |
| `payment` | `process_payment` | Paid badge, amount, order, transaction, receipt email note | — |

Rules every surface follows (enforced by `SuperAgent/tests/test_a2ui.py`): components and props exist in the exported catalog with valid enum values and required props; every Button calls `sendChatMessage` with a non-empty, first-person message and no `[placeholder]` (a click sends immediately); product surfaces contain no price; failed or unknown results produce no surface; no payment token ever appears.

### Wire format

One SSE event per surface, next to the usual `token`, `activity_update`, `structured_card`, `cart_update`, `suggestions` and `done` events (additive: older clients ignore it):

```json
{
  "type": "a2ui",
  "surface_id": "check_availability-3f9a1c0b2e7d",
  "kind": "scheduling",
  "tool": "check_availability",
  "author": "service_fulfillment_agent",
  "operations": [
    {
      "version": "1.0",
      "createSurface": {
        "surfaceId": "check_availability-3f9a1c0b2e7d",
        "components": [
          {"id": "root", "component": "Card", "children": ["title-1", "caption-2", "row-5"]},
          {"id": "title-1", "component": "Title", "text": "Choose an installation time", "size": "lg"},
          {"id": "caption-2", "component": "Caption", "text": "314 Main Street, Philadelphia, PA 19103"},
          {"id": "button-3", "component": "Button", "label": "8 AM–12 PM", "variant": "primary",
           "onClick": {"functionCall": {"@call": "sendChatMessage", "args": {
             "message": "Please book my installation for Friday, November 27, 2026, 8 AM–12 PM (morning)."}}}},
          "…"
        ]
      }
    }
  ]
}
```

`surface_id` is `<tool>-<sha256(result)[:12]>`: stable for the same result, so a result repeated by the A2A transport is sent once. Surfaces carry a `dataModel` only when they have input fields (the contact card).

### Actions: how a click becomes the next turn

CopilotKit forwards `{event}` actions to a CopilotKit agent, which this app does not have. Every button therefore uses a **client function call**: `onClick: {functionCall: {"@call": "sendChatMessage", "args": {"message": …}}}`. `sendChatMessage` is declared in `salesUI` (`requiresUserActivation: true`, so only a real click can run it) and handled in `ChatContext`, which sends the message exactly as if the customer typed it. Messages are written in the customer's voice ("I'll take quote OFF-… (24 months). Please place my order."), so the router, the transcript and the evals treat clicks and typed messages the same. The message can be a literal or a renderer-side function: the contact card uses `formatString` over its data model (`${/contact/email}`).

Gateway rules that make clicks deterministic:

- **Quote selection:** when a message names an active quote of the customer (`OFF-…`) that is not the current `offer_context`, `prepare_turn` loads it (`sales_common.repositories.quotes.load_offer_context`), so accepting the 24-month card orders the 24-month quote even if a 36-month quote was generated later. The quote panel is updated too.
- **Order → scheduling:** after `create_order` succeeds the workflow hands off to `service_fulfillment_agent` in the same turn, so the slots card follows the order card without a question.
- **Contact before order:** `create_order` refuses an order without a valid email (`contact_email_required`); the contact card appears and, once discovery has saved the contact, the workflow hands off back to `order_agent` to create the order.

### Secure payment entry

Card and bank details are collected **in the card, not in the chat**, and never reach a model, an SSE event, a log or the A2UI data model:

```
SecurePaymentForm (React state only)
  → POST /api/payment-methods            gateway: session bearer, customer_id from session state, body never logged
  → POST /payment-methods                payment service REST route (payment_agent/rest.py), no LLM:
                                         tokenize_payment_method → Luhn/expiry checks → opaque tok_… token,
                                         masked method saved to customer_payment_methods
  ← {payment_type, card_brand, last_four, expiry}   (no token, no numbers)
  → chat: "I've added my Visa ending 1111. Please use it to pay for my order."
  → payment_agent: get_payment_methods → token of Visa 1111 → process_payment
```

Defense in depth: the form clears its fields after every submit; the gateway masks card numbers (Luhn-checked), CVVs and account numbers typed into chat (`[REDACTED_CARD]` …) before routing; payment tokens are stripped from SSE payloads; payment emails name the method ("Visa card ending 1111"), not its token. The payment prompt never asks for card data, which also removed Gemini safety-filter false positives on payment replies.

### Theming and layout

`salesTheme` sets the `--a2ui-*` variables (accent `#2563eb`, slate text and borders, 1rem card radius, system font), passed as `generativeUI.theme`; CopilotKit's stylesheet (`@copilotkit/react-core/v2/styles.css`) is prebuilt with Tailwind 4, so `postcss.config.js` runs the app's Tailwind 3 only on the app's own CSS. In `MessageBubble`, surfaces render under the agent's short reply; suggestion chips are hidden when the card has buttons; after a receipt, the same turn's payment-methods card is hidden and the agent's machine-readable payment JSON line is not shown.

### Fallback and configuration

| Setting | Default | Effect |
|---|---|---|
| `A2UI_ENABLED` (gateway) | `true` | `false` stops all `a2ui` events; the UI falls back to the legacy cards (`QuoteCard` from `structured_card`, and text-parsed serviceability/product/order/payment cards) |

The legacy cards are also used for any message without a surface of the same `kind`.

### Adding a surface

1. Add a builder `def _thing(data: dict, state: dict) -> Optional[_Surface]` in `api/a2ui.py` using `_Surface` helpers (`title`, `caption`, `label_value`, `buttons`, `card`) and register it in `_BUILDERS` with a `kind`. Use only catalog components; take every value from `data` or `state`; write button messages in the customer's voice with no placeholders.
2. Add the tool to the "Cards in the chat" list in `libs/sales_common/sales_common/prompts.py`, so the agent stops repeating the data in prose.
3. Add a case to `SuperAgent/tests/test_a2ui.py` (catalog validity, buttons, values) and run `pytest SuperAgent/tests -q`.
4. If you add a component or function to `salesUI`, run `npm run export:a2ui-catalog` in `SuperAgent/client` and commit `catalog.json`.
5. Check it in the browser; the console reports catalog errors (`[generativeUI] …`).

### Testing

- **Contract:** `SuperAgent/tests/test_a2ui.py` validates every surface against `catalog.json`; `test_sse.py` covers emission, de-duplication, the disable flag, MCP results, token stripping and the quote panel.
- **Payment path:** `PaymentAgent/tests/test_rest.py` (REST route) and `SuperAgent/tests/test_api.py` (proxy, chat masking).
- **Browser:** surfaces, button clicks, the contact card's validation and the secure form were verified in headless Chrome against both a mock gateway (no model calls) and the full local stack.

### Limitations

- CopilotKit's generative UI is marked experimental; versions are pinned exactly (`@copilotkit/react-core` 1.85.0, `zod` 3.25.76, `@ag-ui/client` 1.0.2, `rxjs` 7.8.1) and the catalog contract test catches renamed components.
- The provider's local agent uses `agents__unsafe_dev_only` (CopilotKit's `selfManagedAgents` belongs to a paid tier); the agent is inert and holds no secrets.
- The UI bundle grows by roughly 0.9 MB gzipped (CopilotKit, charts, maps, markdown); lazy-loading the renderer is a possible follow-up.
- Surfaces are deterministic by design; agents do not author A2UI yet. The exported catalog is ready for that (for example via `SkillGenerator` from `@a2ui/agent`).

---

## Agent Architecture

### Gateway Workflow and Agent Services

```
                        ┌───────────────────────────────┐
                        │  Gateway (SuperAgent)          │
                        │  sales_journey Workflow        │
                        │  • route_intent (router LLM)   │
                        │  • dispatch                    │
                        │  • HandoffPolicyNode           │
                        │  • sessions + memory           │
                        └───────────────┬───────────────┘
                                        │ A2A
         ┌──────────────────────────────┼──────────────────────────────┐
         │                              │                              │
┌────────▼─────────┐        ┌───────────▼────────────┐       ┌─────────▼──────────────┐
│ DISCOVERY        │        │ CONFIGURATION          │       │ TRANSACTION            │
├──────────────────┤        ├────────────────────────┤       ├────────────────────────┤
│ greeting_agent   │        │ serviceability_agent   │       │ order_agent            │
│ discovery_agent  │        │   └ MCP: serviceability│       │ payment_agent          │
│ faq_agent        │        │ product_agent          │       │ service_fulfillment_   │
│                  │        │   └ MCP: catalog + RAG │       │   agent                │
│                  │        │ offer_management_agent │       │ customer_communication_│
│                  │        │                        │       │   agent (outbox)       │
└──────────────────┘        └────────────────────────┘       └────────────────────────┘
```

### Agent Registry

| Agent (A2A name) | Directory | Port | Cluster | Tables owned | Tools / infrastructure |
|-------|---------|------|---------|----------------|----------------|
| Gateway (`sales_journey`) | `SuperAgent/` | 8000 | Orchestrator | `adk_memories`, `revoked_sessions` | ADK Runner, router LLM, React UI |
| `greeting_agent` | `GreetingAgent/` | 8209 | Discovery | — | Prompt only |
| `discovery_agent` | `DiscoveryAgent/` | 8201 | Discovery | `accounts`, `contacts`, `spend`, `opportunities`, `insights`, `actions` | PostgreSQL tools |
| `faq_agent` | `FAQAgent/` | 8210 | Discovery | — | MCP → catalog service `search_faq` (FAQ corpus RAG) |
| `serviceability_agent` | `ServiceabilityAgent/` | 8202 | Configuration | — | MCP → serviceability service (`coverage_zones`) |
| `product_agent` | `ProductAgent/` | 8203 | Configuration | — | MCP → catalog service (`products` + ChromaDB RAG) |
| `offer_management_agent` | `OfferManagement/` | 8204 | Configuration | `quotes` | PostgreSQL tools, price book |
| `order_agent` | `OrderAgent/` | 8205 | Transaction | `carts`, `cart_items`, `orders`, `order_items` | PostgreSQL tools |
| `payment_agent` | `PaymentAgent/` | 8206 | Transaction | `payments`, `payment_events`, `payment_rate_limit`, `customer_payment_methods` | Hardened payment pipeline |
| `service_fulfillment_agent` | `ServiceFulfillmentAgent/` | 8207 | Transaction | `fulfillments`, `customer_master` | Scheduling, provisioning, activation |
| `customer_communication_agent` | `CustomerCommunicationAgent/` | 8208 | Transaction | `notifications`, `dedup_cache` | Outbox dispatcher, SMTP or simulated delivery |

| Tool service | Directory | Port | Tables owned | Interfaces |
|---|---|---|---|---|
| Catalog | `services/catalog/` | 8101 | `products` | REST `/api/v1`, MCP `/mcp/` (9 tools: 8 product tools + `search_faq`), ChromaDB knowledge index |
| Serviceability | `services/serviceability/` | 8102 | `coverage_zones` | REST `/api/v1`, MCP `/mcp/` (6 tools), optional upstream GIS |

The service manifest used by all scripts is [`scripts/services.conf`](scripts/services.conf); the gateway's routing registry is `SuperAgent/super_agent/registry.py`.

### Agent Routing Priority

The router (`route_intent`) picks one agent per turn in this priority order:

| Priority | Intent Pattern | Target Agent |
|----------|---------------|--------------|
| 1 | Company/business identification | `discovery_agent` |
| 2 | Address validation, coverage check | `serviceability_agent` |
| 3 | Product catalog, specs, SLA questions (no pricing) | `product_agent` |
| 4 | Pricing, quotes, discounts | `offer_management_agent` |
| 5 | Cart, checkout, order placement | `order_agent` |
| 6 | Payment, credit check | `payment_agent` |
| 7 | Installation, scheduling, activation | `service_fulfillment_agent` |
| 8 | Send notification, show history | `customer_communication_agent` |
| 9 | Greetings ("Hi", "Hello"); pure greetings skip the router | `greeting_agent` |
| 10 | Policy, SLA, general questions; fallback for invalid router output | `faq_agent` |

---

## Agent Service Guide

This section defines how every domain agent is built, served and tested. Background decisions are in `openspec/changes/archive/2026-10-01-a2a-agent-services/design.md` and `openspec/changes/archive/2026-10-01-adk2-workflow-orchestration/design.md`.

### 1. Layout

```text
OrderAgent/
├── pyproject.toml          # name "order-agent"; depends on "sales-common" (installed first)
├── Dockerfile              # build context = repo root
├── README.md / AGENTS.md
├── order_agent/
│   ├── __init__.py         # from .agent import root_agent, build_agent
│   ├── agent.py            # build_agent(model=None) -> Agent ; root_agent = build_agent()
│   ├── prompts.py          # domain prompt (static_instruction)
│   ├── tools/              # deterministic tools (plain functions / FunctionTool)
│   └── server.py           # app = create_a2a_app(root_agent)
└── tests/
    ├── conftest.py
    └── test_*.py
```

Rules:

- **Hardcoded agent names**, e.g. `order_agent`. The gateway routes by these names and the UI displays them.
- **No `load_dotenv()` in agent code.** Containers get env from compose or Cloud Run.
- **No `importlib` isolation, no `sys.modules[...]` lookups, and no imports of another agent's package.**
- **`GEMINI_MODEL` has no default.** `sales_common.config.model_name()` raises when it is unset. Agents use `sales_common.models.agent_model()` (that model, retried once when Gemini returns an empty reply); tests pass a scripted model instead.
- **Tools return JSON-serializable dicts** with explicit field names. Deterministic logic only; no LLM calls inside tools.
- **Do not swallow `BaseException` in tools.** ADK 2.x uses exceptions for retries and interrupts. Catch specific exceptions and return `{"success": false, "error": ...}`.

### 2. `agent.py` template

```python
from typing import Optional
from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.models import agent_model
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import ORDER_AGENT_INSTRUCTION, ORDER_SHORT_DESCRIPTION
from .tools.cart_tools import add_to_cart, ...


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    return Agent(
        name="order_agent",
        model=model or agent_model(),                  # Gemini + one retry on empty replies
        description=ORDER_SHORT_DESCRIPTION,
        static_instruction=ORDER_AGENT_INSTRUCTION,   # long, cacheable, NOT templated
        instruction=JOURNEY_CONTEXT_INSTRUCTION,       # short, templated from state
        tools=[add_to_cart, ...],
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        generate_content_config=generate_config(temperature=0.0, max_output_tokens=2048),
    )


root_agent = build_agent()
```

Callbacks accept lists. Agent-specific callbacks are appended after the shared ones. For `after_tool_callback`, the first callback that returns a truthy value wins, so an agent-specific callback that rewrites the response must merge `_context_update` itself or run first.

### 3. `server.py`

```python
from sales_common.a2a_server import create_a2a_app
from .agent import root_agent

app = create_a2a_app(root_agent)   # uses_database=False for agents without DB tools
```

Run with `uvicorn order_agent.server:app --host 0.0.0.0 --port $PORT`.

- `create_a2a_app` builds an ADK `App` with context compaction and context caching, `DatabaseSessionService` sessions, an a2a-sdk `DatabaseTaskStore`, and `GET /healthz`. It also initializes tracing (`sales_common.telemetry`, a no-op without Langfuse keys) and extracts incoming trace headers, so the agent's spans join the gateway's trace.
- The agent card is served at `/.well-known/agent-card.json` and advertises `PUBLIC_URL`.

### 4. Journey context (state across A2A)

- The gateway forwards `customer_context`, `serviceability_context`, `offer_context`, `order_context`, `payment_context`, a recent transcript, and the user profile in A2A request metadata.
- `import_forwarded_context` copies them into the agent's session state before it runs. Tools keep reading `tool_context.state["order_context"]`, and the templated `JOURNEY_CONTEXT_INSTRUCTION` shows them to the model.
- When a tool writes one of those keys (`tool_context.state["offer_context"] = {...}`), `export_context_delta` adds `_context_update` to the tool response. The gateway merges it into its session state.

### 5. Database access (PostgreSQL)

```python
from sales_common import db, notifications
from sales_common.repositories.quotes import mark_ordered

with db.transaction() as conn:                       # commit on success, rollback on error
    conn.execute("INSERT INTO orders (...) VALUES (%s, %s)", (a, b))
    row = conn.execute("SELECT * FROM orders WHERE order_id = %s", (oid,)).fetchone()  # dict row
    mark_ordered(offer_id, conn=conn)
    notifications.enqueue("order_confirmation", recipient_email=email, order_id=oid,
                          customer_id=cid, args={...template args...}, conn=conn)
```

SQL conventions: psycopg 3 placeholders `%s` / `%(name)s`, upserts with `INSERT ... ON CONFLICT ...`, generated ids via `RETURNING`, rows are dicts, timestamps are ISO text (`db.now_iso()`).

- **Quoting:** the `accounts` table uses quoted, case-sensitive columns `"Company Name"`, `"Industry"`, `"Street"`, `"City"`, `"State"`, `"Website"`, `"Existing Customer"`, and so on. Always double-quote them in SQL; unquoted `Street` folds to `street` and fails.
- **Schema:** lives in `db/migrations/*.sql`. Agents never create tables at runtime.
- **No fallbacks:** there are no silent in-memory fallbacks. If `DATABASE_URL` is unset, `sales_common.db` raises.

### 6. Notifications (outbox)

- Producers never call the communication agent. They call `sales_common.notifications.enqueue(...)` inside their business transaction.
- Supported types are in `sales_common.notifications.NOTIFICATION_TYPES`.
- `args` must contain everything the communication service needs to render the message (ids, names, amounts, dates).

### 7. Prompts

- Prompts never tell the model to `transfer_to_agent` or hand off to a named peer agent. Agents cannot transfer; the gateway workflow routes each user turn and runs the deterministic handoffs (Discovery→Serviceability, Scheduling→Payment).
- Keep output formats stable. The UI parses some of them, such as the order and payment JSON blocks and the serviceability key:value lines.

### 8. Tests

`tests/conftest.py`:

```python
import os
os.environ.setdefault("GEMINI_MODEL", "gemini-test")      # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
```

- Tool tests run against a scratch PostgreSQL database (`TEST_DATABASE_URL`) after `sales_common.migrate.run(seed=True)`. Skip them when `TEST_DATABASE_URL` is unset.
- Agent tests use `sales_common.testing.ScriptLlm` (scripted function calls and text) with an ADK `Runner` and an `InMemorySessionService`. No API key is needed.
- Run with `pytest <AgentDir>/tests -q`.

#### Golden evals

Every agent also has a golden set in `evals/golden/agents/<agent_name>/` (real Gemini, ADK `EvalSet`): user turns, the expected tool calls with their stable arguments, a reference response and rubrics, scored for trajectory and response by `scripts/eval.sh --only <agent>`. A new agent adds:

1. its package to `AGENT_PACKAGES` in `evals/golden_io.py` and its tools to `evals/golden/tool_schemas.json` (`python -m evals.record_golden --snapshot-tools`);
2. `<agent_name>.evalset.json` + `test_config.json` (copy another agent's config) and MANIFEST entries, from its Scenarios.md cases;
3. recorded and reviewed reference responses (`python -m evals.record_golden`, `python -m evals.review`).

See [evals/README.md](evals/README.md) and [Evals: Measuring Agent Quality](#evals-measuring-agent-quality).

### 9. Dockerfile template

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8080
WORKDIR /app
COPY libs/sales_common /app/libs/sales_common
RUN pip install /app/libs/sales_common
COPY OrderAgent /app/OrderAgent
RUN pip install /app/OrderAgent
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn order_agent.server:app --host 0.0.0.0 --port ${PORT}"]
```

### 10. Environment variables (all agent services)

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_MODEL` | yes | e.g. `gemini-3-flash-preview` |
| `GOOGLE_API_KEY` | yes (or Vertex AI env) | secret |
| `DATABASE_URL` | yes | `postgresql://user:pw@host:5432/db`; sessions derive `postgresql+asyncpg://` (override `SESSION_DB_URL`) |
| `PUBLIC_URL` | yes | URL other services use to reach this agent (agent card) |
| `SERVICE_AUTH` | no | `none` (default) or `gcp_id_token` |
| `LOG_LEVEL` | no | default `INFO` |
| `MODEL_REQUEST_TIMEOUT_MS` | no | per-request Gemini timeout, default `120000` |
| `CATALOG_MCP_URL` / `SERVICEABILITY_MCP_URL` | for MCP agents | tool service MCP endpoint (product and faq → catalog; serviceability → serviceability); set by the scripts and compose |
| `COMPACTION_*`, `CONTEXT_CACHE_*` | no | see `sales_common.config.ContextSettings` |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`, `LANGFUSE_TRACING_ENVIRONMENT`, `LANGFUSE_CAPTURE_CONTENT`, `TELEMETRY_FLUSH_PER_REQUEST` | no | tracing to Langfuse (off without keys); `create_a2a_app` wires it, no agent code needed. See [Agent Observability](#agent-observability-langfuse) |

---

## Database Architecture (PostgreSQL)

All services share **one PostgreSQL 16 database** (a `postgres:16` container or your own server locally, Cloud SQL in GCP).

- **Schema** is managed only by versioned SQL migrations in `db/migrations/` (`001_sales_schema.sql` 19 sales tables, `002_catalog.sql` `products`, `003_platform.sql` `adk_memories` + `revoked_sessions`, `004_coverage.sql` `coverage_zones`, `005_notifications_seq.sql` outbox insertion order). Services never create business tables at runtime.
- **Seed data** in `db/seed/` (165 demo accounts with contacts, quotes, orders and fulfillments; 16 SKUs; 38 coverage ZIPs) is applied once per database.
- **Apply** with `scripts/db.sh migrate | seed | reset --yes` or `python -m sales_common.migrate [--seed]`. Applied files are tracked in `schema_migrations` / `seed_versions`.
- **Library-managed tables:** ADK session tables (`sessions`, `events`, `app_states`, `user_states`) are created by `DatabaseSessionService`, and `a2a_tasks` by the a2a-sdk `DatabaseTaskStore`.
- **Access:** agent tools use `sales_common.db` (psycopg 3 connection pool, dict rows, `transaction()`); ADK sessions and tasks use SQLAlchemy + asyncpg.

```
┌───────────────────────────────────────────────────────────────────────────┐
│           PostgreSQL 16  (one database, table ownership per service)      │
├──────────────┬───────────┬───────────┬──────────┬──────────┬──────────────┤
│  DISCOVERY   │   OFFER   │   ORDER   │ PAYMENT  │ FULFILL  │    COMMS     │
│ accounts     │ quotes    │ carts     │ payments │fulfill-  │ notifications│
│ contacts     │           │ cart_items│ payment_ │ ments    │  (outbox)    │
│ spend        │           │ orders    │  events  │customer_ │ dedup_cache  │
│ opportunities│           │ order_    │ payment_ │ master   │              │
│ insights     │           │  items    │ rate_... │          │              │
│ actions      │           │           │ customer_│          │              │
│              │           │           │ payment_ │          │              │
│              │           │           │ methods  │          │              │
├──────────────┴───────────┴───────────┴──────────┴──────────┴──────────────┤
│ TOOL SERVICES   products (catalog) · coverage_zones (serviceability)      │
│ PLATFORM        adk_memories · revoked_sessions · ADK sessions · a2a_tasks│
└───────────────────────────────────────────────────────────────────────────┘
```

Table ownership (the single writer per table, and the remaining cross-domain writers) is documented in [db/README.md](db/README.md).

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
        text status "initiated/processing/completed/failed"
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
        text status "pending/sent/simulated/failed"
        text channels_json
        text metadata_json "template + args"
    }

    dedup_cache {
        text dedup_key PK
        text sent_at
    }
```

### How Entities Are Updated Along the Sales Conversation

Each row is a user turn that triggers one or more agent actions:

| Stage | Conversation Trigger | Agent / service | Tables Written | Operation |
|-------|---------------------|-------|---------------|-----------|
| **1. Greeting** | "Hi, I need internet for my office" | `greeting_agent` | — | No DB writes. Returns the phone script. |
| **2. Discovery** | "We're VoiceStream Networks at 123 Main St, Boston" | `discovery_agent` | `accounts` | **INSERT** company with address, zip code, `customer_id`; publishes `customer_context`. |
| | *(agent asks for contact info)* | `discovery_agent` | `contacts` | **INSERT** contact with name, title, email, phone. |
| | *(agent runs BANT qualification)* | `discovery_agent` | `opportunities`, `insights` | **INSERT** opportunity with BANT scores; buying signals and pain points. |
| **3. Serviceability** | *(same turn, deterministic handoff)* or "Check coverage" | `serviceability_agent` → serviceability service | — | No writes. Reads `coverage_zones` through MCP; publishes `serviceability_context`. |
| **4. Product** | "Show me Fiber 5G specs" | `product_agent` → catalog service | — | No writes. Reads `products` through MCP; `search_product_knowledge` queries the ChromaDB index. |
| **5. Quote** | "Give me pricing for Fiber 5G + SD-WAN" | `offer_management_agent` | `quotes`, `notifications` | **INSERT** quote (offer_id, items, discounts, totals; status `active`, 30-day expiry); outbox row for the quote confirmation. |
| **6. Order** | "Proceed with this quote" | `order_agent` | `carts`, `cart_items`, `orders`, `order_items`, `quotes`, `notifications` | **INSERT** cart and order (status `pending_payment`, 48h expiry). **UPDATE** `quotes.status` → `ordered` via `sales_common.repositories.quotes`. Outbox row for the order confirmation. |
| **7. Scheduling** | "Schedule installation" | `service_fulfillment_agent` | `fulfillments`, `notifications` | **INSERT** fulfillment with appointment (status `scheduled`); the workflow then hands off to payment in the same turn. |
| **8. Payment** | *(same turn, deterministic handoff)* then card details | `payment_agent` | `payments`, `payment_events`, `orders`, `notifications` | **INSERT** payment + audit events; **UPDATE** `orders.status` → `paid`; outbox row for the payment receipt. |
| **9. Dispatch / install** | "Simulate install day" | `service_fulfillment_agent` | `fulfillments` | **UPDATE** dispatch id, status → `dispatched` → `installed`. |
| **10. Activation** | "Activate service" | `service_fulfillment_agent` | `fulfillments`, `customer_master`, `accounts`, `orders`, `notifications` | **UPDATE** fulfillment (circuit_id, account_id, `activated`); **INSERT** `customer_master`; **UPDATE** `accounts."Existing Customer"` → `Y` and `orders.status` → `fulfilled`. |
| **Cross-cutting** | *(continuous)* | customer communication dispatcher | `notifications`, `dedup_cache` | Picks `pending` outbox rows (`FOR UPDATE SKIP LOCKED`), renders them, sends via SMTP or simulation, marks `sent` / `simulated` / `failed`, records dedup keys. |
| **Maintenance** | *(startup + hourly)* | gateway (`sales_common.maintenance`) | `quotes`, `carts`, `orders`, `notifications` | Expires stale quotes and carts, cancels timed-out `pending_payment` orders, escalates stuck paid orders, enqueues abandoned-cart / order-cancelled notifications. |

### Entity Lifecycle State Machines

```
Quote:      active ──→ ordered ──→ (done)
                 └──→ expired (TTL: 30 days)

Cart:       active ──→ (consumed by order)
                 └──→ expired (TTL: 24 hours)

Order:      draft ──→ pending_payment ──→ paid ──→ fulfilled
                           │               └──→ escalated (paid, stuck >7 days)
                           └──→ cancelled (pending_payment TTL: 48h)

Payment:    initiated ──→ processing ──→ completed
                                   └──→ failed

Notification (outbox): pending ──→ sent | simulated | failed

Fulfillment: scheduled ──→ dispatched ──→ installed ──→ activated

Account:    Existing_Customer=N ──→ Existing_Customer=Y (on activation)
```


### Table-to-Service Access Matrix

| Table | Discovery | Offer | Order | Payment | Fulfillment | Comms | Catalog svc | Serviceability svc | Gateway |
|-------|:---------:|:-----:|:-----:|:-------:|:-----------:|:-----:|:-----------:|:------------------:|:-------:|
| **accounts** | R/W | — | — | — | R/W | — | — | — | R |
| **contacts** | R/W | — | — | — | — | — | — | — | R |
| **spend**, **actions** | R | — | — | — | — | — | — | — | — |
| **opportunities**, **insights** | R/W | — | — | — | — | — | — | — | — |
| **quotes** | — | R/W | W | — | — | — | — | — | W |
| **carts**, **cart_items** | — | — | R/W | — | — | — | — | — | W |
| **orders** | — | — | R/W | R/W | R/W | — | — | — | R/W |
| **order_items** | — | — | R/W | — | R | — | — | — | — |
| **payments** + payment tables | — | — | — | R/W | — | — | — | — | — |
| **fulfillments** | — | — | — | — | R/W | — | — | — | — |
| **customer_master** | R | — | — | — | W | — | — | — | — |
| **notifications** (outbox) | — | W | W | W | W | R/W | — | — | W |
| **dedup_cache** | — | — | — | — | — | R/W | — | — | — |
| **products** | — | — | — | — | — | — | R | — | — |
| **coverage_zones** | — | — | — | — | — | — | — | R | — |
| **adk_memories**, **revoked_sessions** | — | — | — | — | — | — | — | — | R/W |

> **R** = SELECT, **W** = INSERT/UPDATE. **Gateway** includes the hourly `cleanup_stale_records()` maintenance. Every agent service and the gateway also use the library-managed ADK session and `a2a_tasks` tables. The cross-domain writers (e.g. Payment and Fulfillment updating `orders`) are intentional; moving them behind single-writer services (`mcp-remaining-domains`) was decided against.

### PaymentAgent Hardening

The PaymentAgent is a **deterministic, defense-in-depth payment workflow** rather than a simple "charge card" wrapper:

- **Idempotency keys** on `process_payment()` so client retries return the original result instead of creating duplicate charges.
- **Duplicate-payment protection** that checks whether an order already has a completed payment before inserting a new one.
- A **payment state machine** with explicit transitions (`initiated → processing → completed/failed`).
- **Per-customer rate limiting** for payment attempts (`payment_rate_limit`).
- **Velocity-aware approval checks** that simulate transaction-count and cumulative-spend controls.
- An **append-only `payment_events` audit trail** for every status transition.
- **Opaque random tokens and transaction identifiers** (`tok_` + `secrets.token_urlsafe`), never derived from card data. Saved payment methods are stored masked (brand, last four, expiry) in `customer_payment_methods`; full card numbers and CVV are never stored or logged.
- **Order-status guard:** only orders in `pending_payment` or `draft` can be charged; cancelled, expired, paid or fulfilled orders are refused without a charge, payment row or notification.
- **CVV discard** after validation; sensitive verification data is never stored.
- **Order-linked persistence** in PostgreSQL, with `orders.status` updated to `paid` only after successful completion, in the same transaction as the payment-receipt outbox row.
- **Journey-state propagation:** `payment_context` is written to state and returned to the gateway as `_context_update`, so downstream steps never re-infer payment results from conversation text.
- **Secure payment form:** customers enter card or bank details in the A2UI payment card; the gateway forwards them (with the session's `customer_id`) to the payment service's model-free `POST /payment-methods`, so card data never enters a prompt, a chat message or a trace. The agent only sees "Visa ending 1111" and charges the saved token. Payment emails name the masked method, never the token.

---

## Example Conversation Flows

### Discovery → Serviceability (zero-click handoff)

```
User: "We're Crane.io at 123 Main St, Philadelphia PA 19103"
  ↓ route_intent → discovery_agent (A2A)
  ↓ Discovery registers the company; customer_context returns as _context_update
  ↓ ContextBridgePlugin merges it into the gateway session
  ↓ HandoffPolicyNode: customer has a zip code, no serviceability check yet
  ↓ serviceability_agent receives "Check service availability for this address: {JSON}"
  ↓ serviceability service (MCP) → "✅ Serviceable with Fiber 1G/5G/10G"
  (Same turn: no user message needed between Discovery and Serviceability)
```

### Guided checkout with A2UI cards (quote → order → installation → payment)

Each line marked 🖱 is a card button; the customer can finish the purchase without typing.

```
User: "We're Juicer Inc at 314 Main Street, Philadelphia PA 19103 and need business internet."
  ↓ discovery_agent registers the company            → 🃏 contact card (name, email, phone)
  ↓ handoff → serviceability_agent (same turn)       → 🃏 "Service is available" (FTTP, 5,000 Mbps)
🖱 Save contact details   → discovery saves the contact → customer_context.contact.email
🖱 Show plans             → product_agent              → 🃏 plans at this address (no prices)
🖱 Quote Business Fiber 1 Gbps → offer_management_agent → 🃏 quote (12 months)
🖱 36 months              → "Please re-quote OFF-… on a 36-month term." → 🃏 quote (36 months, 10% off)
🖱 Accept quote           → prepare_turn selects that quote → order_agent
  ↓ create_order (email from customer_context.contact) → 🃏 order created
  ↓ handoff → service_fulfillment_agent (same turn) → check_availability → 🃏 installation times
🖱 Fri, Nov 27 · 8 AM–12 PM → schedule_installation  → 🃏 installation scheduled
  ↓ handoff → payment_agent (same turn) → get_payment_methods → 🃏 payment (amount, saved methods, secure form)
🖱 Save and pay $224.10   → secure form → POST /api/payment-methods (tokenized, no LLM)
  ↓ "I've added my Visa ending 1111. Please use it to pay for my order." → process_payment → 🃏 payment received
```

Without A2UI (`A2UI_ENABLED=false`) the same journey works by typing, with the legacy cards.

---

## 🗃️ RAG / ChromaDB Knowledge Base

Product data and product knowledge live in the **catalog service** (`services/catalog/`), not in the product agent. The product agent reaches both through MCP:

| Data Source | MCP tools | When Used |
|-------------|-------|-----------|
| **`products` table** (PostgreSQL, 16 SKUs) | `get_product_by_id`, `list_available_products`, `compare_products`, `search_products_by_criteria`, `suggest_alternatives`, `get_best_value_product`, `get_product_categories` | Product lookups, comparisons, filtering by speed/category |
| **ChromaDB vector store** (RAG) | `search_product_knowledge` | Documentation-level questions: SLA specifics, installation requirements, codec details, use-case fit |
| **ChromaDB FAQ collection** (RAG, used by `faq_agent`) | `search_faq` | Policy and general questions; the FAQ agent answers only from retrieved passages |

> **Key nuance:** "Compare Fiber 1G vs 5G" reads the **catalog table**, not RAG. RAG is used only when the question needs documentation-level depth (e.g., "What codec does Business Voice use?"). Prices are never returned by the catalog service; they come only from the offer management agent.

### How RAG Works

```
User question
  → product_agent calls search_product_knowledge (MCP → catalog service)
  → query encoded to a 384-dim vector (sentence-transformers all-MiniLM-L6-v2)
  → ChromaDB similarity search → top_k passages (default 4)
  → structured passages {text, doc_file, section, product_ids, distance}
  → agent composes a grounded answer
```

- **Sources:** `services/catalog/data/product_docs/*.md` (fiber, coax, voice, SD-WAN, mobile) for `search_product_knowledge`, and `services/catalog/data/faq_docs/*.md` (billing and payments, cancellation and changes, contracts and terms, installation, service levels, support) for `search_faq`, the FAQ agent's only source. One shared embedder serves both collections.
- **Index:** `CHROMA_PATH` (default `services/catalog/data/embeddings`, gitignored). Build it with `python services/catalog/scripts/ingest_knowledge.py`, or let the service build it in the background on first start (`RAG_BUILD_ON_START=true`).
- **Docker / Cloud Run:** the catalog image installs CPU-only PyTorch, pre-stages the embedding model at `EMBEDDING_MODEL_PATH` and builds the index at image build time; at runtime it works offline.
- **Degraded mode:** when the model or index is unavailable, `search_product_knowledge` / `search_faq` return `available: false` and the rest of the catalog keeps working.

Details: [services/catalog/README.md](services/catalog/README.md).

---

## Sales Conversation Flow

Typical end-to-end flow:

1. **Discovery** — collect business/location context and the contact (name, email: required before ordering)
2. **Serviceability** — verify address + infrastructure (automatic after discovery)
3. **Product** — recommend technically compatible products
4. **Offer Management** — compute quote JSON (pricing + discounts + totals)
5. **Order** — cart/checkout and contract creation (needs the contact email)
6. **Fulfillment** — installation times shown automatically after the order; one click books
7. **Payment** — secure form or saved method, then authorization (automatic after scheduling)
8. **Activation** — install day, activation, `customer_master`
9. **Customer Comms** — confirmations and reminders via the notification outbox

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite 6 + Tailwind CSS 3 |
| Generative UI | A2UI 1.0 (surfaces built by the gateway) rendered with CopilotKit `@copilotkit/react-core` 1.85 (`v2/generative-ui`: `standardUI`, `GenerativeUISurface`, `useGenerativeUIFunction`) |
| Gateway / services | FastAPI / Starlette, Python 3.12 |
| Agent Framework | Google ADK 2.10.0 (`google-adk[a2a,mcp,db]`): `Workflow`, `App`, `DatabaseSessionService`, `RemoteA2aAgent`, `to_a2a`, `McpToolset` |
| Agent protocol | A2A (a2a-sdk 1.x) with agent cards and a PostgreSQL task store |
| Tool protocol | MCP (`mcp` 2.x `MCPServer`, streamable HTTP) |
| LLM | Gemini (configured via `GEMINI_MODEL`, e.g. `gemini-3-flash-preview`) |
| Streaming | Server-Sent Events (SSE): text, activity, cart and `a2ui` events |
| Database | PostgreSQL 16 (psycopg 3, SQLAlchemy 2.1 + asyncpg), versioned SQL migrations |
| RAG | ChromaDB + sentence-transformers (catalog service) |
| Observability | OpenTelemetry (OTLP/HTTP) + OpenInference ADK instrumentation → Langfuse Cloud (traces, sessions, scores, datasets) |
| Deployment | Docker Compose locally; Cloud Run + Cloud SQL + Secret Manager on GCP |

---

## Repository Layout

```
ConversationalSalesAgent/
├── AGENTS.md / CLAUDE.md            # Architecture, standards, assistant instructions
├── README.md / Scenarios.md         # Overview and test scenarios
├── GCP_DEPLOY.md                    # Multi-service Cloud Run deployment guide
├── .env.example                     # Shared environment template (copied to .env)
├── docker-compose.yml               # Full local stack in containers
├── openspec/                        # BASELINE.md (system map), specs/ (behavior), changes/ (proposals + archive)
├── docs/                            # Presentation decks, architecture brief, issue write-ups
├── libs/sales_common/               # Shared runtime library (config, db, A2A, MCP, memory, outbox, telemetry)
├── db/                              # migrations/ + seed/ (PostgreSQL), README with table ownership
├── scripts/                         # services.conf + setup/start/stop/db/deploy/eval scripts, e2e_test.py
├── evals/                           # Golden datasets (ADK EvalSet) + eval runners (agents, router, journeys)
├── services/
│   ├── catalog/                     # Product catalog REST + MCP + RAG (port 8101)
│   └── serviceability/              # Address + coverage REST + MCP (port 8102)
├── SuperAgent/                      # Gateway (port 8000)
│   ├── super_agent/                 #   sales_journey workflow, registry, router prompt, plugins
│   ├── server/                      #   FastAPI app: session, chat (SSE), feedback, payment-methods, debug endpoints
│   │   ├── api/a2ui.py              #     A2UI surface builders (one per tool result kind)
│   │   └── a2ui/catalog.json        #     exported A2UI 1.0 catalog (contract for the builders)
│   ├── client/                      #   React UI
│   │   ├── src/a2ui/                #     salesUI (standard catalog + SecurePaymentForm), theme, provider
│   │   └── src/components/A2UISurface.jsx  # renders a surface inside a chat message
│   └── tests/
├── DiscoveryAgent/                  # A2A agent services (ports 8201-8210), each with
├── ServiceabilityAgent/             #   <pkg>/agent.py, prompts.py, tools/, server.py,
├── ProductAgent/                    #   tests/, Dockerfile, AGENTS.md, README.md
├── OfferManagement/
├── OrderAgent/
├── PaymentAgent/
├── ServiceFulfillmentAgent/
├── CustomerCommunicationAgent/
├── GreetingAgent/
├── FAQAgent/
├── tests/                           # Cross-cutting tests: integration/ (multi-process, scripted model), baseline doc check
└── .certs/                          # (gitignored, optional) local CA bundle for TLS-intercepting proxies
```

---

## Getting Started (Local)

### Prerequisites

- Python 3.12 (3.11+ works for development)
- Node.js 20 (for the React UI)
- PostgreSQL 16, either your own server or Docker (`docker compose`)
- A Gemini API key

### Option A: Native processes (recommended for development)

```bash
# 1. One-time setup: venv, editable installs of libs/sales_common and every service,
#    client npm ci, and .env copied from .env.example (only if .env does not exist)
scripts/setup_local.sh

# 2. Edit .env: GOOGLE_API_KEY, GEMINI_MODEL, DATABASE_URL (default postgresql://csa:csa@localhost:5432/csa)
#    and optionally SESSION_SECRET_KEY (an ephemeral one is generated if empty)

# 3. Local PostgreSQL 16 for DATABASE_URL, then migrations + seed (details below)
scripts/db.sh up

# 4. Start everything: migrations + seed, 2 tool services, 10 agents, gateway, Vite UI
scripts/start_local.sh
```

`scripts/db.sh up` decides how PostgreSQL runs, in this order:

1. `DATABASE_URL` already accepts connections: it is used as is (your own server, a shared dev database, a previous `up`).
2. Docker is installed: the engine must be running. If Rancher Desktop / Docker Desktop is closed, `up` stops and tells you which app to start (`open -a "Rancher Desktop"`); if the app is still booting it waits up to 2 minutes. It then runs container `csa-postgres` (image `postgres:16`, volume `csa-pgdata`, bound to `127.0.0.1`).
3. The `postgres:16` image cannot be pulled (typically a corporate proxy that the Docker VM does not use), or Docker is not installed: it falls back to Homebrew `postgresql@16` (`brew services`), creating the role and database from `DATABASE_URL`.

`scripts/db.sh up --native` skips Docker; `scripts/db.sh down` stops whichever one is running (data is kept). `start_local.sh` refuses to start when the database is unreachable and points to `db.sh up`.

> **Behind a corporate proxy?** Docker Desktop and Rancher Desktop run the engine in a VM that does not use the Mac's proxy auto-config, so pulls from Docker Hub can time out even though the browser works. Either configure the proxy in the engine's settings, or let `db.sh up` fall back to Homebrew.
>
> **Rancher Desktop never becomes ready?** If its log says `The k3s cache is empty and there is no network connection`, Kubernetes is enabled and k3s cannot be downloaded through the proxy. This project needs only Docker: `rdctl start --kubernetes.enabled=false --container-engine.name=moby`. If `docker info` still fails, the CLI may point at another engine's socket: `docker context use rancher-desktop` (or `export DOCKER_HOST=unix://$HOME/.rd/docker.sock`).

- UI: `http://localhost:3000` (Vite proxies `/api` to the gateway)
- Gateway health: `http://localhost:8000/health`
- Agent cards: `http://localhost:8201/.well-known/agent-card.json` … `:8210`
- Tool services: `http://localhost:8101/docs`, `http://localhost:8102/docs`

Useful flags: `scripts/start_local.sh --only catalog,product,gateway`, `--no-ui`, `--skip-migrate`.

> The `postgres` service in `docker-compose.yml` is not published on the host, so native processes use the database from `scripts/db.sh up` (as above).

### Option B: Everything in containers

```bash
cp .env.example .env      # set GOOGLE_API_KEY, GEMINI_MODEL, POSTGRES_PASSWORD
docker compose up --build
```

Starts PostgreSQL 16, a one-shot `db-init` (migrations + seed), both tool services, all 10 agents and the gateway on a private network. Only the gateway is published: `http://localhost:8000` serves the built UI and the API.

### Observability (Langfuse)

Optional tracing of every turn to Langfuse: put `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL` in `.env` and restart. See [Agent Observability (Langfuse)](#agent-observability-langfuse) for what you get, how it works and what to look for in the dashboard.

### Logs and Stopping

```bash
tail -f logs/gateway.log logs/discovery.log logs/serviceability-agent.log   # native processes
scripts/stop_local.sh                     # stops only the PIDs recorded in logs/pids/
scripts/stop_local.sh --only order,ui     # stop selected services
docker compose down                       # containers
```

### Database Operations

```bash
scripts/db.sh up                 # start local PostgreSQL 16 (Docker, Homebrew fallback) + migrate + seed
scripts/db.sh down               # stop it (data kept)
scripts/db.sh migrate            # apply pending migrations
scripts/db.sh seed               # migrations + seed files (each applied once)
scripts/db.sh reset --yes        # drop and recreate the schema, then migrate + seed (local hosts only)
```

### Tests

```bash
pytest OrderAgent/tests -q                                   # any agent or service
TEST_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_test pytest SuperAgent/tests -q
TEST_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_test venv/bin/python -m pytest tests/integration -q -s
python scripts/e2e_test.py --base-url http://127.0.0.1:8000  # against a running stack (real Gemini)
```

DB-backed tests are skipped when `TEST_DATABASE_URL` is unset; use a scratch database. Agent tests use a scripted model and need no API key.

#### Test structure

Tests live **next to the code they test**. Each package (the shared library, every agent, each tool service, the gateway) has its own `tests/` folder. The root `tests/` folder holds only tests that span several services.

| Where | What it tests | Model | Needs | Run |
|---|---|---|---|---|
| `libs/sales_common/tests/` | Shared library: config, DB helpers, migrations, journey context, A2A/MCP factories, model wrapper, tracing (masking, filters, A2A/MCP trace propagation, ADK instrumentation) | none | DB for some tests | `pytest libs/sales_common/tests -q` |
| `<Agent>/tests/` (e.g. `OrderAgent/tests/`) | One agent: its tools against PostgreSQL, and its behavior with a scripted model (`sales_common.testing.ScriptLlm`) | scripted | DB for tool tests | `pytest OrderAgent/tests -q` |
| `services/catalog/tests/`, `services/serviceability/tests/` | One tool service: REST API, MCP tools, RAG indexes | none | DB; the embedding model for some RAG tests | `pytest services/catalog/tests -q` |
| `SuperAgent/tests/` | Gateway: routing workflow with in-process fake agents, handoff rules, SSE mapping, auth, API, `chat_turn` tracing and `/api/feedback` | scripted | DB for some tests | `pytest SuperAgent/tests -q` |
| `tests/integration/` | **Cross-service:** all 13 services as real processes over A2A, MCP and PostgreSQL | scripted (`fake-sales`) | DB | `pytest tests/integration -q -s` |
| `tests/test_baseline_doc.py` | **Repo-wide:** `openspec/BASELINE.md` lists every service, port and agent tool | none | nothing | `pytest tests/test_baseline_doc.py -q` |
| `evals/` | Real-model quality against golden datasets; `test_golden_valid.py` / `test_metrics.py` also run offline | **real Gemini** (live tests) | billed key, DB | `scripts/eval.sh` (offline checks: `pytest evals -q`) |
| `scripts/e2e_test.py` | Live smoke test of a running stack | real Gemini | running stack | `python scripts/e2e_test.py` |

Why unit tests sit inside each package rather than under the root `tests/`:

- **Self-contained services.** Each agent and service is installed, built and deployed on its own, and its tests travel with it. Its `conftest.py` sets that package's environment defaults and scratch-database setup.
- **One pattern for all 14 packages** (documented in [Agent Service Guide](#agent-service-guide)), so a new agent starts with a ready `tests/` folder.
- **Clear meaning for the root `tests/`:** a test there needs the whole system, or checks the repository as a whole.

DB-backed tests use the scratch database in `TEST_DATABASE_URL`, never your dev database. Run every suite before committing; after prompt, model, tool or routing changes, also run the golden evals.

### Evals

Golden-dataset evals run the real model and score agent behavior. See [Evals: Measuring Agent Quality](#evals-measuring-agent-quality) below.

---

## Evals: Measuring Agent Quality

### What evals are (and why tests are not enough)

The **tests** in this repo check the plumbing. They replace Gemini with a scripted model, so they prove that tools return the right JSON, A2A and MCP calls work, and the gateway streams events. They never check what the real model *decides* to do.

**Evals** run the real model and grade its behavior against **golden datasets**: hand-reviewed example conversations that record what a correct answer looks like. They answer different questions:

| Question | Checked by |
|---|---|
| Does `add_new_company` write the right row? | unit tests (scripted model) |
| Does the gateway stream SSE events correctly? | gateway and integration tests |
| Given "We're Acme at 10 Elm St, Boston", does the discovery agent search, then register the company, with the right arguments? | **evals** |
| Does the FAQ agent quote only real policy, never invented ones? | **evals** |
| Does the router send "how much for Fiber 5G?" to the pricing agent? | **evals** |

Evals catch the problems tests cannot. The first eval run found eight real defects, all now fixed:
- The router's JSON was cut off by Gemini 3 thinking tokens.
- The FAQ agent invented policies.
- The product agent compared itself with competitors.
- Fulfilled orders could be cancelled.
- Payment history returned fake data.
- Agents did not know today's date.
- Discovery stalled on a suite-number question.
- The router misrouted company introductions.

### Golden datasets

Goldens live in `evals/golden/` in Google ADK's `EvalSet` format:

```
evals/golden/
  agents/<agent>/<agent>.evalset.json   52 cases across all 10 agents (+ test_config.json: metrics, thresholds)
  router/router.evalset.json            58 routing cases (input → expected agent)
  journeys/<scenario>.evalset.json      5 multi-turn end-to-end conversations
  MANIFEST.json                         review status per case, Scenarios.md ids, seed-data hashes
  tool_schemas.json                     snapshot of every agent's tool parameters
```

Each golden turn records three things:
- the user message
- the **expected trajectory**: which agent answers and which tools it calls, in order, with the arguments that matter (for example `check_service_availability(zip_code="19103")`)
- a **reference reply**, plus **rubrics**: plain-language checks such as "It does not state any price"

Cases come from [Scenarios.md](Scenarios.md) and use seed data (real customer ids, orders, ZIP codes), so expected arguments are exact.

### What gets scored

Every eval scores **both the trajectory (what the agent did) and the response (what it said)**:

| Tier | What runs | Trajectory | Response |
|---|---|---|---|
| **Agents** (52 cases) | each agent in-process with ADK's `AgentEvaluator` | `golden_trajectory_v1`: expected tool calls appear in order with matching arguments | `final_response_match_v2` (LLM judge: same meaning as the reference?), rubric quality (each rubric pass/fail), `hallucinations_v1` (every claim supported by tool output?) |
| **Router** (58 cases) | `route_intent` on the exact input the gateway builds | the chosen agent equals the golden (≥ 95% overall, 100% on explicit routing rules) | valid `RouteDecision` JSON that was not cut off (`MAX_TOKENS` fails the run) |
| **Journeys** (5) | the full stack over HTTP: UI API → gateway → A2A agents → MCP → PostgreSQL | answering agents per turn, tool calls (read from the gateway's stored session), required UI events (quote card, cart update), no errors | reply match and rubrics, per turn |

**LLM-as-judge.** Response metrics use a second model call (the judge, `gemini-3-flash-preview`, three samples each) to grade meaning rather than exact wording. Trajectory and routing checks are deterministic. Thresholds live in each `test_config.json`.

### How a run works

```mermaid
flowchart LR
  G[(Golden datasets<br/>reviewed)] --> E[scripts/eval.sh]
  E --> DB[(csa_eval database<br/>reset to seed data)]
  E --> A[Agents tier<br/>ADK AgentEvaluator]
  E --> R[Router tier]
  E --> J[Journeys tier<br/>full stack over HTTP]
  A --> M[Trajectory + response metrics<br/>LLM judge where needed]
  R --> M
  J --> M
  M --> OUT[evals/results/&lt;timestamp&gt;/<br/>summary, CSV, JSON]
```

1. `scripts/eval.sh` installs the eval extras if needed (`evals/requirements.txt`, i.e. `google-adk[eval]`).
2. It creates a separate **`csa_eval`** database and resets it to seed data. Your development database is never touched, and every run starts from identical data.
3. **Agents and router:** each golden case runs against the real model in-process. The catalog and serviceability services are reused or started for MCP tools.
4. **Journeys:** it resets the database again, starts the whole stack on `csa_eval`, sends each conversation through `/api/session` and `/api/chat`, then reads the gateway's stored session to recover every agent's tool calls.
5. Each case gets a trajectory score and response scores. A case passes only when every metric meets its threshold.
6. Results go to `evals/results/<timestamp>/`: a `summary.txt` table, per-agent CSVs with every metric, expected vs actual reply and tool calls, router and journey JSON, and `run-<n>/cases.jsonl` (one line per case, the input for the Langfuse export). The script exits non-zero on any failure.
7. With `--langfuse`, the run is then exported to Langfuse as dataset experiment runs with per-metric scores ([Agent Observability](#agent-observability-langfuse)). Without it nothing is sent, even when `.env` has Langfuse keys.

### Running evals

Prerequisites:
- PostgreSQL (`scripts/db.sh up`) and the venv (`scripts/setup_local.sh`).
- A Gemini key **with billing**. A full run is roughly 1,000–1,500 model calls including judges; the free tier (20 requests/day) cannot run it.

```bash
scripts/eval.sh                                # everything: 10 agents + router + journeys
scripts/eval.sh --only faq,product             # selected agents
scripts/eval.sh --only router                  # routing only (~1 minute)
scripts/eval.sh --only journeys                # end-to-end; stop the dev stack first (scripts/stop_local.sh)
scripts/eval.sh --only journeys:s4             # one journey
scripts/eval.sh --runs 3                       # 3 independent runs; a case must pass all of them
scripts/eval.sh --only router --langfuse       # also export results to Langfuse (Datasets → csa-golden-*)
pytest evals -q                                # offline golden validation (no key, runs in normal test suites)
```

Run evals after any change to a prompt, a tool, routing or the model. Reading a failure:
- open the agent's CSV in `evals/results/<timestamp>/run-1/`
- compare `expected_tool_calls` with `actual_tool_calls` for trajectory failures
- compare `expected_response` with `actual_response` for response failures

### Golden lifecycle: record → review → approve

Goldens are reviewed data, like code. Only **approved** cases run.

1. **Author** a case: user turns, expected tool calls (only arguments that are stable from run to run; never ids or dates created during the run) and rubrics, from a `Scenarios.md` row.
2. **Record** the reference reply from the real model:
   ```bash
   EVAL_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_eval \
     venv/bin/python -m evals.record_golden --set agents/<agent>/<agent>               # fill missing replies
   venv/bin/python -m evals.record_golden --set agents/<agent>/<agent> --rerecord --case <id>   # after a fix
   scripts/eval.sh --only journeys:<name> --record                                     # journeys
   ```
   It prints the tool calls the model actually made, for comparison with the golden.
3. **Review and approve:**
   ```bash
   venv/bin/python -m evals.review --list --pending
   venv/bin/python -m evals.review --show <case key>
   venv/bin/python -m evals.review --approve <case key> --by "Your Name"
   ```
   Approve only when both the trajectory and the reply are what a correct agent should do. If the agent is wrong, fix the agent (through an OpenSpec change), not the golden.

Offline checks run with every `pytest`. `evals/test_golden_valid.py` fails when:
- a golden uses an unknown tool or parameter
- a reviewed case has no reference reply
- seed data changed since review

Replies that contain dates relative to today (installation slots, payment plans) skip the exact-reply comparison but keep their trajectory and rubric checks (`skip_metrics` in `MANIFEST.json`).

### Baseline results

Latest scored result per tier (`gemini-3-flash-preview`, judge `gemini-3-flash-preview`):

| Tier | Result | Notes |
|---|---|---|
| Agents | **52 / 52 cases pass** every metric | greeting 4/4, faq 5/5, discovery 6/6, serviceability 6/6, product 7/7, offer_management 5/5, order 5/5, payment 5/5, service_fulfillment 5/5, customer_communication 4/4 |
| Router | **58 / 58** (100%), explicit-rule cases 100% | no `MAX_TOKENS` truncation |
| Journeys | **14 / 17 turns** with the correct agents, tool calls and UI events | the 3 other turns timed out waiting for slow model responses (no wrong behavior); s1 (9 turns) and s4 pass their rubric checks |

Grounding (`hallucinations_v1`) is scored at the agent tier, where it is reliable. At journey level, replies combine several remote agents and the judge's scores were not meaningful, so journeys score trajectory, reply match and rubrics.

More detail: [evals/README.md](evals/README.md) and the `agent-evaluation` spec in `openspec/specs/`.

---

## Agent Observability (Langfuse)

Every chat turn can be traced end to end in [Langfuse](https://langfuse.com), an open-source LLM observability platform. Tracing is **optional**: it turns on when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set, and is off otherwise (tests and plain eval runs never send anything). The project uses **Langfuse Cloud** for every environment (local, docker compose, Cloud Run), so there is nothing to host.

### What you get

| In Langfuse | What it shows for this system |
|---|---|
| **Trace** (one per chat turn, named `chat_turn`) | The whole turn across processes: gateway workflow (`prepare_turn`, `route_intent`, `dispatch`, `handoff_policy`, `finish_turn`) → the remote agent (A2A) → its Gemini calls → its tools → the MCP tool service (`catalog` / `serviceability`). Input = the user message, output = the streamed reply |
| **Observations** inside a trace | `AGENT` (agent invocations), `GENERATION` (every Gemini call: model, prompt, response, tokens, cost, latency), `TOOL` (function and MCP tool calls with arguments and results), `CHAIN` (workflow nodes), `SPAN` (`chat_turn`, other steps) |
| **Session** | One conversation (all turns of one gateway session) |
| **User** | The customer id (`CUST-...`) once discovery has identified the company; before that, the browser's anonymous id |
| **Scores** | `user_feedback` (thumbs up/down in the chat UI, 1/0 on that turn's trace); golden-eval metrics and `passed` (from `scripts/eval.sh --langfuse`) |
| **Datasets** | `csa-golden-agents-<agent>`, `csa-golden-router`, `csa-golden-journeys`: golden cases, with one experiment run per eval run for side-by-side comparison |
| **Environment** | `local` (start_local.sh), `docker` (compose), `gcp` (Cloud Run), `eval` (eval stack), `sdk-experiment` (eval exports) |
| **Release** | The Cloud Run image tag (`<git sha>-<timestamp>`), to compare behavior across deploys |

### How it works in this codebase

```
Browser ─▶ Gateway: root span "chat_turn"; session + user ids put into OTel baggage
             │  A2A (httpx): W3C traceparent + baggage headers
             ▼
          Agent service: TraceContextMiddleware extracts them → ADK spans join the same trace
             │  MCP: trace context travels inside the JSON-RPC "_meta" field (mcp 2.2)
             ▼
          Tool service: MCP server emits a "tools/call" span in the same trace
Every process: BatchSpanProcessor → masking/filter exporter → OTLP/HTTP → Langfuse
```

- **One shared module**, `libs/sales_common/sales_common/telemetry.py`. `create_a2a_app` (all 10 agents), the catalog/serviceability apps and the gateway call `init_telemetry(name)`, so no agent has tracing code of its own.
- **Standard OpenTelemetry underneath.** Spans come from the OpenTelemetry SDK, with ADK instrumented by OpenInference's `GoogleADKInstrumentor` (agent/LLM/tool/workflow-node spans with input, output, model and token usage). They are exported over **OTLP/HTTP** to `{LANGFUSE_BASE_URL}/api/public/otel/v1/traces` with Basic auth from the key pair. Langfuse maps the OpenTelemetry/OpenInference attributes to its trace model.
- **Before export**, every span gets `langfuse.session.id`, `langfuse.user.id`, `langfuse.environment` and `langfuse.release`. Card numbers, CVVs and account/routing numbers are replaced with `[REDACTED_*]`. Plumbing spans are dropped: MCP protocol messages (`initialize`, `server/discover`, `tools/list`, ...) and a2a-sdk internals.
- **Feedback:** the SSE `done` event carries `trace_id` and a signed `feedback_token`; the UI's thumbs call `POST /api/feedback`, and the gateway posts the score to Langfuse's REST API.
- **Cloud Run:** CPU is throttled after a response, so each request flushes its spans before its last byte (`TELEMETRY_FLUSH_PER_REQUEST=true`, at most `TELEMETRY_FLUSH_TIMEOUT_MS`, 2 s). A Langfuse outage is logged, never raised; chat keeps working.

Design and decisions: [openspec/BASELINE.md §10](openspec/BASELINE.md), the `agent-observability` spec (`openspec/specs/agent-observability/spec.md`) and the archived change `openspec/changes/archive/2026-11-15-langfuse-observability/`.

### How Langfuse works underneath

Langfuse runs as two services in front of four data stores. On Langfuse Cloud all of this is managed for you. Self-hosting (current version v4) needs all four stores; none can be left out, Redis included.

| Component | Role |
|---|---|
| **langfuse-web** | UI and APIs: receives OTLP traces and REST calls (scores, datasets), serves the dashboard |
| **langfuse-worker** | Processes ingested events asynchronously and writes them to ClickHouse |
| **PostgreSQL** | Transactional data: organizations, projects, users, API keys, prompts, datasets, settings |
| **ClickHouse** | Columnar (OLAP) store for the high-volume data: traces, observations and scores. Fast filtering and aggregation for the dashboards |
| **Redis / Valkey** | Queue between web and worker (references to incoming event batches), plus a cache for API keys and prompts |
| **S3-compatible blob storage** (S3, GCS, MinIO, ...) | Raw ingested events (kept for retries and replay) and media attachments |

Ingestion flow: our services send a batch → **web** authenticates it, writes the raw events to **blob storage** and puts a reference on the **Redis** queue → **worker** picks it up and writes traces/observations/scores to **ClickHouse** → the UI queries ClickHouse (and PostgreSQL for configuration). Traces usually appear within seconds; data written through the REST API can take longer. To self-host later (Docker Compose, Helm or Terraform, per the Langfuse docs), only `LANGFUSE_BASE_URL` and the keys change; no application code changes.

### Setup

1. Create a project in Langfuse Cloud (US `https://us.cloud.langfuse.com` or EU `https://cloud.langfuse.com`) and an API key pair (Project settings → API keys).
2. **Local:** put `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL` in `.env` and restart (`scripts/stop_local.sh && scripts/start_local.sh`, or `docker compose up`). Each service logs `Tracing <name> to https://...` at startup.
3. **GCP:** `scripts/setup_gcp.sh` asks for the two keys (stored in Secret Manager); `scripts/deploy_cloud.sh` then gives every Cloud Run service the secrets plus `LANGFUSE_HOST`, `LANGFUSE_TRACING_ENVIRONMENT=gcp`, `LANGFUSE_RELEASE=<image tag>` and `TELEMETRY_FLUSH_PER_REQUEST=true`. Without the secrets, services deploy with tracing off. `start_cloud.sh` / `shutdown_cloud.sh` need nothing extra, since Langfuse runs outside GCP. Details: [GCP_DEPLOY.md](GCP_DEPLOY.md#tracing-langfuse).
4. **Costs in Langfuse:** if a generation shows tokens but no cost for `GEMINI_MODEL`, add the model's price once under Project settings → Models.

| Variable | Default | Purpose |
|---|---|---|
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | (empty = tracing off) | Project key pair (Secret Manager on GCP) |
| `LANGFUSE_BASE_URL` (or older `LANGFUSE_HOST`) | `https://us.cloud.langfuse.com` | Langfuse region / host |
| `LANGFUSE_TRACING_ENVIRONMENT` | `local` | Environment label (`docker` in compose, `gcp` on Cloud Run, `eval` in eval runs) |
| `LANGFUSE_CAPTURE_CONTENT` | `true` | `false` = send structure, timings, models and tokens only (no prompts, replies or tool arguments) |
| `LANGFUSE_RELEASE` | (empty) | Release label (deploy sets the image tag) |
| `TELEMETRY_FLUSH_PER_REQUEST` / `TELEMETRY_FLUSH_TIMEOUT_MS` | `false` / `2000` | Flush spans before each response completes (Cloud Run) |
| `OTEL_SDK_DISABLED` | (empty) | `true` forces tracing off |

### What to look for in the Langfuse dashboard

Open your project in Langfuse and pick the environment in the top bar (`local`, `gcp`, ...).

| Question | Where | Filter / search |
|---|---|---|
| What happened in a turn? | **Tracing → Traces**, open a `chat_turn` trace | Timeline view: router decision (`route_intent` generation, its `RouteDecision` output), which agent answered, each Gemini call, each tool call and its arguments/result |
| Show me a whole conversation | **Tracing → Sessions** | Session id = the gateway session id (the `X-Session-Id` response header, also in `logs/gateway.log`) |
| Everything for one customer | **Tracing → Users** | User id = `CUST-...` (from discovery); earlier turns of a new visitor use the browser id |
| Which turns failed? | Traces | Tag `error`, or level/status = ERROR; open one and find the red observation |
| Which turns were handed off? | Traces | Tag `handoff`; metadata `handoff_hops` > 0 |
| Turns answered by one agent | Traces | Tag = agent name, e.g. `order_agent`, `serviceability_agent`, `faq_agent` |
| Was it routed correctly? | A trace → `route_intent` generation | Compare its input (routing JSON) with the output `target`; metadata `route_target` on the trace |
| Why was a turn slow? | Trace timeline; **Dashboards** latency charts | Sort traces by latency; look for long `GENERATION`s, MCP `tools/call`, or cold-start gaps on Cloud Run |
| Token use and cost | **Dashboards**; any `GENERATION` | Usage per model (`gemini-3-flash-preview`); cost needs the model price (Setup step 4) |
| What did users dislike? | **Scores**, or Traces filtered by score | `user_feedback` = 0 (thumbs down); open the trace to see the reply and the steps behind it |
| Did a deploy change behavior? | Traces | Filter by `release` (Cloud Run image tag) and compare errors, latency and feedback |
| Did a prompt change break the evals? | **Datasets** → `csa-golden-*` → Runs | Compare runs side by side (scores per metric, `passed`); runs are named `<results timestamp>-run-<n>` |
| Is payment data masked? | Any trace from a payment turn | Card numbers appear as `[REDACTED_CARD]`, CVV as `[REDACTED_CVV]` |

### Privacy, quota and troubleshooting

- **Data sent:** prompts, replies and tool arguments (masked as above). Company names, addresses and emails stay visible. Set `LANGFUSE_CAPTURE_CONTENT=false` to send no conversation content.
- **Quota:** a turn is roughly 10-40 observations. A full golden-eval export is several thousand, so eval export is opt-in (`scripts/eval.sh --langfuse`).
- **No traces at all:** check that the keys are set (startup log says `Tracing ... to ...`, not `Tracing disabled`), that `OTEL_SDK_DISABLED` is not `true`, and that `LANGFUSE_BASE_URL` is the region of your project.
- **`CERTIFICATE_VERIFY_FAILED` in service logs (corporate proxy):** the proxy re-signs `*.langfuse.com` with a CA that Python's certifi bundle lacks (curl works because macOS trusts it). Build a bundle of certifi's roots plus the proxy CAs from the System keychain, e.g. `mkdir -p .certs && { cat "$(venv/bin/python -c 'import certifi; print(certifi.where())')"; security find-certificate -a -c "<proxy root CA name>" -p /Library/Keychains/System.keychain; } > .certs/ca-bundle.pem`, then set `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` to its absolute path in `.env` (`.certs/` is gitignored). Native processes only; Cloud Run is not behind the proxy, and the path does not exist inside compose containers.
- **Spans from one hop missing:** every hop must run the current `sales_common`. Agents created outside `create_a2a_app` do not extract trace headers.

---

## Secrets and Configuration

- All configuration is environment variables. Shared defaults live in [.env.example](./.env.example); copy it to `.env` (git-ignored, as is any `.env.*` other than `.env.example`). Never commit real keys.
- Required: `GEMINI_MODEL`, `GOOGLE_API_KEY` (or Vertex AI env), `DATABASE_URL`, `SESSION_SECRET_KEY` (gateway), `PUBLIC_URL` (each agent service). Services fail fast at startup when a required variable is missing.
- In GCP, secrets come from Secret Manager (`GOOGLE_API_KEY`, `SESSION_SECRET_KEY`, `DB_PASSWORD`, and the optional `SMTP_USER`, `SMTP_PASSWORD`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`); service-to-service calls use Google-signed ID tokens (`SERVICE_AUTH=gcp_id_token`).
- Card numbers, CVVs and bank account numbers typed into chat are masked before the message is routed or stored; payment details are entered only in the secure payment form ([A2UI Generative UI](#secure-payment-entry)). Payment tokens are stripped from every SSE payload.
- Gemini safety thresholds default to `BLOCK_MEDIUM_AND_ABOVE` (`SAFETY_*`); `BLOCK_LOW_AND_ABOVE` blocked ordinary payment replies as false positives.
- Database passwords are masked in logs; the browser log endpoint (`POST /api/client-log`) requires a session token, is rate-limited and strips control characters. Traces sent to Langfuse have card numbers, CVVs and account numbers masked (`LANGFUSE_CAPTURE_CONTENT=false` sends no content at all).

---

## Known Limitations

- **Rate limiting is per gateway instance** (in-memory token bucket); use a shared store or Cloud Armor for multi-instance limits.
- **One shared PostgreSQL schema** with some cross-domain writers (Payment and Fulfillment update `orders`); single-writer services (`mcp-remaining-domains`) were decided against.
- `contacts` and `opportunities` have no unique index (seed data contains legacy duplicates); duplicates are prevented in code under an advisory lock.
- The catalog image downloads the embedding model at build time; knowledge search reports `available: false` if the index is missing.
- ADK compaction, context caching and `to_a2a` are experimental in google-adk 2.10.0 (pinned).
- **A2UI:** CopilotKit's generative UI is experimental (versions pinned exactly); the provider uses an inert local agent through `agents__unsafe_dev_only`; the UI bundle is about 0.9 MB gzipped larger. Surfaces are deterministic; agents do not author A2UI yet.
- **Tracing:** `openinference-instrumentation-google-adk` (pinned 1.1.6) patches ADK internals, so an ADK upgrade must re-run the tracing tests. On Cloud Run each request waits for its spans to be sent (bounded by `TELEMETRY_FLUSH_TIMEOUT_MS`); a span batch can still be lost if an instance is stopped mid-export. The Langfuse eval export (langfuse SDK 5.x) needs OpenTelemetry ≥ 1.45 while google-adk 2.10 pins ≤ 1.42.1, so it runs in an isolated environment.

---

## GCP Cloud Run Deployment

The system deploys as **13 Cloud Run services** (public gateway; private agents and tool services called with Google-signed ID tokens), a **Cloud Run job** for migrations + seed, and **Cloud SQL for PostgreSQL 16**:

```bash
scripts/setup_gcp.sh                   # one time: APIs, Artifact Registry, Cloud SQL, secrets, service accounts
scripts/deploy_cloud.sh                # build, migrate, deploy tools → agents → gateway
scripts/deploy_cloud.sh --only order   # redeploy one service
scripts/shutdown_cloud.sh              # pause: gateway private + Cloud SQL stopped
scripts/start_cloud.sh                 # resume
```

Tracing: when the Langfuse secrets exist (`setup_gcp.sh` asks for them), every service sends traces to Langfuse with environment `gcp`; see [Agent Observability](#agent-observability-langfuse).

See [GCP_DEPLOY.md](./GCP_DEPLOY.md) for resources, IAM, secrets, environment variables, costs, verification, troubleshooting and rollback.

---

## Documentation

| File | Purpose |
|------|---------|
| [openspec/BASELINE.md](./openspec/BASELINE.md) | **Start here:** maintained system map (services, ports, agents, tools, context keys, handoffs, commands, observability) |
| [AGENTS.md](./AGENTS.md) | Architecture, ADK standards, workflow and handoffs, development workflow |
| [Agent Service Guide](#agent-service-guide) (this README) | Building, serving and testing an agent service |
| [A2UI Generative UI](#a2ui-generative-ui) (this README) | Interactive cards: architecture, surface catalog, actions, secure payment form, adding a surface |
| [SuperAgent/README.md](./SuperAgent/README.md) | Gateway: workflow, API (incl. `/api/feedback`, `/api/payment-methods`, the `a2ui` SSE event), environment variables, tests |
| [SuperAgent/client/AGENTS.md](./SuperAgent/client/AGENTS.md) | React UI: structure, SSE events, A2UI rendering, secure payment form, feedback buttons |
| [services/catalog/README.md](./services/catalog/README.md) | Catalog REST + MCP + RAG service |
| [services/serviceability/README.md](./services/serviceability/README.md) | Serviceability REST + MCP service |
| [db/README.md](./db/README.md) | Migrations, seed files, table ownership |
| [GCP_DEPLOY.md](./GCP_DEPLOY.md) | Multi-service Cloud Run deployment guide |
| [Agent Observability](#agent-observability-langfuse) (this README) | Langfuse tracing: setup, how it works, dashboard guide |
| [evals/README.md](./evals/README.md) | Golden evals: tiers, running, Langfuse export, golden lifecycle |
| [tests/integration/README.md](./tests/integration/README.md) | Multi-process integration test |
| [Scenarios.md](./Scenarios.md) | Test cases and end-to-end conversation flows |
| `openspec/specs/`, `openspec/changes/` | Behavioral specs (source of truth, incl. `generative-ui`) and change proposals (open: `guided-checkout`; history, including `a2ui-generative-cards`, `2026-11-15-langfuse-observability` and the declined `2026-11-16-mcp-remaining-domains`, in `archive/`) |
| Each `<Agent>/AGENTS.md` | Individual agent documentation |

