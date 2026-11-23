## MODIFIED Requirements

### Requirement: Streaming chat API contract preserved

`POST /api/chat` SHALL continue to stream Server-Sent Events of types `token`, `activity_update`, `structured_card`, `cart_update`, `suggestions`, `done` and `error`, and SHALL additionally stream `a2ui` events (see the `generative-ui` capability) when A2UI is enabled. Payload shapes of the existing types SHALL be unchanged, except that when tracing is enabled the `done` event SHALL also carry `trace_id` (the turn's 32-hex-character trace id) and `feedback_token` (a signature binding that trace id to the session). When tracing is disabled, `done` SHALL carry neither field. `token.author` SHALL be the domain agent name. Orchestrator-internal output (routing decisions, workflow bookkeeping) SHALL NOT be streamed as `token` events. Identical final texts repeated by the transport SHALL be emitted once.

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
