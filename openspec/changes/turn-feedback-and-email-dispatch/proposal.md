# Proposal: Turn Feedback and Email Dispatch

Builds on `a2ui-generative-cards` and the open `guided-checkout` change.

## Why

A live journey on Cloud Run (2026-11-27, release `4717fb9`) showed three problems:

1. **Cards stay open after the customer acts.** After "Save contact details", a quote choice or an installation slot, the card looked unchanged: every button stayed clickable and the gateway's default (the first quote button, the earliest slot) stayed blue even when the customer picked another one. Nothing on the card said the step was done.
2. **Turns are slow and look stalled.** `/api/chat` took 15–96 s per turn. Cloud Run logs show a cold start on almost every step, because each step reaches a different scaled-to-zero service for the first time: discovery 16 s, serviceability agent 38 s (plus its MCP service 17 s), product 62 s, catalog 18 s, offer 17 s, order 18 s, fulfillment 15 s, payment 19 s. Warm turns still take 15–21 s (router, agent, sometimes a handoff, then suggestions). A2UI is not the cause: surfaces are built by pure Python functions in the gateway. Meanwhile the UI shows three dots only until the first text token, then nothing while a handoff agent or the suggestions are still running.
3. **No emails were sent.** SMTP is configured on `csa-agent-communication` (`SMTP_ENABLED=true`, secrets present), but the notification outbox is only drained by that service's background loop. On Cloud Run the service scales to zero and gets CPU only while it serves a request; nothing calls it during a normal checkout (quote, order, installation and payment emails are queued by other services). Its logs show it started at the 2026-11-24 deploy, stopped 15 minutes later and never ran again, so every queued email is still `pending`.

## What Changes

- **Completed card actions (UI + gateway).** Every gateway-built Button carries its `surface` id and `button` id in the `sendChatMessage` args. On a click the UI marks that surface as acted: the chosen button becomes the highlighted one with a check icon, every other button and input on that card is disabled, and a status badge says what happened ("Saved", "Selected: …"). While the turn runs the chosen button shows a loading state; if the turn fails the card is restored so the customer can retry. The change is applied by appending an A2UI `updateComponents` operation for the surface, so the CopilotKit runtime updates it in place.
- **Turn progress (gateway + UI).** A new additive SSE event `progress` `{stage: routing|agent|suggestions|retrying, agent?}`: `routing` when the turn starts, `agent` each time the workflow routes or hands off to an agent, `retrying` before a retry, `suggestions` before suggestions are generated. The UI replaces the three-dot indicator with a status line shown for the whole turn: what is happening ("Understanding your request…", "Checking coverage…", "Preparing suggested replies…") and the elapsed seconds; after 10 s on one step it adds "Starting a service can take up to a minute the first time."
- **Warm-up at session start (gateway + agents).** `POST /api/session` starts, in the background, one request to every agent service (`GET /.well-known/agent-card.json`; `POST /dispatch` for customer communication; not `/healthz`, which Cloud Run's front end answers itself with 404), at most once per `WARMUP_INTERVAL_S` (default 300) per gateway process; `WARMUP_ENABLED` (default `true`). Each agent service with MCP dependencies sends a `GET` to their MCP endpoint when it starts. The customer's first minute of reading and typing then hides the cold starts.
- **Email dispatch on demand (communication service + gateway).** The customer communication service serves `POST /dispatch` (no model): it delivers due pending notifications within the request and returns the counts. The gateway calls it in the background as soon as a tool result in the turn reports a queued notification (`notification_id`, `email_notification_id`, `notification_queued`, `email_confirmation_queued` or `notification_sent`), at most one call in flight per gateway process; a later trigger while one is running causes one more call after it. The background loop stays for local and compose runs.

- **Findings of the first cloud run (same change).** (a) A card click while the reply that showed the card is still streaming is queued and sent when that reply ends, instead of being dropped (the contact card arrives with `add_new_company` and the turn continues with the coverage handoff; a dropped Save made the order step ask for the contact again). (b) The activity panel shows each notification's delivery status: producer tools return the `notification_id`, and before `done` the gateway reports the status of the turn's notifications once its dispatch request has run (bounded wait `NOTIFY_STATUS_WAIT_S`, default 5). (c) A step completed without a click closes its open cards: an order placed in the same turn as the cart leaves no live "Place my order" button. (d) The installation email shows the time window ("1 PM–5 PM (afternoon)"), not "PM".
- **Contact before coverage (second cloud run).** After a new company is registered without a contact email, the gateway waits for the contact card before the automatic coverage check (`registration_waiting_for_contact`), so the customer is not asked to save the contact after the coverage result has already arrived.
- **Provisioning after payment (third cloud run).** A successful payment for an order with a scheduled installation hands off to service fulfillment in the same turn (provision equipment, dispatch technician); before, the customer had to ask another question to start it.

## Capabilities

### New Capabilities
- none

### Modified Capabilities
- `generative-ui`: acted surfaces show completion; button args identify their surface and button; clicks during a streaming reply are queued; completed steps close their surfaces.
- `conversation-orchestration`: `progress` SSE event; warm-up at session start; email dispatch trigger; notification delivery status reported to the UI; discovery-to-serviceability handoff waits for the registration contact; payment-to-fulfillment handoff.
- `sales-data-store`: notification outbox is drained on demand, not only by a background loop.
- `agent-services`: communication service `POST /dispatch`; agents warm their MCP dependencies at startup; producer tools return the notification id; installation email shows the time window.

## Non-goals

- No `min-instances` or always-on CPU for the services (cost); warm-up only hides cold starts inside a session.
- No change to model calls, prompts or routing; golden evals are not re-run (billed), per project rule.
- No retry or status reporting of emails to the browser beyond the existing activity panel.
- Only order placement and installation booking close cards that were not clicked; other steps completed by typing leave their cards unchanged.

## Impact

- **BASELINE.md sections:** §3 (communication service `POST /dispatch`), §5 (SSE `progress` event, `sendChatMessage` args, warm-up, dispatch trigger, config `WARMUP_ENABLED`/`WARMUP_INTERVAL_S`), §10 none.
- **Agents:** customer communication (`server.py` extra route); all agents (startup warm-up of MCP deps in `sales_common.a2a_server`).
- **Gateway:** `server/api/a2ui.py`, `server/api/sse.py`, `server/api/chat.py`, `server/api/session.py`, new `server/api/background.py`, `super_agent/config.py`.
- **Shared lib:** `sales_common/a2a_server.py`.
- **UI:** `src/a2ui/salesUI.js` (function args), new `src/a2ui/actedSurface.js`, `src/contexts/ChatContext.jsx`, `src/components/A2UISurface.jsx`, `src/components/ChatWindow.jsx`, new `src/components/TurnProgress.jsx` (replaces `TypingIndicator.jsx`), `src/utils/api.js`; `server/a2ui/catalog.json` re-exported.
- **Data:** none.
- **Scripts:** none (`deploy_cloud.sh` already grants the gateway `run.invoker` on every agent, including communication).
- **Docs:** BASELINE, README (A2UI actions, SSE contract), SuperAgent/README.md (config), client AGENTS.md, CustomerCommunicationAgent docs, `.env.example`.
