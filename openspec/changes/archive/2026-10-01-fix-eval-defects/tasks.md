# Tasks: Fix Defects Found by the Golden Evals

## 1. FAQ RAG (catalog service + faq agent)

- [x] 1.1 FAQ corpus `services/catalog/data/faq_docs/*.md` (contracts, installation, support, SLAs, billing, cancellation), consistent with pricing, scheduling, payment and expiry rules in code
- [x] 1.2 `rag.py` FAQ collection `faq_knowledge` (heading-only chunks dropped), `search_faq` in core, MCP and REST `GET /api/v1/faq/search`, health status; verified: catalog tests 91 passed, the real embedding model ranks the correct FAQ topic first for all 7 test questions
- [x] 1.3 `faq_agent` with `McpToolset(search_faq)`, grounded prompt, temperature 0.2; services.conf + compose MCP dependency; verified: FAQ tests pass, live recordings call `search_faq` for every question and quote only corpus facts

## 2. Agent fixes

- [x] 2.1 Product prompt: decline competitor comparisons with no tool calls and no product claims; "what products do you offer" lists all products; verified by re-recorded goldens
- [x] 2.2 `cancel_order` guard (`NON_CANCELLABLE_STATUSES`) + order prompt; verified: order tests (fulfilled seed order refused, double cancel refused), golden 9.11
- [x] 2.3 `get_payment_history` from `payments` (+ orders, + saved methods for masked type); `setup_payment_plan` past-date guard; verified: payment tests (seed payment returned, empty-string customer id handled), goldens 8.5/8.6
- [x] 2.4 `current_date` in `import_forwarded_context` + `JOURNEY_CONTEXT_INSTRUCTION`; `check_availability` rejects past dates; date rules in payment and fulfillment prompts; verified: sales_common and fulfillment tests, reschedule golden picks next week's date
- [x] 2.5 Discovery prompt: never ask for suite/unit; register once required fields are known; verified: journey E2E-4 registers and runs the serviceability handoff in one turn
- [x] 2.6 Router prompt: company introductions → discovery_agent; verified: router eval 58/58

## 2b. Defects found while running the full suite

- [x] 2.7 Catalog service segfault: two sentence-transformers models on Apple's MPS backend encoding from several threads crashed the process (crash report: SIGSEGV in `at::native::mps`). Fix: one shared embedder on CPU (`EMBEDDING_DEVICE`, default `cpu`) with a lock around `encode`, warm-up of both corpora in one thread; verified by `test_concurrent_search_on_shared_embedder` (40 concurrent searches)
- [x] 2.8 Model calls had no request timeout, so a dead dependency hung a turn forever: `generate_config` sets `HttpOptions.timeout` (`MODEL_REQUEST_TIMEOUT_MS`, default 120000) with the existing retries
- [x] 2.9 Greeting prompt's own example claimed "the nation's leading telecommunications provider": example fixed, rule added (no size/ranking/market-position claims), greeting goldens re-recorded with a rubric for it

## 3. Verification

- [x] 3.1 All unit/agent/gateway/service tests pass with a test database (also fixed: serviceability zone ordering independent of DB collation)
- [x] 3.2 9 pending goldens re-recorded, reviewed and approved (115/115); eval-suite fixes found during full runs: unverifiable rubrics removed, offer cases isolated per customer, date-dependent replies skip exact match, call ids kept for journey judges, DB reset before journeys, eval.sh empty-array crash and masked exit status, `--rerecord`, `journeys:<name>`. Scored: router 58/58; customer_communication 4/4, discovery 6/6, faq 5/5 on every metric; journey trajectories correct for all 15 turns of s1–s4 (s6 not run)

## 4. Docs

- [x] 4.1 BASELINE.md (bug list removed, FAQ RAG, new behaviors), README (Evals section), evals/README, catalog README, FAQ agent docs, architecture brief

## Follow-ups

- Complete the scored baseline (`scripts/eval.sh`) for greeting (judges), offer_management, order, payment, product, serviceability, service_fulfillment and the journey response metrics: the last run stopped on Gemini 402 (prepaid credits depleted). Unit tests and re-recorded, reviewed goldens cover the fixes in the meantime.
