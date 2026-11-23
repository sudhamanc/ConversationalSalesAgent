# Tasks: A2UI Generative Cards in the Sales Chat

## 1. UI dependencies and catalog (`SuperAgent/client`)

- [x] 1.1 Install `@copilotkit/react-core@1.85.0`, `zod@3.25.76`, plus `@ag-ui/client@1.0.2` and `rxjs@7.8.1` for `InertAgent` (all exact). `postcss.config.js` runs Tailwind 3 on app CSS only (CopilotKit's stylesheet is prebuilt with Tailwind 4). Verify: `package.json` pins them; `npm run build` ✓ (app classes such as `bg-primary-600` still compiled).
- [x] 1.2 Add `SuperAgent/client/scripts/export_a2ui_catalog.mjs` (`npm run export:a2ui-catalog`; it lives in the client so it resolves CopilotKit) writing `exportA2UICatalog(salesUI)` to `SuperAgent/server/a2ui/catalog.json`. Verify: 69 components (Card, Column, Row, Text, Table, Button, …) and 17 functions including `sendChatMessage`; re-running produces no diff.

## 2. Gateway (`SuperAgent/server`, `SuperAgent/super_agent`)

- [x] 2.1 Add `api/a2ui.py` builders (quote, serviceability, products, compare) and `build_surface(tool, response)`. Verify: `pytest SuperAgent/tests/test_a2ui.py -q` (22 passed) checks component names, props, enum values and required props against `catalog.json`, `sendChatMessage` messages on every Button with no placeholders, no prices on product surfaces, `None` for failures.
- [x] 2.2 `A2UI_ENABLED` in `super_agent/config.py`; `EventMapper(a2ui_enabled=…)` emits `a2ui` events once per surface per turn; `chat.py` passes the setting. Verify: `pytest SuperAgent/tests -q` (113 passed, 7 skipped; new `test_sse.py` cases for emitted, repeated, disabled and MCP results).

## 3. UI rendering (`SuperAgent/client`)

- [x] 3.1 `src/a2ui/salesUI.js`, `theme.js`, `InertAgent.js`, `GenerativeUIProvider.jsx` (inspector off); provider in `main.jsx`. Verify: `npm run build` ✓; headless Chrome load shows no CopilotKit errors (only the pre-existing `/favicon.ico` 404, also on main).
- [x] 3.2 `api.js` `a2ui` → `onA2UI`; `ChatContext` stores `a2uiSurfaces` on the assistant message and mounts the `sendChatMessage` handler. Verify: headless Chrome against a mock gateway streaming real `build_surface` output: clicking "Show plans" and "Quote Fiber 1 Gbps" sent "Show me the plans available at my address" and "I'd like a quote for Fiber 1 Gbps" to `POST /api/chat`.
- [x] 3.3 `A2UISurface.jsx` + `MessageBubble.jsx` (surfaces under the reply, legacy card skipped for the same kind). Verify: the same run rendered the serviceability → products → quote surfaces (3 surfaces, themed), `QuoteCard` absent, no generative UI errors in the console. A live journey against the real agents was not run (billed Gemini).

## 4. Docs

- [x] 4.1 `openspec/BASELINE.md` §5, `SuperAgent/README.md` (SSE + env tables), `SuperAgent/client/AGENTS.md` (stack, events, A2UI section), `.env.example`. Verify: `pytest tests/test_baseline_doc.py -q` (23 passed).

## 5. Evals

- [x] 5.1 Golden evals not run: no agent prompt, tool, model or routing change (and no billed Gemini runs by user decision). Verify: `git diff --stat` touches no `*/prompts.py`, `tools/`, `super_agent/prompts.py` or `workflow.py`.
