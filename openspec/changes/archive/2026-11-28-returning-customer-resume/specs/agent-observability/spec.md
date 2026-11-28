## MODIFIED Requirements

### Requirement: Span delivery on Cloud Run and at shutdown

When `TELEMETRY_FLUSH_PER_REQUEST=true`, each HTTP request served by a gateway, agent or tool service SHALL flush pending spans before the final response chunk is sent, with a bounded timeout (`TELEMETRY_FLUSH_TIMEOUT_MS`, default 5000). Agent services SHALL also flush at the end of every agent run (`TelemetryFlushPlugin.after_run_callback`), while the request is still open. A failed export and a flush that times out SHALL each be logged as a warning. Each service SHALL flush and shut down its tracer provider when the application shuts down.

#### Scenario: Scale to zero
- **WHEN** a Cloud Run agent instance handles one turn and then scales to zero
- **THEN** that turn's spans reach Langfuse

#### Scenario: Flush after agent run
- **WHEN** an agent run finishes in an A2A service with per-request flushing
- **THEN** the run's spans are exported before the A2A response completes

#### Scenario: Export failure visible
- **WHEN** the OTLP exporter returns a failure
- **THEN** a warning naming the number of spans is logged
