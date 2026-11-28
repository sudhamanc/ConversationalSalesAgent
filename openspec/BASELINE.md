# Project Baseline: Conversational Sales Agent

**Read this first in every session.** It is the maintained map of the system: what exists, where it lives, how the pieces connect. Trust it instead of re-discovering from code; open component docs (linked) only for depth.

**Keeping it true:** every OpenSpec change that alters a service, port, tool, context key, handoff rule or command updates this file in the same change. This file describes the system as it is; defects are tracked as OpenSpec changes, not listed here. `pytest tests/test_baseline_doc.py` fails when services, ports or agent tools drift from `scripts/services.conf` / `evals/golden/tool_schemas.json`.

Last verified: 2026-10-01 (ADK 2.10.0, google-genai 2.26.0, `GEMINI_MODEL=gemini-3-flash-preview`). All 115 golden eval cases reviewed.

---

## 1. System at a glance

```
Browser (React, :3000) ──/api──▶ Gateway SuperAgent (:8000, FastAPI + ADK Workflow "sales_journey")
                                   │  A2A (JSON-RPC, RemoteA2aAgent) to one agent per turn (+ ≤2 handoffs)
                                   ▼
              10 agent services (:8201–:8210, ADK Agent + server.py create_a2a_app)
                   │ MCP (streamable HTTP, McpToolset)        │ in-process FunctionTools
                   ▼                                          ▼
     catalog (:8101)  serviceability (:8102)          PostgreSQL 16 (one schema, :5432)
```

- One PostgreSQL database for everything (business tables, ADK sessions, A2A tasks). Local: Docker container `csa-postgres` via `scripts/db.sh up`.
- Agents never import each other; they talk only through the gateway (A2A). Deterministic data comes from tools (JSON); no LLM calls inside tools.
- Tracing (optional): with `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` set, every service exports OpenTelemetry traces to Langfuse Cloud; one trace per chat turn across gateway → agent → MCP tool service (§10).
- Company name shown to customers: **Connectivity Max**.

## 2. Services (from `scripts/services.conf`)

| Service | Kind | Port | Dir / module | A2A name | MCP deps |
|---|---|---|---|---|---|
| catalog | tool | 8101 | `services/catalog` · `catalog_service.app:app` | — | — |
| serviceability | tool | 8102 | `services/serviceability` · `serviceability_service.app:app` | — | — |
| discovery | agent | 8201 | `DiscoveryAgent` · `discovery_agent.server:app` | discovery_agent | — |
| serviceability-agent | agent | 8202 | `ServiceabilityAgent` · `serviceability_agent.server:app` | serviceability_agent | serviceability |
| product | agent | 8203 | `ProductAgent` · `product_agent.server:app` | product_agent | catalog |
| offer | agent | 8204 | `OfferManagement` · `offer_management.server:app` | offer_management_agent | — |
| order | agent | 8205 | `OrderAgent` · `order_agent.server:app` | order_agent | — |
| payment | agent | 8206 | `PaymentAgent` · `payment_agent.server:app` | payment_agent | — |
| fulfillment | agent | 8207 | `ServiceFulfillmentAgent` · `service_fulfillment_agent.server:app` | service_fulfillment_agent | — |
| communication | agent | 8208 | `CustomerCommunicationAgent` · `customer_communication_agent.server:app` | customer_communication_agent | — |
| greeting | agent | 8209 | `GreetingAgent` · `greeting_agent.server:app` | greeting_agent | — |
| faq | agent | 8210 | `FAQAgent` · `faq_agent.server:app` | faq_agent | catalog |
| gateway | gateway | 8000 | `SuperAgent` (runs from `SuperAgent/server`) · `main:app` | — | — |
| ui (Vite) | — | 3000 | `SuperAgent/client` | — | — |

Health: agents/tools `GET /healthz`, gateway `GET /health`; agent cards `GET /.well-known/agent-card.json`. Logs `logs/<service>.log`.

## 3. Agents

