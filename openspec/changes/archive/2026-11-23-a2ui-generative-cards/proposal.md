# Proposal: A2UI Generative Cards in the Sales Chat

## Why

Structured results in the chat are drawn by bespoke React cards. Only the quote card is fed by data (`structured_card`); the serviceability and product cards are recovered by regex from the reply text (`MessageBubble.jsx` `parse*`), so they break whenever an agent rewords its reply, and none of them is interactive. A2UI 1.0 is an open, declarative format for agent-built UI, and CopilotKit ships a renderer with a standard catalog of 69 components (Card, Column, Row, Text, Table, Button, Chart, …). Emitting A2UI from the tool results the gateway already sees gives the chat data-driven, interactive cards without parsing prose, and it puts the project on a standard UI format that agents can later write themselves.

## What Changes

- **Gateway** (`SuperAgent/server/api/a2ui.py`, new): pure builders turn remote tool results into A2UI 1.0 operations (`createSurface` with components + data model) using only components of CopilotKit's standard catalog:
  - quote (`generate_offer_quote`, `find_best_bundle_offer`, `get_quote_details`)
  - serviceability (`check_service_availability`, MCP result)
  - products (`list_available_products`, `search_products_by_criteria`, `compare_products`, MCP results; no prices)
- **SSE**: `EventMapper` emits a new additive event `a2ui {surface_id, tool, author, operations}` next to the existing events. `A2UI_ENABLED` (default `true`) turns it off.
- **Actions**: every Button calls the client function `sendChatMessage` with a gateway-authored, customer-voice `message`; the click sends that message as the customer's next turn.
- **UI** (`SuperAgent/client`): `@copilotkit/react-core@1.85.0` + `zod@3.25.76`. A `CopilotKitProvider` with `generativeUI={{ ui: salesUI, theme }}` (`salesUI` = the standard catalog `standardUI` plus the `sendChatMessage` function) wraps the app; `A2UISurface` ingests the operations into the generative UI runtime and renders them in the assistant message, themed with `--a2ui-*` variables. A message with an A2UI surface does not also render the legacy card for it.
- **Catalog export**: `SuperAgent/client/scripts/export_a2ui_catalog.mjs` writes `SuperAgent/server/a2ui/catalog.json` with `exportA2UICatalog`; gateway tests validate every builder against it.

## Capabilities

### New Capabilities

- `generative-ui`: A2UI surfaces built from tool results, rendered in the chat with the standard catalog, with customer-voice actions.

### Modified Capabilities

- `conversation-orchestration`: the streaming chat contract gains the `a2ui` event type.

## Non-goals

- No CopilotKit runtime, `BuiltInAgent`, `/api/copilotkit` route or `CopilotChat`: replies still come only from the ADK gateway and its A2A agents.
- No LLM-authored A2UI: agents' prompts, tools and routing do not change, so golden evals are unaffected. (Exporting the catalog prepares for that later.)
- No cart/order surface: the cart side panel already shows the cart live.
- Legacy cards and their text parsers stay as the fallback for turns without a matching tool result.

## Impact

- **BASELINE.md sections:** §5 Gateway (SSE event list, config).
- **Agents / MCP services / data:** none.
- **Gateway:** `server/api/a2ui.py` (new), `server/api/sse.py`, `server/a2ui/catalog.json` (new, generated), `super_agent/config.py`.
- **UI:** `package.json`, `src/main.jsx`, `src/a2ui/*` (new), `src/components/A2UISurface.jsx` (new), `src/components/MessageBubble.jsx`, `src/contexts/ChatContext.jsx`, `src/utils/api.js`.
- **Scripts:** `SuperAgent/client/scripts/export_a2ui_catalog.mjs` (new), `postcss.config.js` (Tailwind on app CSS only).
- **Config:** `A2UI_ENABLED` in `.env.example` and the SuperAgent/README.md table.
- **Docs:** `openspec/BASELINE.md`, `SuperAgent/README.md`, `SuperAgent/client/AGENTS.md`.
