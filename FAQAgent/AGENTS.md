# FAQAgent - agent notes

Follows `docs/agent-service-guide.md` (ADK 2.x + A2A + PostgreSQL).

- Agent name: `faq_agent` (hardcoded; the gateway routes by it). Default port 8210.
- `faq_agent/prompts.py`: domain prompt, used as `static_instruction`; `instruction` is the shared `JOURNEY_CONTEXT_INSTRUCTION`.
- One MCP tool, `search_faq` (catalog service at `CATALOG_MCP_URL`, `tool_filter=("search_faq",)`), temperature 0.2. The prompt requires calling it before answering and stating only facts from the passages. FAQ content lives in `services/catalog/data/faq_docs/*.md` (edit there, not in the prompt). No `transfer_to_agent` instructions in the prompt: the orchestrator routes the next turn.
- `faq_agent/server.py`: `create_a2a_app(root_agent)` (DB-backed sessions, `/healthz`).
- Tests use `sales_common.testing.ScriptLlm`; no API key needed.
