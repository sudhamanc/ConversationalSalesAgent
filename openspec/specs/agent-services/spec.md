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

When `SERVICE_AUTH=gcp_id_token`, callers SHALL attach a Google-signed ID token whose audience is the target service URL. Agent and tool services SHALL NOT be publicly invokable. When `SERVICE_AUTH=none` (local), no token is attached.

#### Scenario: Unauthenticated call rejected in cloud
- **WHEN** an anonymous request reaches a deployed agent service
- **THEN** Cloud Run rejects it with HTTP 403 before it reaches the agent

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

