## ADDED Requirements

### Requirement: Opt-in tracing configuration

Every service (gateway, agents, tool services) SHALL initialize tracing through one shared entry point, `sales_common.telemetry.init_telemetry(service_name)`, at startup. Tracing SHALL be enabled only when both `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set. Spans SHALL then be exported over OTLP/HTTP to `{host}/api/public/otel/v1/traces`, with Basic authentication from the key pair and the header `x-langfuse-ingestion-version: 4`. The host SHALL be `LANGFUSE_BASE_URL` (Langfuse's current name), else `LANGFUSE_HOST`, else `https://us.cloud.langfuse.com`. When either key is missing, no tracer provider SHALL be installed and no request to Langfuse SHALL be made. Calling `init_telemetry` more than once in a process SHALL have no further effect.

#### Scenario: Keys absent
- **WHEN** a service starts without `LANGFUSE_PUBLIC_KEY`
- **THEN** it serves requests normally, sends nothing to Langfuse, and the `done` event carries no `trace_id`

#### Scenario: Keys present
- **WHEN** a service starts with both keys and `LANGFUSE_HOST=https://cloud.langfuse.com`
- **THEN** its spans are exported to `https://cloud.langfuse.com/api/public/otel/v1/traces` with `Authorization: Basic base64(public:secret)`

### Requirement: One trace per chat turn across services

With tracing enabled, each `POST /api/chat` turn SHALL produce one trace whose root span is named `chat_turn`. The gateway SHALL send W3C `traceparent` and `baggage` headers on its A2A requests. Agent services SHALL extract them, so the remote agent's spans join the gateway's trace. MCP tool calls SHALL carry the trace context in the JSON-RPC `_meta` field, so the tool service's `tools/call` span joins the same trace. The root span SHALL record the user message as input, the streamed reply text as output, the answering agents as tags, and the number of handoff hops and retry attempts as metadata. It SHALL have error status when the turn ends in a stream `error`.

#### Scenario: Discovery hands off to serviceability
- **WHEN** a turn routes to `discovery_agent` and hands off to `serviceability_agent`, which calls `check_service_availability` over MCP
- **THEN** one trace contains the gateway workflow spans, both agents' invocation spans and the serviceability service's `tools/call check_service_availability` span

#### Scenario: Agent unavailable
- **WHEN** the routed agent service is down and the turn ends with a stream `error`
- **THEN** the `chat_turn` span has error status and the trace shows the failing hop

### Requirement: Agent, model and tool observations

Agent invocations, Gemini calls and tool calls SHALL be recorded as spans that Langfuse maps to agent, generation and tool observations, by instrumenting ADK with `openinference.instrumentation.google_adk.GoogleADKInstrumentor`. Each span SHALL carry input and output. Generation spans SHALL carry the model name and token usage. ADK workflow nodes (`invoke_workflow`, `invoke_node`) SHALL appear with their input and output, so the router decision and handoff policy are visible. Each agent, model or tool call SHALL appear once (no duplicate ADK-native span). The gateway's suggestion generation, which calls Gemini outside ADK, SHALL be recorded as a generation span with model, input, output and token usage.

#### Scenario: Router decision visible
- **WHEN** a turn takes the LLM routing path
- **THEN** the trace contains the `route_intent` generation, with the routing input and the `RouteDecision` output, and its token usage

#### Scenario: Tool call recorded once
- **WHEN** `order_agent` calls `create_cart`
- **THEN** the trace contains exactly one tool observation for `create_cart`, with its arguments and response

### Requirement: Conversation session, user and environment attributes

Every exported span, in every service, SHALL carry these attributes:
- `langfuse.session.id`: the gateway session id
- `langfuse.user.id`: the customer id from gateway state `user:customer_id` when known, otherwise the gateway session's user id
- `langfuse.environment`: from `LANGFUSE_TRACING_ENVIRONMENT`, one of `local`, `docker`, `gcp` or `eval`; default `local`
- `langfuse.release`: from `LANGFUSE_RELEASE`, when set

Session and user SHALL travel between services as W3C baggage. Only these two identifiers SHALL be placed in baggage.

#### Scenario: Conversation grouped
- **WHEN** a customer has a five-turn conversation
- **THEN** Langfuse shows five traces under one session whose id is the gateway session id

#### Scenario: Environment separation
- **WHEN** the same build runs locally and on Cloud Run
- **THEN** local traces have environment `local` and Cloud Run traces have environment `gcp`

### Requirement: Sensitive data masking

Before export, string span attributes SHALL have the following replaced:
- payment card numbers (13–19 digits, optionally separated by spaces or dashes, that pass the Luhn check) with `[REDACTED_CARD]`
- card security codes that follow `cvv`, `cvc`, `cvv2` or `security code` with `[REDACTED_CVV]`
- digit runs of 6–17 digits that follow `account number`, `routing number`, `acct` or `aba` with `[REDACTED_ACCOUNT]`

When `LANGFUSE_CAPTURE_CONTENT=false`, prompts, model responses, tool arguments, tool responses and node input/output SHALL be removed from spans before export. Names, timings, status, model and token usage SHALL be kept.

#### Scenario: Card number in a chat message
- **WHEN** a customer writes "pay with 4111 1111 1111 1111 cvv 123"
- **THEN** every exported span shows `[REDACTED_CARD]` and `[REDACTED_CVV]` instead of the digits

#### Scenario: Content capture disabled
- **WHEN** `LANGFUSE_CAPTURE_CONTENT=false`
- **THEN** the trace shows spans, durations, models and token counts, but no message or tool content

### Requirement: Protocol noise is not exported

Only MCP spans for requests that do work (`tools/call`, `resources/read`, `prompts/get`) SHALL be exported. All other MCP protocol spans (`initialize`, `server/discover`, `tools/list`, `ping`, `notifications/*` and any other method) SHALL NOT be exported. Spans from the a2a-sdk tracer (`a2a-python-sdk`: event-queue and task-manager internals) SHALL NOT be exported.

#### Scenario: A2A plumbing hidden
- **WHEN** a turn is served over A2A
- **THEN** the trace contains the agent, model and tool observations but no `a2a.server.*` spans

#### Scenario: Tool list refresh
- **WHEN** an agent refreshes its MCP tool list during a turn
- **THEN** the trace contains no `tools/list` span

### Requirement: Span delivery on Cloud Run and at shutdown

When `TELEMETRY_FLUSH_PER_REQUEST=true`, each HTTP request served by a gateway, agent or tool service SHALL flush pending spans before the final response chunk is sent, with a bounded timeout (`TELEMETRY_FLUSH_TIMEOUT_MS`, default 2000). Each service SHALL flush and shut down its tracer provider when the application shuts down.

#### Scenario: Scale to zero
- **WHEN** a Cloud Run agent instance handles one turn and then scales to zero
- **THEN** that turn's spans reach Langfuse

### Requirement: Telemetry never breaks a turn

Failures to export or flush spans, a Langfuse outage, and invalid incoming trace headers SHALL be logged, SHALL NOT raise into request handling, and SHALL NOT fail or delay a turn beyond the flush timeout.

#### Scenario: Langfuse unreachable
- **WHEN** `LANGFUSE_HOST` is unreachable
- **THEN** chat turns complete normally and a warning is logged
