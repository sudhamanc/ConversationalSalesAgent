# Tasks: Project Baseline Spec

## 1. Baseline document

- [x] 1.1 Write `openspec/BASELINE.md` (agents, services, gateway, context contract, data, commands, recipes, spec index, known issues); verified against `scripts/services.conf`, `evals/golden/tool_schemas.json`, `sales_common/context.py`, `super_agent/workflow.py`, agent `tool_context.state` writes (serviceability via `callbacks.py`), `db/README.md` and seed data

## 2. Drift check

- [x] 2.1 `tests/test_baseline_doc.py` (services, ports, modules from services.conf; tools from tool_schemas.json); verified: 23 pass; removing `get_credit_report` from BASELINE.md fails naming the tool; changing payment's port in services.conf fails naming the service

## 3. Specs

- [x] 3.1 Archived a2a-agent-services, adk2-workflow-orchestration, catalog-serviceability-mcp, multi-service-scripts, local-dev-reliability, agent-eval-suite in that order; `openspec/specs/` now holds agent-evaluation, agent-services, conversation-orchestration, conversation-state-memory, product-catalog-service, sales-data-store, service-operations, serviceability-service; links to the moved change folders repointed to `openspec/changes/archive/`

## 4. Session entry points

- [x] 4.1 CLAUDE.md (READ FIRST, reading order, OpenSpec steps, checklist, context docs), AGENTS.md (reading order, specs location, change table) and `openspec/config.yaml` (context + proposal rule) point to BASELINE.md and require updating it; links verified
