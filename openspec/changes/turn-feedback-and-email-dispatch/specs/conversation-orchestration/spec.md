## MODIFIED Requirements

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

## ADDED Requirements

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
