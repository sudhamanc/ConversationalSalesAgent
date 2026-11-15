## MODIFIED Requirements

### Requirement: Streaming chat API contract preserved

`POST /api/chat` SHALL continue to stream Server-Sent Events of types `token`, `activity_update`, `structured_card`, `cart_update`, `suggestions`, `done` and `error`. Payload shapes SHALL be unchanged, except that when tracing is enabled the `done` event SHALL also carry `trace_id` (the turn's 32-hex-character trace id) and `feedback_token` (a signature binding that trace id to the session). When tracing is disabled, `done` SHALL carry neither field. `token.author` SHALL be the domain agent name. Orchestrator-internal output (routing decisions, workflow bookkeeping) SHALL NOT be streamed as `token` events. Identical final texts repeated by the transport SHALL be emitted once.

#### Scenario: Quote card emitted from remote tool result
- **WHEN** `offer_management_agent` generates a quote with an `offer_id`
- **THEN** the stream contains one `structured_card` event with `card_type` `quote` and the quote payload

#### Scenario: No duplicate text
- **WHEN** a domain agent's final text is delivered twice by the transport
- **THEN** the client receives that text once

#### Scenario: Done carries the trace id
- **WHEN** tracing is enabled and a turn completes
- **THEN** the `done` event is `{"type": "done", "trace_id": "<32 hex>", "feedback_token": "<token>"}`

## ADDED Requirements

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