Every agent package `<Dir>/<package>/` has `agent.py` (`build_agent(model=None)`, `root_agent`), `prompts.py`, `server.py` (A2A app), `tools/`; tests in `<Dir>/tests/` (scripted `ScriptLlm`, no key); golden evals in `evals/golden/agents/<agent>/`. Pattern: [README: Agent Service Guide](../README.md#agent-service-guide).

| Agent (package) | Tools (parameters: `evals/golden/tool_schemas.json`) | Writes context | Owns tables |
|---|---|---|---|
| **greeting_agent** (`greeting_agent`) | — (prompt only; generic welcome, never uses the customer's company name) | — | — |
| **faq_agent** (`faq_agent`) | via MCP (catalog :8101): search_faq. RAG over the FAQ corpus `services/catalog/data/faq_docs/*.md`; answers only from retrieved passages, otherwise offers a specialist follow-up | — | — |
| **discovery_agent** (`discovery_agent`) | search_companies, get_company_profile, get_contact_personas, get_customer_intent, search_by_intent_signals, get_high_priority_opportunities, add_new_company, update_company_info, add_new_contact, update_contact_info, add_or_update_insights, create_opportunity_from_bant, check_customer_state | customer_context, returning_customer_context (+ restores offer_context, serviceability_context) | accounts, contacts, spend, opportunities, insights, actions |
| **serviceability_agent** (`serviceability_agent`) | via MCP (serviceability :8102): check_service_availability, extract_zip_code, get_coverage_zones, get_infrastructure_by_technology, normalize_address, validate_and_parse_address | serviceability_context | serviceability_checks (after-tool callback insert; reads coverage_zones via service) |
| **product_agent** (`product_agent`) | via MCP (catalog :8101, filtered to its 8 tools): compare_products, get_best_value_product, get_product_by_id, get_product_categories, list_available_products, search_product_knowledge, search_products_by_criteria, suggest_alternatives | — | — (reads products via service; never prices; declines competitor comparisons) |
| **offer_management_agent** (`offer_management`) | find_best_bundle_offer, generate_offer_quote, get_existing_quotes, get_quote_details | offer_context | quotes |
| **order_agent** (`order_agent`) | create_cart, add_to_cart, remove_from_cart, get_cart, clear_cart, create_order, update_order_status, get_order, modify_order, generate_contract, cancel_order | order_context | carts, cart_items, orders, order_items |
| **payment_agent** (`payment_agent`) | validate_payment_method, process_payment, get_payment_methods, tokenize_payment_method, add_payment_method, check_business_credit, get_credit_report, generate_invoice, get_payment_history, setup_payment_plan | payment_context | payments, payment_events, payment_rate_limit, customer_payment_methods |
| **service_fulfillment_agent** (`service_fulfillment_agent`) | check_availability, schedule_installation, reschedule_appointment, cancel_appointment, provision_equipment, track_equipment, verify_equipment_delivery, dispatch_technician, update_installation_status, complete_installation, activate_service, run_service_tests, get_fulfillment_status | order_context (status) | fulfillments, customer_master |
| **customer_communication_agent** (`customer_communication_agent`) | send_order_confirmation, send_quote_confirmation, send_payment_notification, send_installation_reminder, send_service_activated_notification, send_abandoned_cart_reminder, send_order_status_update, get_notification_history | — | notifications, dedup_cache (outbox dispatcher: background loop + REST `POST /dispatch`, no model, called by the gateway) |

Cross-writers (intentional; single-writer services in `mcp-remaining-domains` were decided against): service_fulfillment → accounts; order → quotes.status; payment/fulfillment → orders.status; gateway maintenance → quotes/orders expiry. Full table: [db/README.md](../db/README.md#table-ownership-writer-services).

Flow the prompts enforce: **cart → order (pending_payment) → installation scheduling → payment → confirmed**.
- Discovery: `search_companies`, then `add_new_company` in the same turn once name, industry (inferred), street, city, state and ZIP are known; never asks for suite/unit.
- Order: cart-first, asks "add other products?" before `create_order`; `cancel_order` refuses fulfilled/activated/installed/completed/cancelled orders (`NON_CANCELLABLE_STATUSES`) and is called without asking for a reason.
- Offer: `get_existing_quotes` first for returning customers, then `generate_offer_quote` (persists quote, emails when `customer_email` given).
- Serviceability: `validate_and_parse_address` then `check_service_availability`.
- Product: never states prices, ends with "Next Steps", declines competitor comparisons without tool calls.
- Agent startup (`sales_common.a2a_server` lifespan): background `GET <MCP URL>` to every `*_MCP_URL` dependency (Cloud Run answers external `/healthz` requests itself with 404), so a scaled-to-zero tool service starts with its agent.
- Payment: never asks for card data in chat; `get_payment_methods` first (shows the payment card), then `process_payment` with the chosen saved token. The service also serves REST `POST /payment-methods` (no model). `get_payment_history` reads `payments` (joined to `orders` and `customer_payment_methods`, method masked); `setup_payment_plan` and fulfillment `check_availability`/`schedule_installation`/`reschedule_appointment` reject dates before today/tomorrow.

## 4. Journey context contract (`libs/sales_common/sales_common/context.py`)

A2A carries messages only, so state crosses the boundary explicitly:
- **Gateway → agent:** `build_forwarded_metadata` (A2A request metadata) → agent `before_agent_callback` `import_forwarded_context` copies `JOURNEY_KEYS` + `journey_transcript`, `user_profile`, `gateway_session_id` into session state.
- **Agent → gateway:** tool writes `tool_context.state[<key>]` → `after_tool_callback` `export_context_delta` appends `_context_update` to the tool response → gateway `ContextBridgePlugin` (`SuperAgent/super_agent/plugins.py`) merges it into gateway state.

`import_forwarded_context` also sets `current_date` ("YYYY-MM-DD (Weekday)") on every turn; `JOURNEY_CONTEXT_INSTRUCTION` shows it as "Today's date" so agents resolve relative dates from it.

`JOURNEY_KEYS = customer_context, serviceability_context, offer_context, order_context, payment_context, returning_customer_context`. Shapes:
- `customer_context`: `{customer_id, company_name, address: {street, address_line2, city, state, zip_code}, contact?: {name, email, phone?}}`. `contact` is written by discovery (`add_new_contact` / `update_contact_info` with a valid email, or the first contact on file in `get_company_profile`); offer, order and payment default their email from it, and `create_order` refuses without a valid email (`error: contact_email_required`).
- `serviceability_context`: `{is_serviceable, infrastructure_type, max_speed_mbps, available_products, available_product_categories, service_zone, estimated_install_days, service_address}`. Written by `serviceability_agent/callbacks.py` (after `check_service_availability`), not by an MCP tool.
- `offer_context`: `{offer_id, customer_id, company_name, items, term_months, total_price, monthly_total, total_discount}`
- `order_context`: `{order_id, customer_id, customer_name, contact_email, contact_phone, service_address, service_type, price, offer_id, total_amount, status}`
- `returning_customer_context`: `{customer_id, company_name, status: active_service|in_progress|known, active_quote, pending_orders, fulfillments, fulfilled_orders, active_services, last_serviceability}`. Written by discovery (`get_company_profile`, `check_customer_state`) for a customer found in the CRM, via `sales_common.repositories.customer_state.summarize_returning_customer`; the same call restores the active quote as `offer_context` (`restored: true`) and a stored check of the account address within `SERVICEABILITY_REUSE_DAYS` (default 30) as `serviceability_context` (`reused: true`, `checked_at`).
- gateway-only: `returning_acknowledged_customer`, `appointment_confirmed_order`, `installation_scheduled_order`, `last_agent`, `last_reply`, `transcript`, `user:customer_id`, `user:company_name`

## 5. Gateway (`SuperAgent/`, detail: [SuperAgent/README.md](../SuperAgent/README.md))

Workflow `sales_journey` (`super_agent/workflow.py`): `START → prepare_turn → (fast: dispatch | llm: route_intent → dispatch) → <agent node (RemoteA2aAgent)> → handoff_policy → … → finish_turn`.
- `prepare_turn`: pure greetings (or `[GREETING]` prefix) go straight to greeting_agent; otherwise builds the router input `{message, last_agent, last_reply (last 400 chars), journey flags, company_name, memories (≤5)}`.
- `route_intent`: `Agent(mode="single_turn", include_contents="none", output_schema=RouteDecision{target, reason})`, temperature 0, `max_output_tokens=1024`, `thinking_level=MINIMAL` on `gemini-3*` (thinking tokens count toward the output limit). Rules in `super_agent/prompts.py` (priority: greeting; company introduction with or without address → discovery; serviceability phrases; pricing phrases; short follow-ups stay with last agent; best scope).
- `handoff_policy` (`evaluate_handoff`, max 2 hops per turn): discovery → serviceability when the customer has a ZIP not yet checked, except in the turn a returning CRM customer is first identified (`returning_customer_context` for the same customer, then `returning_acknowledged_customer` is set) so discovery can welcome them back first, and while a new registration waits for its contact card (`registration_waiting_for_contact`, set when `add_new_company` succeeded with no `customer_context.contact.email`; cleared by the handoff once discovery has saved the email); discovery → order when an order waits for a contact (`order_waiting_for_contact`, set when `create_order` returned `contact_email_required`) and `customer_context.contact.email` is now set; order → fulfillment when `create_order` succeeded this turn and no installation is scheduled (`order_created_order`; fulfillment shows the slots); fulfillment → payment when an appointment was just confirmed and the order is unpaid; payment → fulfillment when `process_payment` succeeded (`payment_completed_order`) and the installation is `scheduled` (provision equipment, dispatch technician; activation stays a later step). `prepare_turn` loads a quote the customer names (`OFF-…`, active, same customer) into `offer_context`. Card/CVV/account numbers in user messages are masked (`telemetry.mask_text`) before routing.
- API: `POST /api/session` → bearer token (and, when `WARMUP_ENABLED` (default true), a background warm-up round at most once per `WARMUP_INTERVAL_S` (300) per process: `GET /.well-known/agent-card.json` on every agent, `POST /dispatch` on customer communication; `server/api/background.py`); `POST /api/chat` → SSE events `token{content, author}`, `activity_update`, `structured_card{card_type: quote|…}`, `a2ui{surface_id, kind, tool, author, operations}` (A2UI 1.0 surfaces built by `server/api/a2ui.py` from tool results + journey state: quote, serviceability, products, cart, order, installation slots/appointment, payment methods with `SecurePaymentForm`, receipt; rendered with CopilotKit's standard catalog; buttons send customer messages via `sendChatMessage({message, surface, button})` and the UI then marks that surface done (`client/src/a2ui/actedSurface.js`; a click while a reply streams is queued until it ends; an order placed or installation booked without a click closes the open cart/quote/contact or scheduling surfaces); `A2UI_ENABLED`; payment tokens stripped from all SSE payloads), `progress{stage: routing|agent|retrying|suggestions, agent?}` (status line in the UI for the whole turn), `cart_update`, `suggestions` (3 customer-voice chips from `server/api/suggestion_playbook.py` + Gemini: stage from session state, fill-in `[placeholder]` reply first when the agent asked for details), `error`, `done` (`done{trace_id, feedback_token}` when tracing is on); `POST /api/feedback` (`{trace_id, feedback_token, value: up|down}` → Langfuse score `user_feedback`; 404 when tracing is off); `POST /api/payment-methods` (secure form → payment service `POST /payment-methods`, model-free tokenization, `customer_id` from session state, masked response); `POST /api/client-log`; `GET /api/debug/session` (DEBUG=true only).
- Config: `super_agent/config.py` loads only the repo-root `.env` (no override). All agents' Gemini calls use `sales_common.config.generate_config` (safety settings, default `BLOCK_MEDIUM_AND_ABOVE`; replies of all agents are short when a card shows the tool result: `sales_common.prompts` "Cards in the chat"; 3 retries, `MODEL_REQUEST_TIMEOUT_MS` per-request timeout, default 120 s) and the model `sales_common.models.agent_model()` (`ResilientGemini`: a non-streaming response with no text and no function call is retried once). Rate limit, session TTL and safety thresholds come from env (see `.env.example`).
- Email dispatch: when a tool result in the turn reports a queued notification (`notification_id`, `email_notification_id`, `notification_queued`, `email_confirmation_queued`, `notification_sent`), `_run_turn` calls `api.background.request_dispatch()` → background `POST /dispatch` on customer communication (one in flight per process, one follow-up for triggers meanwhile). Before `done` the gateway waits up to `NOTIFY_STATUS_WAIT_S` (5) for that request, reads the turn's rows from `notifications` and emits `activity_update{category: notification, tool: notification_status, data: {notification_id, status, status_update: true}}` for delivered ones (still-pending ids are reported by a later turn of the session, per process); the panel updates the entry in place.
- Errors from agents/models surface as SSE `error` → UI "The assistant service is temporarily unavailable" (including Gemini 402 prepaid credits depleted / 429 quota).

## 6. Data (`db/`, detail: [db/README.md](../db/README.md))

- Connection budget (`csa-db` is `db-f1-micro`, about 22 usable connections shared by every instance): each process has one async engine (`sales_common.db.create_session_engine`, `NullPool` unless `DB_ASYNC_POOL_SIZE` > 0) shared by ADK sessions, the A2A task store and gateway memory, plus a psycopg tool pool (`DB_POOL_MIN` 0 / `DB_POOL_MAX` 2 / `DB_POOL_MAX_IDLE_S` 60).
- Migrations `db/migrations/001..006` (006: `serviceability_checks`, written by serviceability_agent's callback, read by `customer_state`) and seed `db/seed/001..003`, applied by `python -m sales_common.migrate [--seed]` (tracked in `schema_migrations` / `seed_versions`).
- Seed facts used by goldens: 165 accounts (e.g. Beacon Wealth Advisors CUST-20260426-038, 234 Charles Street, Baltimore MD 21201; Connection Pro Inc CUST-20260430-156), 16 products (FIB-1G/5G/10G, COAX-200M/500M/1G, VOICE-BAS/STD/ENT/UCAAS, SDWAN-ESS/PRO/ENT, MOB-BAS/UNL/PREM), 38 coverage ZIPs (19103 FTTP 5 Gbps, 21201 FTTP 5 Gbps, 06103 HFC 1 Gbps; 59601 not covered), 9 orders, 13 quotes, 8 fulfillments. Changing seed files invalidates golden review (`evals/test_golden_valid.py`).
- Knowledge corpora (markdown in git, indexed by the catalog service into ChromaDB at `services/catalog/data/embeddings` with one shared `all-MiniLM-L6-v2` embedder on CPU (`EMBEDDING_DEVICE`), rebuilt on start when a collection is empty): product docs `services/catalog/data/product_docs/`, FAQ/policies `services/catalog/data/faq_docs/` (the only facts the FAQ agent may state; keep consistent with pricing, scheduling, payment and expiry rules).

## 7. Commands

| Task | Command |
|---|---|
| One-time setup (venv, packages, UI deps, `.env`) | `scripts/setup_local.sh` |
| Local PostgreSQL (Docker, Homebrew fallback) + migrate + seed | `scripts/db.sh up` · stop: `scripts/db.sh down` |
| Start / stop everything | `scripts/start_local.sh [--only a,b] [--no-ui] [--skip-migrate]` · `scripts/stop_local.sh` |
| Containers | `docker compose up --build` |
| Unit/agent tests (no key) | `pytest <AgentDir>/tests -q` · `pytest SuperAgent/tests -q` · `pytest evals -q` · `pytest tests/test_baseline_doc.py -q` |
| DB-backed / integration tests | `TEST_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_test pytest … ` · `pytest tests/integration -q -s` |
| Live smoke | `python scripts/e2e_test.py --base-url http://127.0.0.1:8000` |
| Golden evals (billed key) | `scripts/eval.sh [--only <agent>,router,journeys,journeys:<name>] [--runs N] [--record] [--langfuse]`; goldens: `python -m evals.record_golden [--rerecord]`, `python -m evals.review` ([evals/README.md](../evals/README.md)). Judge model `gemini-3-flash-preview` (ADK's default `gemini-2.5-flash` is not available to this project) |
| Eval results → Langfuse | `scripts/eval.sh --langfuse` (or later: `uv run --no-project --with-requirements evals/requirements-langfuse.txt python -m evals.langfuse_sync evals/results/<ts>`); isolated env because langfuse 5.x needs OTel ≥ 1.45 and ADK 2.10 pins ≤ 1.42.1 |
| Cloud | `scripts/setup_gcp.sh`, `scripts/deploy_cloud.sh`, `scripts/start_cloud.sh`, `scripts/shutdown_cloud.sh` ([GCP_DEPLOY.md](../GCP_DEPLOY.md)) |
| OpenSpec | `openspec list`, `openspec validate <change>`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive` |

## 8. Change recipes (always start with an OpenSpec change)

- **Change an agent's behavior:** edit `<Dir>/<package>/prompts.py` (or `tools/`), update its tests, run `scripts/eval.sh --only <agent>` (+ `router` if scope words change); refresh and re-review affected goldens.
- **Add or change a tool:** implement in `tools/` returning a JSON dict (no LLM); register in `agent.py`; if it changes journey state write `tool_context.state[<JOURNEY_KEY>]`; add tool tests; `python -m evals.record_golden --snapshot-tools`; add golden cases; update §3 here.
- **Change routing or handoffs:** `SuperAgent/super_agent/prompts.py` / `workflow.py`; `pytest SuperAgent/tests`; `scripts/eval.sh --only router,journeys`; update §5.
- **Add an agent:** follow the README "Agent Service Guide"; add to `scripts/services.conf`, `docker-compose.yml`, gateway registry (`super_agent/registry.py`), `evals/golden_io.py AGENT_PACKAGES`, golden set; update §2–3.
- **Schema change:** new `db/migrations/00N_*.sql` (never edit applied ones); update ownership in db/README.md and §6.
- **Config variable:** `.env.example` (+ SuperAgent/README.md table for gateway vars).
- **Trace something outside ADK** (a direct `genai` call, a background job): `with sales_common.telemetry.get_tracer(...).start_as_current_span(name, attributes={"openinference.span.kind": "LLM", ...})` (no-op when tracing is off); never put secrets or identifiers other than session/user into baggage.
- **FAQ / policy answer:** edit `services/catalog/data/faq_docs/*.md` (not the FAQ prompt), restart catalog (or `python services/catalog/scripts/ingest_knowledge.py`), then `scripts/eval.sh --only faq`.

## 9. Capability specs (behavioral source of truth: `openspec/specs/`)

| Capability | From change |
|---|---|
| agent-services, sales-data-store | a2a-agent-services |
| conversation-orchestration, conversation-state-memory | adk2-workflow-orchestration (+ router budget from local-dev-reliability) |
| product-catalog-service, serviceability-service | catalog-serviceability-mcp |
| service-operations | multi-service-scripts (+ db lifecycle from local-dev-reliability) |
| agent-evaluation | agent-eval-suite |
| project-baseline | project-baseline |
| agent-observability (+ additions to conversation-orchestration, agent-evaluation, service-operations) | langfuse-observability (2026-11-15) |
| generative-ui (+ SSE contract in conversation-orchestration) | a2ui-generative-cards (2026-11-23) |
| acted surfaces, `progress` events, warm-up, on-demand email dispatch | turn-feedback-and-email-dispatch (open) |

Open: `guided-checkout` (checkout surfaces, secure payment form, automatic scheduling, contact email; golden evals pending), `returning-customer-resume`, `turn-feedback-and-email-dispatch` (acted A2UI cards, turn progress, warm-up, `POST /dispatch`; cloud verification pending). Decided not to do: `openspec/changes/archive/2026-11-16-mcp-remaining-domains` (REST + MCP services for the other six domains; archived without merging specs). Archived changes: `openspec/changes/archive/`.

## 10. Observability (`libs/sales_common/sales_common/telemetry.py`)

Langfuse Cloud, the same for local, compose and Cloud Run. Off unless both keys are set (and `OTEL_SDK_DISABLED` is not true); tests and plain eval runs send nothing.

- **Setup:** every process calls `init_telemetry(name)` once: `create_a2a_app` (agents), the catalog/serviceability apps, gateway `main.py`. It installs the global `TracerProvider` → `BatchSpanProcessor` → `FilteringMaskingExporter` → OTLP/HTTP `{LANGFUSE_HOST}/api/public/otel/v1/traces` (Basic auth, `x-langfuse-ingestion-version: 4`), and `GoogleADKInstrumentor` (openinference, pinned 1.1.6; agent/LLM/tool/workflow-node spans with input, output, model, tokens; suppresses ADK's duplicate native spans).
- **One trace per turn:** gateway root span `chat_turn` (input, output, tags = answering agents + `handoff`/`error`, metadata hops/attempts/route target). Gateway → agent: `traceparent`/`baggage` from the httpx event hook on the `remote_agent()` client; agents extract them in `TraceContextMiddleware`. Agent → tool: mcp 2.2 carries the context in JSON-RPC `_meta`; tool services emit `tools/call` spans.
- **Attributes on every span** (`LangfuseAttributesProcessor`): `langfuse.session.id` = gateway session id, `langfuse.user.id` = `user:customer_id` (else browser user id), both via baggage (the only baggage keys); `langfuse.environment` = `LANGFUSE_TRACING_ENVIRONMENT` (`local`, `docker` in compose, `gcp` on Cloud Run, `eval` for `eval.sh --langfuse`); `langfuse.release` = `LANGFUSE_RELEASE` (image tag on Cloud Run).
- **Masking/filtering before export:** card numbers (Luhn-checked) → `[REDACTED_CARD]`, CVV → `[REDACTED_CVV]`, account/routing numbers → `[REDACTED_ACCOUNT]`; `LANGFUSE_CAPTURE_CONTENT=false` drops all prompts, replies and tool arguments; MCP protocol spans are dropped (only `tools/call`, `resources/read`, `prompts/get` are exported), and so are a2a-sdk internals (tracer `a2a-python-sdk`). Names, addresses and emails stay visible when content is captured.
- **Delivery:** `TELEMETRY_FLUSH_PER_REQUEST=true` (Cloud Run, set by `deploy_cloud.sh`) flushes before the final response chunk (bounded by `TELEMETRY_FLUSH_TIMEOUT_MS`, 5000); agent services also flush after every agent run (`TelemetryFlushPlugin`, added by `create_a2a_app`) while the A2A stream is open; lifespans call `shutdown_telemetry()`. Failed exports and timed-out flushes are logged as warnings, never raised.
- **Feedback:** UI thumbs (`FeedbackButtons.jsx`) → `POST /api/feedback` → `sales_common.langfuse_api` → Langfuse score `user_feedback` (BOOLEAN; score id and timestamp derived from the trace and turn, so a revote updates it).
- **Evals:** each run writes `evals/results/<ts>/run-<n>/cases.jsonl`; `eval.sh --langfuse` syncs them (`evals.langfuse_sync`, langfuse SDK 5.x in an isolated env) into datasets `csa-golden-agents-<agent>`, `csa-golden-router`, `csa-golden-journeys` as experiment runs named `<ts>-run-<n>` with per-metric and `passed` scores (environment `sdk-experiment`).
- **Config:** `LANGFUSE_BASE_URL` (or older `LANGFUSE_HOST`; default `https://us.cloud.langfuse.com`), `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_TRACING_ENVIRONMENT`, `LANGFUSE_CAPTURE_CONTENT`, `LANGFUSE_RELEASE`, `TELEMETRY_FLUSH_PER_REQUEST`, `TELEMETRY_FLUSH_TIMEOUT_MS`; GCP: secrets `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` (setup_gcp.sh, optional).
