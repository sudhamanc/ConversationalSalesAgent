# Tasks: Returning-Customer Resume

## 1. Data

- [x] 1.1 `db/migrations/006_serviceability_checks.sql`. Verify: `python -m sales_common.migrate` on local Postgres; table exists.
- [x] 1.2 `sales_common.repositories.customer_state`: `summarize_returning_customer`, latest serviceability check, active quote details. Verify: `TEST_DATABASE_URL=… pytest libs/sales_common/tests -q`.

## 2. Agents

- [x] 2.1 Discovery: `get_company_profile` and `check_customer_state` publish `returning_customer_context` and restore `offer_context`/`serviceability_context`; the prompt acknowledges by status. Verify: `pytest DiscoveryAgent/tests -q` (pg).
- [x] 2.2 Serviceability: the callback stores checks in `serviceability_checks`. Verify: `pytest ServiceabilityAgent/tests -q`.
- [x] 2.3 Offer: `quote_not_saved` on persistence failure; prompt rules (no invented reasons; restored quote). Verify: `pytest OfferManagement/tests -q` (pg) with a failure test.
- [x] 2.4 `sales_common.context`: add `returning_customer_context` to JOURNEY_KEYS. Verify: context tests.

## 3. Gateway

- [x] 3.1 Handoff: skip for unacknowledged returning customers; set `returning_acknowledged_customer`. Verify: `pytest SuperAgent/tests -q`.
- [x] 3.2 Suggestions: address topic fix, confirm-location topic, `returning_active` stage. Verify: `pytest SuperAgent/tests/test_suggestions.py -q`.

## 4. Telemetry

- [x] 4.1 `TelemetryFlushPlugin` in `create_a2a_app`; export-failure and flush-timeout logging; 5000 ms default. Verify: `pytest libs/sales_common/tests -q`; local OTLP sink repro.

## 5. Docs and deploy

- [x] 5.1 BASELINE, `db/README.md`, `.env.example`, `DiscoveryAgent/AGENTS.md`. Verify: `pytest tests/test_baseline_doc.py -q`.
- [x] 5.2 Deploy (migration job runs), then confirm agent spans in Langfuse after a turn. Verify: Langfuse observations from agent services with the new release. Done: deployed 2026-11-27 (all 13 services, migration job); Langfuse v2 observations 2026-11-27/28 (environment `gcp`, 273) include agent-service spans `invocation [payment_agent]`, `invocation [service_fulfillment_agent]`, `invocation [greeting_agent]` and their tool spans (`create_order`, `get_payment_methods`, `check_availability`, …).
- [x] 5.3 Golden evals: skipped by user decision (no billed Gemini requests).
