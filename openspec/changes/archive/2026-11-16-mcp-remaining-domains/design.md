# Design: REST + MCP for the Remaining Domain Tools

## Context

Builds on the `services/<domain>/` layering from `catalog-serviceability-mcp`: `core.py` holds the logic, while REST routes and MCP tools are thin wrappers over it. Deferred by user decision.

## Decisions

- **Migration order:** notifications → crm → pricing → orders → payments → fulfillment. Each step removes that domain's SQL from its agent container.
- **Moving tools:** tool modules move with `git mv` from `<Agent>/<pkg>/tools/` to `services/<domain>/<domain>_service/core.py`. The agent keeps only prompts, callbacks, and an `McpToolset`.
- **Journey context:** `_context_update` export stays agent-side. An `after_tool_callback` maps the MCP result to state, as done for serviceability.
- **Idempotency:** payments and orders accept an `Idempotency-Key` header. This is required because ADK 2.x re-runs failed workflow nodes on resume.

## Risks / Trade-offs

- **[More network hops per tool call] → Mitigation:** same-region Cloud Run; stateless JSON-response MCP.
