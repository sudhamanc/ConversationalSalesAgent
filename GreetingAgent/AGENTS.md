# GreetingAgent - agent notes

Follows the README "Agent Service Guide" (ADK 2.x + A2A + PostgreSQL).

- Agent name: `greeting_agent` (hardcoded; the gateway routes by it). Default port 8209.
- `greeting_agent/prompts.py`: domain prompt, used as `static_instruction`; `instruction` is the shared `JOURNEY_CONTEXT_INSTRUCTION`.
- No tools, temperature 0.7. No `transfer_to_agent` instructions in the prompt: the orchestrator routes the next turn.
- `greeting_agent/server.py`: `create_a2a_app(root_agent)` (DB-backed sessions, `/healthz`).
- Tests use `sales_common.testing.ScriptLlm`; no API key needed.
