# agent-services Specification

## Purpose
TBD - created by archiving change a2a-agent-services. Update Purpose after archive.
## Requirements
### Requirement: One A2A service per agent

Each domain agent SHALL run as its own process and container, reachable only through the A2A protocol (JSON-RPC over HTTP). The domain agents are: discovery, serviceability, product, offer management, order, payment, service fulfillment, customer communication, greeting, faq. No agent SHALL import another agent's package at runtime.

#### Scenario: Independent restart
- **WHEN** the `payment_agent` service is restarted
- **THEN** all other agent services continue to serve A2A requests without restarting

#### Scenario: No cross-agent imports
- **WHEN** the repository's Python sources are scanned
- **THEN** no agent package imports another agent package, and no code resolves agents through `sys.modules` lookups or `importlib.util.spec_from_file_location`

### Requirement: Agent card discovery

Each agent service SHALL serve an A2A Agent Card at `GET /.well-known/agent-card.json`. The card SHALL contain the agent's fixed name (e.g. `payment_agent`), a description, the streaming capability, and a public URL taken from configuration.

#### Scenario: Card fetch
- **WHEN** a client requests `/.well-known/agent-card.json` from the offer management service
- **THEN** it receives HTTP 200 with a JSON card whose `name` is `offer_management_agent` and whose interface URL equals the configured `PUBLIC_URL`

### Requirement: Durable agent sessions and tasks

Each agent service SHALL persist its sessions and A2A tasks in PostgreSQL. Successive A2A messages carrying the same context id SHALL continue the same agent session.

#### Scenario: Multi-turn with one agent
- **WHEN** the gateway sends two messages to `order_agent` with the same context id
- **THEN** the second message is processed with the first message in the agent's session history

### Requirement: Forwarded journey context

Each agent service SHALL accept forwarded journey context in A2A request metadata. Before the agent runs, it SHALL apply the forwarded journey keys, user profile and recent transcript to its session state. Tool results that change a journey key SHALL include a `_context_update` object with the new values.

#### Scenario: Customer context available to order agent
- **WHEN** the gateway forwards `customer_context` with `customer_id` `CUST-20260930-001` to `order_agent`
- **THEN** order tools that read `customer_context` see `CUST-20260930-001`

#### Scenario: Context update returned
- **WHEN** `generate_offer_quote` creates offer `OFF-1`
- **THEN** its function response contains `_context_update.offer_context.offer_id` = `OFF-1`

### Requirement: Health endpoint

Each agent service SHALL expose `GET /healthz`, returning HTTP 200 with the agent name when the process is ready, and HTTP 503 if its database is unreachable.

#### Scenario: Database down
- **WHEN** PostgreSQL is unreachable
- **THEN** `/healthz` returns 503

### Requirement: Service authentication in cloud

When `SERVICE_AUTH=gcp_id_token`, callers SHALL attach a Google-signed ID token whose audience is the target service URL. This SHALL apply to every service-to-service request: A2A calls from the gateway, and every MCP request from an agent to a tool service, including session setup and tool listing that happen outside a request context. Agent and tool services SHALL NOT be publicly invokable. When `SERVICE_AUTH=none` (local), no token is attached.

#### Scenario: Unauthenticated call rejected in cloud
- **WHEN** an anonymous request reaches a deployed agent service
- **THEN** Cloud Run rejects it with HTTP 403 before it reaches the agent

#### Scenario: MCP tools load on a cold instance
- **WHEN** a freshly started agent instance lists its MCP tools before handling any request
- **THEN** the request carries `Authorization: Bearer <ID token for the tool service URL>` and the tools load

### Requirement: Fail-fast configuration

An agent service SHALL refuse to start, with a clear error naming the missing variable, when any of these is unset: `GEMINI_MODEL`, `DATABASE_URL` (when the agent uses the database), or `PUBLIC_URL`.

#### Scenario: Missing model
- **WHEN** an agent service starts without `GEMINI_MODEL`
- **THEN** the process exits non-zero, logging `GEMINI_MODEL is required`

### Requirement: FAQ answers are grounded

`faq_agent` SHALL call `search_faq` before answering and SHALL state only facts present in the returned passages. When no relevant passage is returned, it SHALL say a specialist will follow up instead of answering.

