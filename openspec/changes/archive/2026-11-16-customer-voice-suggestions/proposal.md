# Proposal: Customer-Voice Suggested Next Steps

## Why

The "Suggested Next Steps" chips under each assistant reply are clicked by the customer. A click pre-fills the chat input, so a chip becomes the customer's own message. Today many chips are written from the sales rep's side, at every stage of the journey:
- the agent's question repeated back ("Tell me about your company and location")
- back-office actions ("Send order confirmation to customer", "Send a status update to the customer")
- filler ("Continue", "Show me next best step")

There are three causes. The gateway's suggestion prompt never says who is speaking. It sees only the first 400 characters of the reply, so the agent's closing question is usually cut off. And suggestions are keyed only on the answering agent, not on what the journey already knows, so chips re-ask for given details or skip missing ones.

## What Changes

- **Chip contract** (every source, every stage):
  - each chip is a first-person message the customer would send
  - it either *answers* the agent's latest question as a fill-in template with `[placeholders]`, or *requests* the next step of the purchase
  - it never addresses the customer or mentions "the customer"
  - it never asks for information the journey already holds
- **Journey-aware stage playbook** (`SuperAgent/server/api/suggestion_playbook.py`):
  - `journey_stage(state)` derives one stage from the gateway session state, reusing `super_agent.workflow.journey_flags`
  - `PLAYBOOK[stage]` holds customer-voice request chips
  - `REPLY_TEMPLATES` maps what the agent asked for (company, address, needs, contact, date, payment, confirmation) to a fill-in reply chip
- **Gateway suggestions** (`api/suggestions.py`):
  - the prompt states that the chips are the customer's next messages
  - it includes the contract, stage, known and missing facts, and the head and tail of the reply
  - a deterministic validator drops rep-voice and filler chips
  - chip 1 is a reply template whenever the agent asked something
  - chips are topped up from the playbook, so the LLM failing still yields 3 chips
  - `chat.py` reads the session state after the turn and passes it in; `_ACTIVATION_SUGGESTIONS` becomes the playbook's provisioning set
- **UI**:
  - the client fallback (`utils/suggestions.js`) is rewritten in customer voice
  - a click on a template chip selects the first `[placeholder]`; Tab or Enter moves to the next; Send is blocked while any placeholder remains (`utils/placeholders.js`)
  - template chips show a pencil marker

## Capabilities

### Modified Capabilities

- `conversation-orchestration`: adds the requirement that suggestions are customer-voice and journey-aware.

## Non-goals

- No new SSE event type and no payload shape change: `suggestions.data` stays a list of strings.
- No change to routing, handoffs, agents, tools or MCP services.
- Payment details typed into a template are not handled differently from today's typed messages. Masking in traces is unchanged.

## Impact

- **BASELINE.md sections:** §5 Gateway (the `suggestions` event description).
- **Agents / MCP / data / scripts:** none.
- **Gateway:** `server/api/suggestions.py`, `server/api/suggestion_playbook.py` (new), `server/api/chat.py`.
- **UI:** `utils/suggestions.js`, `utils/placeholders.js` (new), `components/ChatInput.jsx`, `components/SuggestionCard.jsx`.
- **Docs:** `SuperAgent/README.md`, `SuperAgent/client/AGENTS.md`, `openspec/BASELINE.md`.
