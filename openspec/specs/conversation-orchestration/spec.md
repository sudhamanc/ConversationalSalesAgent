# conversation-orchestration Specification

## Purpose
TBD - created by archiving change adk2-workflow-orchestration. Update Purpose after archive.
## Requirements
### Requirement: Every user turn is routed by the orchestrator

The system SHALL route every user message through the orchestrator, which selects exactly one target domain agent from: `greeting_agent`, `faq_agent`, `discovery_agent`, `serviceability_agent`, `product_agent`, `offer_management_agent`, `order_agent`, `payment_agent`, `service_fulfillment_agent`, `customer_communication_agent`. A domain agent SHALL NOT retain control of later turns without passing through the orchestrator.

#### Scenario: Pricing request goes to offer management
- **WHEN** a registered customer sends "Give me a quote for Fiber 5G with SD-WAN"
- **THEN** the turn is handled by `offer_management_agent` and the streamed text is authored by `offer_management_agent`

#### Scenario: Follow-up answer returns to the agent that asked
- **WHEN** `order_agent` ended the previous turn with a question and the user replies "no, that's all"
- **THEN** the orchestrator routes the reply to `order_agent`

#### Scenario: Unrecognized routing decision falls back safely
- **WHEN** the routing decision names an agent that does not exist
- **THEN** the turn is routed to `faq_agent` and a warning is logged with the session id

### Requirement: Greeting fast path

The system SHALL route a message consisting only of a greeting (e.g. "hi", "hello", "good morning"), or prefixed with `[GREETING]`, to `greeting_agent` without invoking the routing model.

#### Scenario: Initial UI greeting
- **WHEN** the UI sends "hi" on page load
- **THEN** `greeting_agent` responds and no routing-model call is made for that turn

### Requirement: Deterministic discovery-to-serviceability handoff

After `discovery_agent` registers or identifies a customer with a complete service address, and serviceability for that customer has not yet been checked in the session, the system SHALL invoke `serviceability_agent` within the same turn, passing the exact structured address. No additional user message SHALL be required.

#### Scenario: New company registration triggers coverage check
- **WHEN** the user says "We're Crane.io at 123 Main St, Philadelphia PA 19103" and discovery registers the company
- **THEN** the same streamed response contains the discovery confirmation followed by a `serviceability_agent` coverage result for ZIP 19103

#### Scenario: Serviceability already checked
- **WHEN** discovery updates a customer whose serviceability was already checked in this session
- **THEN** no automatic serviceability handoff occurs

### Requirement: Deterministic scheduling-to-payment handoff

After `service_fulfillment_agent` confirms an installation appointment for an order whose payment is not yet completed, the system SHALL invoke `payment_agent` within the same turn, with the order id and total amount.

#### Scenario: Scheduling confirmation starts payment
- **WHEN** the user confirms an installation slot and fulfillment returns an appointment id for an order with status `pending_payment`
- **THEN** the same streamed response continues with `payment_agent` requesting a payment method for that order id

#### Scenario: Already paid order
- **WHEN** scheduling is confirmed for an order whose payment status is `completed` or `approved`
- **THEN** no payment handoff occurs

### Requirement: Bounded handoff chaining

The system SHALL chain at most 2 automatic handoffs per user turn.

#### Scenario: Chain limit reached
- **WHEN** handoff conditions would trigger a third automatic handoff in one turn
- **THEN** the turn ends after the second handoff and the condition is re-evaluated on the next user turn

### Requirement: Streaming chat API contract preserved

`POST /api/chat` SHALL continue to stream Server-Sent Events of types `token`, `activity_update`, `structured_card`, `cart_update`, `suggestions`, `done` and `error`. Payload shapes SHALL be unchanged. `token.author` SHALL be the domain agent name. Orchestrator-internal output (routing decisions, workflow bookkeeping) SHALL NOT be streamed as `token` events. Identical final texts repeated by the transport SHALL be emitted once.

#### Scenario: Quote card emitted from remote tool result
- **WHEN** `offer_management_agent` generates a quote with an `offer_id`
- **THEN** the stream contains one `structured_card` event with `card_type` `quote` and the quote payload

#### Scenario: No duplicate text
- **WHEN** a domain agent's final text is delivered twice by the transport
- **THEN** the client receives that text once

### Requirement: Agent failure surfaces as a stream error

If a domain agent is unreachable or fails, the system SHALL emit one `error` event with a user-safe message, then `done`. Internal hostnames, stack traces or credentials SHALL NOT be included.

#### Scenario: Remote agent down
- **WHEN** `payment_agent` cannot be reached during a turn
- **THEN** the client receives an `error` event saying the payment service is temporarily unavailable, followed by `done`

### Requirement: Router output budget

The `route_intent` router SHALL complete its `RouteDecision` JSON within its output budget. On `gemini-3*` models it SHALL request `thinking_level=MINIMAL`, and its `max_output_tokens` SHALL be at least 1024.

#### Scenario: Gemini 3 routing
- **WHEN** `GEMINI_MODEL=gemini-3-flash-preview` and a message needs LLM routing
- **THEN** the router response finishes with `STOP` and parses as a `RouteDecision`

### Requirement: Company introductions route to discovery

The router SHALL send a message in which the customer introduces their company (with or without an address) to discovery_agent, not serviceability_agent. The deterministic handoff then runs the serviceability check after registration.

#### Scenario: Company with address
- **WHEN** the message is "We're Crane.io at 123 Main St, Philadelphia PA 19103"
- **THEN** the router chooses discovery_agent

