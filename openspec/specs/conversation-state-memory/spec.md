# conversation-state-memory Specification

## Purpose
TBD - created by archiving change adk2-workflow-orchestration. Update Purpose after archive.
## Requirements
### Requirement: Durable sessions

Conversation sessions (events and state) SHALL be persisted in PostgreSQL and SHALL survive process restarts and be readable by any gateway instance.

#### Scenario: Restart mid-conversation
- **WHEN** a customer has registered their company, the gateway restarts, and the customer sends another message with the same session token
- **THEN** the orchestrator still has that customer's `customer_context` and prior conversation history

### Requirement: Shared journey context

The system SHALL maintain these session-scoped journey context keys, and SHALL make their current values available to every domain agent invoked in the session:
- `customer_context`
- `serviceability_context`
- `offer_context`
- `order_context`
- `payment_context`

Values produced by a domain agent's tool SHALL be reflected in session state before the next agent in the same turn runs.

#### Scenario: Order agent sees the quote
- **WHEN** `offer_management_agent` produced offer `OFF-123` and the user then says "place the order"
- **THEN** `order_agent` receives `offer_context.offer_id` = `OFF-123` without the user repeating it

#### Scenario: Exact values preserved
- **WHEN** discovery stores address ZIP `19103` in `customer_context`
- **THEN** the serviceability handoff uses ZIP `19103` exactly, character for character

### Requirement: Returning-user profile

The system SHALL accept a stable anonymous browser identifier when creating a session. It SHALL store user-scoped state (`user:` prefix), such as the last identified `customer_id` and company name, that is visible to later sessions of the same identifier.

#### Scenario: Returning browser
- **WHEN** a browser that previously identified as company "Crane.io" starts a new session
- **THEN** the orchestrator's routing context includes the known company name

### Requirement: Long-term memory

After each completed turn, the system SHALL add the session to a PostgreSQL-backed memory store, scoped to the user identifier. At the start of each turn it SHALL retrieve up to 5 relevant memories for the user's message, which are provided as routing context.

#### Scenario: Recall prior interest
- **WHEN** a returning user asked about SD-WAN in a previous session and now asks "what about the security product I looked at?"
- **THEN** the routing context for this turn includes the prior SD-WAN memory

#### Scenario: Memory isolation
- **WHEN** two different user identifiers each have memories
- **THEN** memory retrieval for one never returns the other's memories

### Requirement: Context compaction

Each agent application SHALL compact older conversation events into summaries so that model input stays bounded. Compaction is triggered by either (a) every 8 invocations, with 2 invocations of overlap, or (b) exceeding 60,000 prompt tokens, retaining the 10 most recent events.

#### Scenario: Long conversation
- **WHEN** a session exceeds 8 invocations
- **THEN** a compaction event exists in the session, and subsequent model requests include the summary instead of all compacted raw events

### Requirement: Model context caching

Each LLM-backed agent application SHALL enable model context caching with a TTL of 1800 seconds, refreshed after at most 10 invocations. It SHALL only cache prefixes that meet the model's minimum cacheable size.

#### Scenario: Cache configured
- **WHEN** any agent application starts
- **THEN** its App configuration includes a context cache config, and startup logs record the cache TTL and interval

### Requirement: Session tokens independent of instance

Session bearer tokens SHALL be verifiable by any gateway instance, with no in-memory registry. A token SHALL encode its expiry and be integrity-protected with `SESSION_SECRET_KEY`. Tokens for a revoked session SHALL be rejected.

#### Scenario: Token from another instance
- **WHEN** instance A issues a token and the next request lands on instance B
- **THEN** instance B accepts the token and serves the same session

#### Scenario: Tampered token
- **WHEN** a token's payload is modified
- **THEN** the request is rejected with HTTP 401 via an `error` SSE event

