# Proposal: ADK 2.x Workflow Orchestration

## Why

The system runs on ADK 1.x with an LLM-only router, three `after_agent_callback` handoff hacks, a synthetic server-side "Proceed to payment" re-run, and in-memory sessions that are lost on every restart. ADK 2.x (2.10.0) adds a graph Workflow runtime, `App`-level context compaction and model context caching, database-backed sessions, and a unified `Context`. These let routing and handoffs be deterministic and conversation state durable. They are also prerequisites for splitting agents into A2A services (change `a2a-agent-services`).

## What Changes

- **BREAKING:** Upgrade every Python package from `google-adk~=1.20` to `google-adk[a2a,mcp,db]==2.10.0` (plus `asyncpg`, `greenlet`).
- Replace the root `super_sales_agent` LlmAgent coordinator with an ADK 2.x **`Workflow` graph** (`sales_journey`). The graph is composed of custom workflow nodes (ADK 2.0's successor to "custom template workflows"):
  - `prepare_turn`: loads shared context and memory, and builds the router input
  - `route_intent`: an LlmAgent with a structured `RouteDecision` output
  - `dispatch`: a routing node
  - one node per domain agent
  - `HandoffPolicyNode`: deterministic Discovery→Serviceability and Scheduling→Payment chaining
- **Removed:** the three `after_agent_callback` handoffs in `SuperAgent/super_agent/sub_agents/*` and the synthetic payment re-run in `server/api/chat.py`.
- Wrap the workflow in an ADK **`App`** with `EventsCompactionConfig` (context compression), `ContextCacheConfig` (model context caching), and plugins (shared-context bridge, logging).
- Replace `InMemorySessionService` with **`DatabaseSessionService`** on PostgreSQL. Sessions survive restarts and scale across instances.
- Add long-term **Memory**: a PostgreSQL-backed `BaseMemoryService` implementation (ADK core ships none for SQL). Sessions are saved to memory after each turn, and relevant memories are injected into routing context.
- Use ADK **State** scopes deliberately:
  - session keys for the journey contexts (`customer_context`, `serviceability_context`, `offer_context`, `order_context`, `payment_context`)
  - `user:` for a returning browser's profile
  - `temp:` for per-turn values
- Use **Events** as the streaming contract: the SSE API maps ADK events (text, `function_response`, `state_delta`) to the existing UI event types, de-duplicating repeated final texts.
- Use **conversational context** features: instruction templating from state (`{customer_context?}`), `static_instruction` for cache-friendly prompts, and a forwarded recent-transcript for agents that do not see other agents' turns.

## Capabilities

### New Capabilities

- `conversation-orchestration`: per-turn intent routing, deterministic agent handoffs, and event streaming to the chat UI.
- `conversation-state-memory`: durable sessions, scoped shared state, long-term memory, context compaction and model context caching.

### Modified Capabilities

None (no baseline specs exist in `openspec/specs/`).

## Non-goals

- Changing the React UI's visual design or SSE event names.
- Replacing Gemini as the model provider.
- Vertex AI Agent Engine / Memory Bank adoption (possible later; PostgreSQL keeps local dev and Cloud Run symmetric).
- Fixing domain-agent business-logic bugs unrelated to orchestration. These are listed in the design document's risks section.

## Impact

- **Code:**
  - `SuperAgent/super_agent/` (rewritten as the gateway workflow)
  - `SuperAgent/server/` (runner, SSE mapping, sessions, auth tokens)
  - every agent's `pyproject.toml` / requirements
- **Dependencies:** google-adk 2.10.0, a2a-sdk 1.x, mcp 2.x, SQLAlchemy 2.1, asyncpg, greenlet, psycopg 3.
- **Data:** new ADK session tables and a `memories` table in PostgreSQL.
- **Docs:** `AGENTS.md`, `CLAUDE.md`, `SuperAgent/README.md`, `SuperAgent/super_agent/sub_agents/{AGENTS,CLAUDE}.md`, the architecture brief.
- **Depends on:** `a2a-agent-services` (domain nodes are remote A2A agents; PostgreSQL provisioning).
