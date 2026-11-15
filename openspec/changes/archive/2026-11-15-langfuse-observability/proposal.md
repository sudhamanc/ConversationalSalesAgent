# Proposal: Langfuse Agent Observability

## Why

A chat turn crosses up to four processes: the gateway workflow (prepare_turn, router, dispatch, handoffs), a remote A2A agent, its Gemini calls and tools, and an MCP tool service. Nothing records that path. ADK 2.10 creates OpenTelemetry spans, but no service sets a TracerProvider or exporter, and no trace context crosses the A2A hop. When a turn misroutes, calls the wrong tool, is slow, or costs too many tokens, the only evidence is per-service log lines. We want full agent observability that works the same way locally and on GCP, without running new infrastructure. Langfuse Cloud provides this. Self-hosted Langfuse v4 would need ClickHouse, Redis and blob storage in addition to Postgres.

## What Changes

- **New `sales_common.telemetry`:**
  - One OpenTelemetry pipeline per process, exporting OTLP/HTTP to Langfuse (`{LANGFUSE_HOST}/api/public/otel/v1/traces`, Basic auth from the project key pair).
  - OpenInference `GoogleADKInstrumentor`, so agent, LLM and tool spans carry input, output, model and token usage.
  - Conversation session and user propagated as W3C baggage and stamped on every span.
  - An exporter wrapper that masks payment data (card, CVV, account and routing numbers), optionally drops all content (`LANGFUSE_CAPTURE_CONTENT=false`), and drops protocol-noise spans.
  - An ASGI middleware that extracts `traceparent`/`baggage` and can flush per request on Cloud Run.
  - Tracing is off unless `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set.
- **Wiring through shared factories only (no per-agent code):**
  - `create_a2a_app` initializes telemetry and adds the middleware.
  - `remote_agent()` injects trace headers on the gateway's A2A httpx client.
  - The catalog and serviceability apps initialize telemetry.
  - MCP hops propagate through the mcp 2.2 SDK's built-in `_meta` trace context.
- **Gateway:**
  - One root span `chat_turn` per turn, with input, output, answering agents, handoff count, retries and errors.
  - The SSE `done` event gains `trace_id` and `feedback_token` when tracing is on.
  - New `POST /api/feedback` records a thumbs up/down as a Langfuse score on that trace.
  - The suggestions Gemini call is traced as a generation.
- **UI:** thumbs up/down on assistant messages that carry a trace id.
- **Evals:**
  - `scripts/eval.sh --langfuse` writes a uniform `cases.jsonl` per run.
  - `python -m evals.langfuse_sync` upserts golden datasets, creates a dataset run per results directory, and posts per-metric scores.
- **Ops:**
  - New env vars in `.env.example`.
  - `setup_gcp.sh` prompts for the Langfuse keys and stores them in Secret Manager.
  - `deploy_cloud.sh` wires keys, host, environment `gcp`, the release tag and per-request flush when the secrets exist.
  - Compose marks its traffic as environment `docker`.
- **New `sales_common.langfuse_api`:** a small REST client for scores (gateway feedback). The eval sync uses the official `langfuse` SDK in an isolated environment and never in the services' venv.

## Capabilities

### New Capabilities

- `agent-observability`: distributed tracing of every turn to Langfuse, covering span sources, cross-service propagation, session/user/environment attributes, masking, opt-in configuration and flush behavior.

### Modified Capabilities

- `conversation-orchestration`: the `done` event carries `trace_id` and `feedback_token` when tracing is enabled (the streaming contract changes additively). The new feedback endpoint records user feedback as a score.
- `agent-evaluation`: eval runs can be exported to Langfuse as dataset runs with scores.
- `service-operations`: observability configuration for local, compose and GCP. Langfuse secrets go in Secret Manager and are wired at deploy.

## BASELINE.md sections affected

- §1 System at a glance (traces to Langfuse Cloud)
- §5 Gateway (`done.trace_id`/`feedback_token`, `POST /api/feedback`)
- §7 Commands (`scripts/eval.sh --langfuse`, `python -m evals.langfuse_sync`)
- New section: Observability (env vars, span sources, session/user mapping, masking, flush)

No service, port or agent tool changes, so `tests/test_baseline_doc.py` is unaffected.

## Non-goals

- Self-hosting Langfuse (Postgres + ClickHouse + Redis + blob storage). Moving later only changes `LANGFUSE_HOST` and the keys.
- Exporting OTel metrics or logs. This change covers traces only.
- Langfuse prompt management, LLM-as-judge evaluators hosted in Langfuse, and annotation queues.
- Sampling. Every turn is traced while keys are set; eval export is opt-in.
- Automating Langfuse model-price definitions. A missing price for `GEMINI_MODEL` is added once in the Langfuse UI (documented).

## Impact

- **Agents:** no prompt, tool or routing change. All 10 agents get tracing through `create_a2a_app`. The golden evals are re-run once to confirm there's no regression.
- **APIs / MCP servers:**
  - `done` SSE payload gains two optional fields.
  - New `POST /api/feedback` (bearer auth, rate limited).
  - MCP tool services emit `tools/call` spans (the SDK default) once a TracerProvider is set.
  - A2A requests carry `traceparent`/`baggage` headers.
- **Data:** no schema or seed change. Prompts, responses and tool arguments (masked) are sent to Langfuse Cloud when keys are set. Customer names, addresses and emails stay visible in traces; `LANGFUSE_CAPTURE_CONTENT=false` removes all content.
- **Dependencies:**
  - `libs/sales_common`: `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `openinference-instrumentation-google-adk`
  - `evals/requirements-langfuse.txt`: `langfuse` 5.x (eval sync only, in an isolated environment, because langfuse 5.x needs OTel ≥ 1.45 and ADK 2.10 pins ≤ 1.42.1)
- **Scripts:** `scripts/eval.sh` (`--langfuse`), `scripts/setup_gcp.sh` (Langfuse secrets), `scripts/deploy_cloud.sh` (secrets and env wiring), `docker-compose.yml` (environment label).
- **Cloud Run:** per-request span flush adds latency at the end of each request (export to Langfuse Cloud). Without it, CPU throttling after the response stalls the batch exporter.
- **Documentation:** BASELINE.md, README.md (getting started), SuperAgent/README.md (env, API), GCP_DEPLOY.md (secrets, env), evals/README.md, SuperAgent/client/AGENTS.md, `.env.example`.
