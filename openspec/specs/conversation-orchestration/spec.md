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

After `discovery_agent` registers or identifies a customer with a complete service address, and serviceability for that customer has not yet been checked in the session, the system SHALL invoke `serviceability_agent` within the same turn, passing the exact structured address. No additional user message SHALL be required. Exception: in the turn in which a customer already present in the CRM (`returning_customer_context` for the same `customer_id`) is first identified, the handoff SHALL NOT occur, and the gateway SHALL record `returning_acknowledged_customer`. On later turns the rule applies as above. Exception: after `add_new_company` registers a company and no contact email is on file (`customer_context.contact.email`), the gateway SHALL record `registration_waiting_for_contact` and the handoff SHALL NOT occur until discovery has saved a contact email; in the discovery turn that saves it, the handoff occurs and the flag is cleared.

#### Scenario: New company registration waits for the contact
- **WHEN** the user says "We're Crane.io at 123 Main St, Philadelphia PA 19103" and discovery registers the company without a contact email
- **THEN** the turn ends with the discovery reply and the contact card, without a `serviceability_agent` coverage result

#### Scenario: Contact saved, then coverage check
- **WHEN** the customer then saves the contact card and discovery records the contact email
- **THEN** the same streamed response contains the discovery confirmation followed by a `serviceability_agent` coverage result for ZIP 19103

#### Scenario: Serviceability already checked
- **WHEN** discovery updates a customer whose serviceability was already checked in this session
- **THEN** no automatic serviceability handoff occurs

#### Scenario: Returning customer acknowledged first
- **WHEN** discovery identifies an existing CRM customer whose address has not been checked
- **THEN** no serviceability handoff occurs in that turn
- **AND** when discovery runs on the next turn after the customer confirms the location, the handoff occurs

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

