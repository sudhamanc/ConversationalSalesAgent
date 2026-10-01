# Proposal: Project Baseline Spec

## Why

Every coding session re-discovered the system from code: agent ports, tool names and arguments, which journey context each agent writes, handoff rules, seed data, scripts. That was slow and error-prone (stale docs, wrong guesses). Separately, six implemented OpenSpec changes were never archived, so `openspec/specs/` (the source of truth for current behavior) was empty.

## What Changes

- **`openspec/BASELINE.md`**: one authoritative system map for future sessions. It covers:
  - every agent: package, port, tools, context written and read, tables owned, prompt, tests, golden set
  - tool services and gateway: workflow nodes, router, handoff rules, API, SSE events
  - the journey-context contract
  - data and seed facts
  - commands
  - change recipes
  - capability-spec index
  - known defects
- **Archive the implemented changes in order:** `a2a-agent-services`, `adk2-workflow-orchestration`, `catalog-serviceability-mcp`, `multi-service-scripts`, `local-dev-reliability`, `agent-eval-suite`, then this one. Their delta specs merge into `openspec/specs/<capability>/spec.md`. `mcp-remaining-domains` stays open (planned).
- **`tests/test_baseline_doc.py`** (offline) fails when BASELINE.md drifts from `scripts/services.conf` (every service and port) or from `evals/golden/tool_schemas.json` (every agent tool).
- **CLAUDE.md, AGENTS.md and `openspec/config.yaml`** make BASELINE.md the first read and require every change to update it.

## Capabilities

### New Capabilities

- `project-baseline`: the maintained system map and the rule that changes keep it current.

### Modified Capabilities

None.

## Non-goals

- Rewriting component READMEs or AGENTS.md (BASELINE.md links to them for depth).
- Fixing the agent defects found by the golden evals (listed under Known issues; separate changes).
- Implementing `mcp-remaining-domains`.

## Impact

- **Docs:** new `openspec/BASELINE.md`; CLAUDE.md, AGENTS.md, `openspec/config.yaml`.
- **Specs:** `openspec/specs/*` populated by archiving; changes move to `openspec/changes/archive/`.
- **Tests:** new offline `tests/test_baseline_doc.py`.
- **Agents / services / data:** none.