#### Scenario: Question not in the corpus
- **WHEN** a customer asks something the FAQ corpus does not cover
- **THEN** the agent does not invent an answer and offers a specialist follow-up

### Requirement: Agents know the current date

Every agent's instruction SHALL include today's date (from `import_forwarded_context`). Tools that create plans or appointments SHALL reject start dates in the past.

#### Scenario: Payment plan without a date
- **WHEN** a customer asks for a payment plan without a start date
- **THEN** the first installment is due after today, never in a past year

### Requirement: Fulfilled orders cannot be cancelled

`cancel_order` SHALL refuse orders whose status is fulfilled, activated, installed, completed or cancelled. The order agent SHALL relay the refusal without first asking for a cancellation reason.

#### Scenario: Cancel a fulfilled order
- **WHEN** the customer asks to cancel an order with status `fulfilled`
- **THEN** the order is unchanged and the agent explains the service is already active

### Requirement: Payment history from the payments table

`get_payment_history` SHALL return the customer's rows from `payments` (matched on the payment's or its order's customer id), newest first, with optional date bounds and limit.

#### Scenario: Seeded customer
- **WHEN** history is requested for CUST-20260427-152
- **THEN** it returns the 495.97 payment for ORD-20260427-518 and no generated transactions

### Requirement: Competitor comparisons are declined

`product_agent` SHALL decline to compare with or comment on competitors and offer its own product specifications instead.

#### Scenario: Competitor question
- **WHEN** asked "How does your fiber compare to AT&T?"
- **THEN** the reply says it cannot compare with other providers and offers Connectivity Max fiber details

### Requirement: Registration without optional address fields

`discovery_agent` SHALL register a new company with `add_new_company` as soon as name, industry, street, city, state and ZIP are known. It SHALL NOT ask for suite, unit or floor.

#### Scenario: Complete address in one message
- **WHEN** a prospect gives company, industry and a full street address with ZIP
- **THEN** the company is registered in the same turn and the serviceability handoff runs

### Requirement: Empty model responses are retried

Agents SHALL use a model wrapper that repeats a non-streaming model call once when the response contains neither text nor a function call.

#### Scenario: Empty response
- **WHEN** Gemini returns a response with no text and no function call
- **THEN** the call is repeated once and the retry's response is used

### Requirement: Credit check reports the score

The payment agent SHALL include the credit score returned by `check_business_credit` together with the decision.

#### Scenario: Conditional approval
- **WHEN** the credit check returns a score of 55 and a conditional decision
- **THEN** the reply states both the score and the conditional approval

### Requirement: Agent service pattern documented in README

README.md SHALL contain the "Agent Service Guide" section, the single description of how an agent service is built: layout, `agent.py`, `server.py`, journey context, database access, notifications, prompts, tests and golden evals, Dockerfile, environment variables. Other docs SHALL link to it instead of a separate guide or a template folder.

#### Scenario: New agent
- **WHEN** a developer adds an agent
- **THEN** README "Agent Service Guide" gives the layout and templates, and no other template folder exists

### Requirement: Returning customers are acknowledged and resumed

When `discovery_agent` identifies a customer that already exists in the CRM, it SHALL publish `returning_customer_context` with `status` (`active_service`, `in_progress` or `known`) and the customer's active quote, pending orders, fulfillments, active services and last stored serviceability check. It SHALL restore the most recent active quote as `offer_context`. It SHALL restore a serviceability check for the account address made within `SERVICEABILITY_REUSE_DAYS` (default 30) as `serviceability_context` with `reused: true`. Its reply SHALL acknowledge that the customer was found and summarize their status before anything else happens:
- **active service:** the active service, and a question about what else the customer needs
- **in progress:** the saved quote, order or installation, and an offer to continue
- **known:** the address on file, and a question to confirm it

#### Scenario: Returning customer with a saved quote
- **WHEN** a customer with active quote `OFF-1` introduces their company
- **THEN** `offer_context.offer_id` is `OFF-1`
- **AND** the reply welcomes them back and offers to continue with `OFF-1`

#### Scenario: Customer with an activated service
- **WHEN** a customer with a `customer_master` row introduces their company
- **THEN** `returning_customer_context.status` is `active_service`
- **AND** the reply names the active service and asks what else they need

