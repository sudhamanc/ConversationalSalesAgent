# Tasks: Langfuse Agent Observability

## 1. Shared library (`libs/sales_common`)

- [x] 1.1 Add `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http` and `openinference-instrumentation-google-adk` (pinned) to `pyproject.toml`, then install into the venv. Verify: `venv/bin/python -c "import opentelemetry.exporter.otlp.proto.http.trace_exporter, openinference.instrumentation.google_adk"` succeeds.
- [x] 1.2 Implement `sales_common/telemetry.py`:
  - `init_telemetry`: idempotent, a no-op without keys, OTLP/HTTP to `{LANGFUSE_HOST}/api/public/otel/v1/traces` with Basic auth and `x-langfuse-ingestion-version: 4`, then `GoogleADKInstrumentor().instrument()`
  - `LangfuseAttributesProcessor`
  - `FilteringMaskingExporter` (MCP noise drop, card/CVV/account masking, `LANGFUSE_CAPTURE_CONTENT=false` content removal, event attributes)
  - `TraceContextMiddleware` (extract and attach `traceparent`/`baggage`; flush before the final body when `TELEMETRY_FLUSH_PER_REQUEST=true`, bounded by `TELEMETRY_FLUSH_TIMEOUT_MS`)
  - `inject_trace_headers`, `turn_baggage_context`, `current_trace_id`, `shutdown_telemetry`

  Verify: new `tests/test_telemetry.py` (`InMemorySpanExporter`) covers each behavior, including Luhn-valid vs invalid digit runs, export failure logged and not raised, and an invalid `traceparent` ignored.
- [x] 1.3 Implement `sales_common/langfuse_api.py` (`LangfuseClient.from_env()`, `create_score` posting a one-element array to `POST /api/public/scores`; Basic auth; timeout; non-2xx raised as `LangfuseApiError`). Verify: `tests/test_langfuse_api.py` with `httpx.MockTransport` asserts the path, auth header and array payload.
- [x] 1.4 Wire `create_a2a_app` (`init_telemetry(name)`, wrap the app in `TraceContextMiddleware`, `shutdown_telemetry` in the lifespan) and `remote_agent()` (httpx `event_hooks={"request": [inject_trace_headers]}`). Verify: `tests/test_a2a_server.py` and new tests show that a request with a `traceparent` header produces agent spans with that trace id, and that the remote-agent client injects `traceparent`/`baggage`.

## 2. Tool services

- [x] 2.1 Call `init_telemetry` in `services/catalog/catalog_service/app.py` and `services/serviceability/serviceability_service/app.py`, add `TraceContextMiddleware`, and call `shutdown_telemetry` on shutdown. Verify: `pytest services/catalog/tests services/serviceability/tests -q` passes, and a unit test shows that an MCP `tools/call` with `_meta.traceparent` yields a `tools/call` span in that trace.

## 3. Gateway

- [x] 3.1 `server/main.py`: `init_telemetry("gateway")`, `TraceContextMiddleware`, and `shutdown_telemetry` in the lifespan. Verify: `pytest SuperAgent/tests -q` passes.
- [x] 3.2 `server/api/chat.py` `stream_turn`: a `chat_turn` root span with baggage (session id, customer id or user id), input, output, tags (answering agents, `handoff`, `error`), metadata (hops, attempts), error status; `done` carries `trace_id` and `feedback_token` only when tracing is on. Verify with tests:
  - With an in-memory provider, `done` has a 32-hex `trace_id` that equals the `chat_turn` span's trace.
  - The span has the session id attribute.
  - The error path sets error status.
  - With tracing off, `done` is `{"type": "done"}`.
- [x] 3.3 `server/api/feedback.py`: `POST /api/feedback` (bearer auth, client-log rate limit, itsdangerous token check, `create_score` with an id derived from the trace id, `user_feedback` BOOLEAN). Register it in `main.py`. Verify: tests for 401, 400, 403 (token from another session), 404 (tracing off) and 204 (mocked client called once with the expected payload; a revote reuses the same id).
- [x] 3.4 `server/api/suggestions.py`: an LLM span around the `genai` call (model, input, output, token counts). Verify: a test with a stubbed client shows one LLM span with `llm.token_count.total`.

## 4. UI (`SuperAgent/client`)

- [x] 4.1 `utils/api.js`: pass the `done` payload to `onDone`; add `sendFeedback(traceId, feedbackToken, value)`. Store `traceId`/`feedbackToken` on the finished assistant message. Verify: `npm run build` succeeds and `npm run lint` passes (if configured).
- [x] 4.2 `components/MessageBubble.jsx`: thumbs up/down (Tailwind only, accessible labels, selected state, disabled while sending) on assistant messages with `traceId`. Verify: build passes, `grep -n "style=" MessageBubble.jsx` finds nothing new, and in a manual run the vote shows as selected and appears in Langfuse.

## 5. Evals

