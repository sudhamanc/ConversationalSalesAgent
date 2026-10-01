# Tasks: Golden-Dataset Agent Eval Suite

## 1. Framework (evals/)

- [x] 1.1 `evals/conftest.py` (RUN_EVALS gate, `eval` marker, EVAL_DATABASE_URL), `evals/golden_io.py`, `evals/metrics.py` (`golden_trajectory_v1`), `evals/trace.py`; verified: `pytest evals -q` without RUN_EVALS runs 58 offline tests and skips all live ones
- [x] 1.2 `evals/test_golden_valid.py` (EvalSet parse, set ids, manifest coverage, reviewed completeness, tool/parameter names, journey agents/events, router inputs/targets, seed hashes, configs); verified it passes on the reviewed goldens
- [x] 1.3 `evals/record_golden.py` (`--snapshot-tools`, recording, `--refresh`, `--dry-run`, per-case save) and `evals/review.py`; verified: snapshot wrote 73 tools; an interrupted recording (402 billing) kept progress; approve refuses unrecorded cases

## 2. Golden datasets

- [x] 2.1 Agent goldens for all 10 agents (52 cases, Scenarios.md IDs, stable tool arguments from seed data, rubrics)
- [x] 2.2 Router golden (58 cases: every agent, rules 1-4, follow-ups, allowed alternatives)
- [x] 2.3 Journey goldens (E2E 1+5, 2, 3, 4, 6 in the current cart → order → scheduling → payment flow)
- [x] 2.4 Recorded with real Gemini and reviewed case by case on 2026-09-30: 106 of 115 approved (44 agent, 58 router, 4 journeys). Four goldens were corrected where the agent's behavior was right and the golden too strict (po-box, non-existent product, declines-pricing, invalid-product quote) and s2's rubric was fixed to the real 5 Gbps coverage at 21201. 9 cases stay pending because the agent misbehaves (see Follow-ups); they are skipped until fixed and re-reviewed

## 3. Runners

- [x] 3.1 `evals/test_agents.py` + per-agent `test_config.json` (judge `gemini-3-flash-preview`; ADK's `gemini-2.5-flash` default returns 404 for this key); verified live: `scripts/eval.sh --only serviceability` passed 6/6 with golden_trajectory_v1, final_response_match_v2, rubric quality and hallucinations all 1.0
- [x] 3.2 `evals/test_router.py` (accuracy, rule accuracy, schema, `MAX_TOKENS` guard, confusion table; router evaluated as an identical `mode="chat"` copy because ADK rejects `single_turn` as root); verified live: 57/58 correct with the final labels (98.3%), rule cases 100%; with the old router config (256 tokens, default thinking) accuracy fell to 39.7% with `MAX_TOKENS` failures, so the eval catches that regression
- [x] 3.3 Client helpers moved to `scripts/e2e_client.py`; `evals/test_journeys.py` (session trace → Invocations → ADK evaluators, `EVAL_RECORD=1`); verified live: `scripts/eval.sh --only journeys --record` drove all 5 journeys through the real stack and the stored sessions converted to per-turn agents, tool calls and replies used for review

## 4. Script

- [x] 4.1 `scripts/eval.sh` (dependency install, csa_eval create + reset per run, tool-service reuse, journey stack lifecycle, junit summary); verified: guards, a scored agent run and a journey recording run; the dev database is never targeted (EVAL_DATABASE_URL must differ, checked)

## 5. Docs

- [x] 5.1 `evals/README.md`, README (Tests → Evals, project tree), AGENTS.md, CLAUDE.md, docs/agent-service-guide.md, Scenarios.md, `.gitignore`

## Follow-ups (agent defects found by the goldens; separate changes)

- FAQ agent has no knowledge source and invents policies (month-to-month plans, self-install kits, support hours): 3.2, 3.3, 3.4 pending
- Product agent does not decline competitor comparisons (6.10)
- Order agent asks for a cancellation reason instead of checking that ORD-20260427-065 is already fulfilled (9.11)
- Payment `get_payment_history` returns generated sample transactions instead of the `payments` table (8.6)
- Payment and fulfillment agents do not know today's date (payment plan dated May 2025, reschedule offers May 2026): 8.5, 10.6
- Discovery asks for a suite number instead of registering a company with a complete address, so the serviceability handoff never runs (E2E-4)
- Router sends "We're Crane.io at 123 Main St, Philadelphia PA 19103" to serviceability instead of discovery (1.1)
- Scored journey baseline (`scripts/eval.sh --only journeys`) not yet run