#### Scenario: Serviceability reused
- **WHEN** the account address was checked 3 days ago
- **THEN** `serviceability_context.reused` is true and no serviceability check runs in that turn

### Requirement: Unsaved quotes are not presented

`generate_offer_quote` SHALL return `success: false` with `error: "quote_not_saved"` and SHALL NOT publish `offer_context` when the quote cannot be persisted. The offer agent SHALL tell the customer that the quote could not be saved. When no quote is found, it SHALL say so without inventing a reason.

#### Scenario: Database unavailable while quoting
- **WHEN** saving the quote raises a database error
- **THEN** the tool result has `success: false` and `error: "quote_not_saved"`
- **AND** session state has no new `offer_context`

### Requirement: Payment methods REST endpoint

The payment service SHALL expose `POST /payment-methods` taking `customer_id`, `payment_type` (`credit_card` or `ach`) and the card (`card_number`, `expiry_month`, `expiry_year`, `cvv`) or bank (`routing_number`, `account_number`, `account_type`) fields. It SHALL validate and tokenize without a model call, save only the masked method and opaque token to `customer_payment_methods`, and return the payment type, brand, last four digits and whether it was saved, never the token or full numbers. Invalid details SHALL return HTTP 400 with the validation error. The gateway SHALL proxy it as `POST /api/payment-methods` for an authenticated chat session, taking `customer_id` only from the session state.

#### Scenario: Invalid card
- **WHEN** the card number fails the Luhn check
- **THEN** the endpoint returns 400 with "Invalid card number (failed Luhn check)" and nothing is saved

### Requirement: Replies do not repeat cards

Agents SHALL keep a reply to at most two short sentences when their tool result is shown as a card in the chat (serviceability, product lists and details, quotes, cart, orders, installation slots and confirmations, payment methods and receipts), and SHALL NOT repeat the card's rows, prices, slots or identifiers. The serviceability agent SHALL NOT disclose internal network element details (switch, cabinet, OLT, splice point or fiber pair identifiers).

#### Scenario: Serviceable address
- **WHEN** serviceability_agent confirms service at an FTTP address
- **THEN** its reply is a one- or two-sentence confirmation with a next question and contains no switch or cabinet id

### Requirement: Notification dispatch endpoint

The customer communication service SHALL serve `POST /dispatch`, without calling a model: it delivers the due pending notifications within the request (the same delivery as the background loop, safe to run concurrently with it) and returns `{"success": true, "processed", "sent", "simulated", "deduped", "retrying", "failed"}`. On Cloud Run the endpoint SHALL be private like every agent service.

#### Scenario: Pending rows delivered on request
- **WHEN** two `pending` notifications exist and `POST /dispatch` is called
- **THEN** the response reports `processed: 2` and both rows are no longer `pending`

### Requirement: Agents warm their tool services at startup

An agent service SHALL, when it starts, send a `GET` in the background to the endpoint of each configured MCP dependency (environment variables ending in `_MCP_URL`), with service authentication; any response from the tool service counts as warmed. Failures SHALL NOT delay or fail startup.

#### Scenario: Product agent cold start
- **WHEN** the product agent starts with `CATALOG_MCP_URL=https://csa-catalog-…/mcp/`
- **THEN** it sends `GET https://csa-catalog-…/mcp/` without waiting for the response before serving

### Requirement: Producer tools report the queued notification id

Every tool that queues an outbox notification SHALL return its `notification_id` (order: `email_notification_id`) in the result, next to any boolean flag, so the gateway can report the notification's delivery status. This covers `schedule_installation`, `dispatch_technician`, `complete_installation` and `activate_service` in service fulfillment.

#### Scenario: Installation booked
- **WHEN** `schedule_installation` books an appointment and queues `installation_scheduled`
- **THEN** its result contains `notification_queued: true` and the row's `notification_id`

### Requirement: Installation emails show the time window

The `installation_scheduled` email SHALL show the booked time window as a readable range built from `start_time` and `end_time` (for example `1 PM–5 PM (afternoon)`), not the bare window code (`PM`); without times it SHALL fall back to the window name.

#### Scenario: Afternoon window
- **WHEN** the notification args are `window: "PM"`, `start_time: "13:00"`, `end_time: "17:00"`
- **THEN** the email reads `Time Window: 1 PM–5 PM (afternoon)`