- [x] 5.1 Write `cases.jsonl` from the router, agents and journeys tiers (key, tier, set, input, expected, actual, metrics, passed, session_id, trace_ids). Journeys capture `done.trace_id` and `X-Session-Id`. Verify: `pytest evals -q` passes (offline), and new unit tests for the writer pass.
- [x] 5.2 Add `langfuse` (5.x) to `evals/requirements.txt` and implement `evals/langfuse_sync.py`:
  - upsert datasets and items (stable item ids from case keys)
  - `run_experiment` per group, with a run name equal to the results directory; the task replays the recorded actual output and sets the case session through `propagate_attributes`
  - evaluators return each metric as NUMERIC and `passed` as BOOLEAN
  - refuses to run without keys

  Verify: a unit test with a fake Langfuse client over a sample `cases.jsonl` asserts the datasets, items, run name, replayed outputs and scores.
- [x] 5.3 `scripts/eval.sh --langfuse`: exports `LANGFUSE_TRACING_ENVIRONMENT=eval` and runs the sync on the results directory. Verify: `bash -n scripts/eval.sh`; `--help` lists the flag; a live `scripts/eval.sh --only router --langfuse` creates the `csa-golden-router` dataset run.

## 6. Scripts and configuration

- [x] 6.1 `.env.example`: `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_TRACING_ENVIRONMENT`, `LANGFUSE_CAPTURE_CONTENT`, `LANGFUSE_RELEASE` (commented), `TELEMETRY_FLUSH_PER_REQUEST`, `TELEMETRY_FLUSH_TIMEOUT_MS`. Verify: `scripts/start_local.sh` passes them through (shared `.env`).
- [x] 6.2 `docker-compose.yml`: `LANGFUSE_TRACING_ENVIRONMENT: docker` in the shared env anchor. Verify: `docker compose config` shows it on every app service.
- [x] 6.3 `scripts/setup_gcp.sh`: prompt for the Langfuse secrets (hidden; empty skips) and grant secretAccessor to the gateway, agent and tool service accounts. Verify: `scripts/setup_gcp.sh --dry-run` prints the secret creation and IAM bindings.
- [x] 6.4 `scripts/deploy_cloud.sh`: when both secrets exist, add the secrets, `LANGFUSE_HOST`, `LANGFUSE_TRACING_ENVIRONMENT=gcp`, `LANGFUSE_RELEASE=<tag>` and `TELEMETRY_FLUSH_PER_REQUEST=true` to every service. Verify: `scripts/deploy_cloud.sh --dry-run` output with the secrets present vs absent.

## 7. Documentation

- [x] 7.1 `openspec/BASELINE.md`: §1 line, §5 (`done` fields, `/api/feedback`), §7 commands, and a new Observability section. Verify: `pytest tests/test_baseline_doc.py -q` passes.
- [x] 7.2 `README.md` (Langfuse Cloud project and keys in getting started), `SuperAgent/README.md` (env table, API list), `GCP_DEPLOY.md` (secrets, env, cost/latency note, model-price step), `evals/README.md` (`--langfuse`, `cases.jsonl`, quota note), `SuperAgent/client/AGENTS.md` (feedback UI). Verify: `git grep -n LANGFUSE_` shows each documented variable.

## 8. End-to-end verification

- [ ] 8.1 Local, with keys in `.env`: run `scripts/db.sh up && scripts/start_local.sh`, then a greeting turn, a discovery → serviceability handoff turn and a product turn that uses MCP. Verify in Langfuse (environment `local`):
  - Partially verified (2026-11-15): stack running locally, all 13 services tracing, a model-free MCP call reached Langfuse (`local`). Owner's UI walkthrough not reported back; deferred at archive by the owner.
  - one trace per turn containing the gateway workflow, agent and `tools/call` spans
  - one session for the conversation
  - generations with model and tokens
  - a card number shown as `[REDACTED_CARD]`
  - a thumbs-down recorded as `user_feedback` = 0
- [ ] 8.2 Docker compose: one turn shows environment `docker`.
  - Deferred at archive by the owner (compose not run; note: the `.certs` CA bundle lines in `.env` are native-only).
- [ ] 8.3 Evals: `scripts/eval.sh --only router --langfuse` and `--only journeys:s4 --langfuse` create dataset runs with scores; the journey's experiment trace sits in its gateway session.
  - Deferred by the owner (2026-11-15): live eval runs cost Gemini tokens. The export path is covered offline (`evals/test_langfuse_sync.py`, SDK API checked in the isolated env); run it with the next eval run that is needed anyway.
- [x] 8.4 GCP: run `scripts/deploy_cloud.sh`, then `python scripts/e2e_test.py --base-url $GW`. Traces with environment `gcp` and release = image tag arrive.
  - Verified 2026-11-15: fresh GCP setup + deploy; traces with environment `gcp` and release = image tag arrive (gateway exports return 200); FAQ turn traced end to end (18 observations after filtering a2a-sdk spans). Led to fixes `fix-mcp-service-auth` and `fix-catalog-model-permissions` (archived).
- [ ] 8.5 Regression: `pytest` for every agent dir, `SuperAgent/tests`, `libs/sales_common/tests`, `evals` and `tests/test_baseline_doc.py`; then run the golden evals once with `scripts/eval.sh`.
  - Also deferred at archive: PostgreSQL-backed tests not run in this change.
  - Offline suites pass (2026-11-15). Golden evals not re-run, by owner decision: this change alters no prompt, model, tool or routing (CLAUDE.md's trigger for evals). PostgreSQL-backed tests (`TEST_DATABASE_URL`) still to run.
- [x] 8.6 `openspec validate langfuse-observability` passes. Commit the code with the change, then run `openspec archive langfuse-observability -y`.