`POST /api/chat` SHALL continue to stream Server-Sent Events of types `token`, `activity_update`, `structured_card`, `cart_update`, `suggestions`, `done` and `error`, and SHALL additionally stream `a2ui` events (see the `generative-ui` capability) when A2UI is enabled and `progress` events (see "Turn progress events"). Payload shapes of the existing types SHALL be unchanged, except that when tracing is enabled the `done` event SHALL also carry `trace_id` (the turn's 32-hex-character trace id) and `feedback_token` (a signature binding that trace id to the session). When tracing is disabled, `done` SHALL carry neither field. `token.author` SHALL be the domain agent name. Orchestrator-internal output (routing decisions, workflow bookkeeping) SHALL NOT be streamed as `token` events. Identical final texts repeated by the transport SHALL be emitted once.

#### Scenario: Quote card emitted from remote tool result
- **WHEN** `offer_management_agent` generates a quote with an `offer_id`
- **THEN** the stream contains one `structured_card` event with `card_type` `quote` and the quote payload
- **AND** when A2UI is enabled, also one `a2ui` event for that quote

#### Scenario: No duplicate text
- **WHEN** a domain agent's final text is delivered twice by the transport
- **THEN** the client receives that text once

#### Scenario: Done carries the trace id
- **WHEN** tracing is enabled and a turn completes
- **THEN** the `done` event is `{"type": "done", "trace_id": "<32 hex>", "feedback_token": "<token>"}`

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

### Requirement: User feedback recorded as a trace score

`POST /api/feedback` SHALL accept `{"trace_id", "feedback_token", "value"}`, where `value` is `up` or `down`, with the same bearer session authentication as `POST /api/chat`. It SHALL apply a per-session rate limit with the same `RATE_LIMIT_*` settings as `POST /api/client-log`, in separate buckets. Responses:
- 401 when the bearer token is invalid
- 404 when tracing is disabled
- 429 when the rate limit is exceeded
- 400 when the body is malformed
- 403 when `feedback_token` was not issued for this session and trace id
- 502 when Langfuse rejects the score
- 204 when the vote has been recorded

The gateway SHALL record the vote as a Langfuse score named `user_feedback` on that trace: boolean, `1` for up and `0` for down. The score id SHALL be derived from the trace id, so a changed vote replaces the earlier one. The chat UI SHALL show thumbs-up and thumbs-down controls on assistant replies whose `done` event carried a `trace_id`, and SHALL show the selected vote.

#### Scenario: Thumbs down
- **WHEN** the user clicks thumbs down on a reply whose turn had trace id `T`
- **THEN** Langfuse shows a `user_feedback` score of 0 on trace `T`

#### Scenario: Changed vote
- **WHEN** the user clicks thumbs down and then thumbs up on the same reply
- **THEN** trace `T` has a single `user_feedback` score of 1

#### Scenario: Token from another session
- **WHEN** a client submits a `feedback_token` issued to a different session
- **THEN** the gateway responds 403 and records nothing

### Requirement: Suggestions are customer-voice and journey-aware

Each string in a `suggestions` event SHALL be a first-person message the customer could send to the sales agent. A suggestion SHALL NOT address the customer (for example "Tell me about your company"), SHALL NOT mention "the customer", and SHALL NOT be filler ("Continue", "Show me next best step"). Suggestions SHALL be chosen for the journey stage derived from the gateway session state (customer, serviceability, offer, order, installation and payment context), not only from the answering agent. They SHALL NOT ask the customer to provide information the journey already holds. When the agent's reply asks the customer for information or a decision, the first suggestion SHALL answer it, as a fill-in template using `[bracketed placeholders]` where the customer must supply details. When suggestions are enabled and the turn produced text, the gateway SHALL send three suggestions even if the suggestion model call fails.

#### Scenario: Agent asks for the company and address
- **WHEN** discovery_agent replies "What is your company name and business address?"
- **THEN** the first suggestion is a fill-in template such as "We're [company name], located at [street, city, state ZIP]"
- **AND** no suggestion contains "your company" or "your address"

#### Scenario: Quote already exists
- **WHEN** the session has an `offer_context.offer_id` and faq_agent answers a policy question
- **THEN** the suggestions include a request to proceed with or adjust the quote
- **AND** no suggestion offers to share the company name or address

#### Scenario: Suggestion model fails
- **WHEN** the suggestion model call raises an error after a reply that asks for a contact email
- **THEN** the gateway sends three suggestions, the first being a contact template containing `[email]`

#### Scenario: Rep-voice output from the model
- **WHEN** the model returns "Send order confirmation to customer"
- **THEN** that suggestion is dropped and replaced from the stage playbook

### Requirement: Placeholder templates are completed before sending

When the customer clicks a suggestion containing `[bracketed placeholders]`, the UI SHALL pre-fill the input and select the first placeholder. Tab or Enter SHALL move the selection to the next placeholder while any remain. The message SHALL NOT be sent while any placeholder remains.

#### Scenario: Filling a template
- **WHEN** the customer clicks "You can reach me at [email] or [phone]"
- **THEN** `[email]` is selected in the input
- **AND** after typing an email and pressing Tab, `[phone]` is selected
- **AND** pressing Enter while `[phone]` remains does not send the message

### Requirement: Suggestion reply templates match explicit requests

A fill-in reply template SHALL be chosen only when the agent's question explicitly asks for that information. A mention of "your location" in an offer SHALL NOT produce an address template. A question confirming "this location" SHALL produce a confirmation chip. When `returning_customer_context.status` is `active_service` and the session has no quote or order, suggestions SHALL use the `returning_active` stage.

#### Scenario: Location mentioned in an offer
- **WHEN** the agent asks "Add other services? (We also have Voice at your location.) Proceed with this quote?"
- **THEN** no suggestion contains `[street, city, state ZIP]`

#### Scenario: Existing-service customer
- **WHEN** `returning_customer_context.status` is `active_service` and there is no `offer_context`
- **THEN** the suggestions come from the `returning_active` stage

### Requirement: Order-to-scheduling handoff

When `create_order` succeeded in the current turn and the order has no scheduled installation, the gateway SHALL hand off from `order_agent` to `service_fulfillment_agent` in the same turn with a message asking it to show the available installation slots. The handoff counts toward the per-turn hop limit and fires once per created order.

#### Scenario: Order created
- **WHEN** order_agent creates order ORD-1 with status `pending_payment`
- **THEN** the same turn continues with service_fulfillment_agent, which offers installation slots

### Requirement: Payment details are masked before routing

The gateway SHALL replace card numbers that pass the Luhn check, CVV codes and bank account numbers in a user chat message with `[REDACTED_CARD]`, `[REDACTED_CVV]` and `[REDACTED_ACCOUNT]` before the message is stored, routed or sent to any agent.

#### Scenario: Card typed into chat
- **WHEN** the customer sends "my card is 4111 1111 1111 1111 cvv 123"
- **THEN** the router and agents receive "my card is [REDACTED_CARD] cvv [REDACTED_CVV]"

### Requirement: Turn progress events

The gateway SHALL stream `{"type": "progress", "stage": <stage>}` events during a turn: `routing` before the workflow runs, `agent` with `agent: <domain agent name>` each time the workflow routes or hands off to a different agent, `retrying` before a retry of the turn, and `suggestions` before suggestions are generated. The UI SHALL show, for the whole turn until `done` or `error`, a status line naming the current step and the elapsed seconds, and after 10 seconds on one step a note that starting a service can take up to a minute the first time.

#### Scenario: Handoff within a turn
- **WHEN** discovery_agent answers and the workflow hands off to serviceability_agent
- **THEN** the stream contains `progress` with `agent: "discovery_agent"` and later `progress` with `agent: "serviceability_agent"`, each once

#### Scenario: Status after the first text
- **WHEN** the first agent's text has streamed and suggestions are still being generated
- **THEN** the UI still shows the status line ("Preparing suggested replies…") until `done`

### Requirement: Services warmed at session start

When `POST /api/session` creates a session and `WARMUP_ENABLED` is true (default), the gateway SHALL, without delaying the response, send one request to every agent service that reaches its container (`GET /.well-known/agent-card.json`; `POST /dispatch` for customer communication) with service authentication, at most once per `WARMUP_INTERVAL_S` seconds (default 300) per gateway process. Failures SHALL be logged and SHALL NOT affect the session.

#### Scenario: Two sessions in quick succession
- **WHEN** two sessions are created 10 seconds apart on one gateway process
- **THEN** the agent services receive warm-up requests once

### Requirement: Email dispatch triggered by queued notifications

When a tool result in a turn reports a queued notification (`notification_id`, `email_notification_id`, `notification_queued: true`, `email_confirmation_queued: true` or a `notification_sent` object), the gateway SHALL request `POST /dispatch` on the customer communication service in the background, without delaying the turn, with at most one request in flight per gateway process; a trigger that arrives while one is in flight SHALL cause exactly one further request after it.

#### Scenario: Order confirmation email
- **WHEN** `create_order` returns `email_notification_id` in a turn
- **THEN** the gateway sends `POST /dispatch` to the customer communication service during that turn and the order confirmation is delivered without waiting for the service's background loop

### Requirement: Notification delivery status reported to the UI

The activity panel's notification entries SHALL show the delivery status, not only "queued". When a turn's tool results queued notifications, the gateway SHALL, before `done`, wait at most `NOTIFY_STATUS_WAIT_S` (default 5) for its dispatch request to finish, read those rows' status from `notifications`, and emit for each delivered row an `activity_update` (`category: "notification"`, `data: {notification_id, status, status_update: true}`). Rows still `pending` SHALL be reported at the end of a later turn of the same session (best effort, per gateway process). The UI SHALL update the matching entry in place and ignore a status update for an entry it does not show.

#### Scenario: Order confirmation delivered during the turn
- **WHEN** `create_order` queues the order confirmation and the dispatch request sends it before the turn ends
- **THEN** the turn emits a `queued` entry for it and, before `done`, a status update `sent` for the same `notification_id`, and the panel shows "sent"

#### Scenario: Dispatch slower than the wait
- **WHEN** the communication service is still starting when the wait ends
- **THEN** the entry stays "queued" and the next turn of the session reports its status

### Requirement: Deterministic payment-to-fulfillment handoff

When `process_payment` succeeds in a turn (status `completed`, `approved` or `captured`) for an order whose installation is scheduled but not yet dispatched (`order_context.installation.status == "scheduled"`), the gateway SHALL record `payment_completed_order` and invoke `service_fulfillment_agent` within the same turn, instructing it to provision the equipment and dispatch the technician for that order (not to activate the service). The key SHALL be cleared by the handoff. No handoff SHALL occur when the installation is not scheduled or was already dispatched.

#### Scenario: Payment starts provisioning
- **WHEN** the customer pays for order ORD-1 whose installation is scheduled
- **THEN** the same streamed response contains the payment confirmation followed by `service_fulfillment_agent` provisioning the equipment and dispatching the technician

#### Scenario: Already dispatched
- **WHEN** a payment succeeds for an order whose installation status is `dispatched`
- **THEN** no fulfillment handoff occurs

