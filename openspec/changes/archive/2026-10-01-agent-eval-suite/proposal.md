# Proposal: Golden-Dataset Agent Eval Suite

## Why

Every existing test replaces Gemini with a scripted model (`sales_common.testing.ScriptLlm`, `tests/integration/fake_llm`). The tests prove that tools, A2A, MCP and SSE work, but nothing measures what the real model does:
- whether it calls the right tools with the right arguments
- whether its replies stay grounded in tool output
- whether the router picks the right agent
- whether a full sales journey completes

The Gemini 3 router truncation bug (fixed in `local-dev-reliability`) passed every test for exactly this reason.

## What Changes

- **Golden datasets** under `evals/golden/` in ADK `EvalSet` format: curated, human-reviewed cases with the expected trajectory (tool calls with arguments, answering agents) and a reference response per turn. `MANIFEST.json` tracks dataset version, review status, scenario IDs, volatile arguments and seed-file hashes.
- **Three eval tiers**, each scoring trajectory and response:
  - **Agents:** all 10, in-process via `google.adk.evaluation.AgentEvaluator`.
  - **Router:** `route_intent` against labeled routing inputs.
  - **Journeys:** E2E scenarios through the gateway over HTTP/SSE. The trace is read from the gateway session and scored with ADK evaluators.
- **`evals/record_golden.py`** records draft goldens from the real model for human review. **`evals/test_golden_valid.py`** validates goldens with no LLM.
- **`scripts/eval.sh`** runs selected tiers against an isolated `csa_eval` database reset to seed data.
- `scripts/e2e_test.py` client helpers move into an importable module.

## Capabilities

### New Capabilities

- `agent-evaluation`: golden datasets and the eval runners that score trajectory and response for agents, router and journeys.

### Modified Capabilities

None.

## Non-goals

- CI or nightly scheduled eval runs; a GCP eval job.
- Load or latency benchmarking.
- Changing agent prompts or behavior. Gaps the evals find are fixed in separate changes.
- Synthetic user-simulator conversations (`conversation_scenario`). Goldens are static conversations.

## Impact

- **Agents / MCP services / data:** no runtime change. Evals read agents through their existing `root_agent` exports and use a separate `csa_eval` database.
- **Gateway:** none. Journeys use the existing `DEBUG=true` `/api/debug/session` endpoint and the ADK session store.
- **Scripts:** new `scripts/eval.sh`; `scripts/e2e_test.py` imports shared client helpers.
- **Cost:** live runs call Gemini (agents plus LLM judges) and need a billed key. The free tier (20 requests/day) cannot run the suite.
- **Docs:** `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/agent-service-guide.md`, `Scenarios.md`, new `evals/README.md`.
