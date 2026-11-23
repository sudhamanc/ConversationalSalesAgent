# Proposal: Guided Checkout (secure payment form, automatic scheduling, consistent A2UI)

Depends on `a2ui-generative-cards` (A2UI surfaces from tool results).

## Why

A live journey (2026-11-23, "Rewards inc", 314 Main Street, Philadelphia) showed:
1. Replies repeat what the A2UI card already shows (serviceability listed switch ids, OLT ports and splice points; the plans reply listed all 16 products).
2. Many steps are still plain text: cart, order, installation slots, scheduling confirmation, payment.
3. Payment failed twice with "An error occurred during processing": Gemini returned `finish_reason: SAFETY` with no output. A reproduction rated the payment agent's reply HARASSMENT MEDIUM and SEXUALLY_EXPLICIT LOW under `BLOCK_LOW_AND_ABOVE`. The prompt told the agent to collect card numbers and CVVs in chat, with full card numbers as examples. With a prompt that never handles card data, all ratings were NEGLIGIBLE.
4. After the order was created the customer had to ask for installation dates, then type a slot back ("November 27 - Morning or Afternoon", ambiguous).
5. Card defects: floats crossing A2A showed as "5000.0 Mbps", "12.0 months", "Qty 1.0"; the plans card listed the whole catalog (HFC/DOCSIS plans at an FTTP-only address); "Accept quote" on the 24-month card did not say which quote, and the order used the latest (36-month) quote.

## What Changes

- **Secure payment entry.** Card and bank details never reach a model:
  - payment service REST `POST /payment-methods` (tokenize + save the masked method, no LLM), proxied by the gateway as `POST /api/payment-methods` (session bearer; `customer_id` from session state, never from the browser).
  - a `SecurePaymentForm` component added to the A2UI catalog (`salesUI`), holding card fields in local component state only, cleared after submit; after saving it sends "I've added my Visa ending 1111. Please use it to pay for my order."
  - the gateway masks card numbers (Luhn), CVVs and bank account numbers typed into chat before the message reaches the router or any agent.
  - payment prompt rewritten: never asks for card data; calls `get_payment_methods` (which shows the payment card) and pays with the chosen saved token.
  - safety default `BLOCK_MEDIUM_AND_ABOVE` (Gemini's default) instead of `BLOCK_LOW_AND_ABOVE`.
- **Automatic scheduling.** New handoff: when `create_order` creates an order this turn and no installation is scheduled, order_agent → service_fulfillment_agent ("show the available installation slots"). Fulfillment calls `check_availability`; the slots card has one button per slot with an exact customer message.
- **More A2UI surfaces** (gateway, deterministic): cart (`add_to_cart`, `remove_from_cart`, `get_cart`), order (`create_order`, `get_order`), installation slots (`check_availability`), installation confirmation (`schedule_installation`), payment methods (`get_payment_methods` + order total from state), payment receipt (`process_payment`), product detail (`get_product_by_id`).
- **Card fixes:** whole numbers shown without ".0"; product lists filtered to the address's `available_products` when serviceability is known; quote buttons name the quote id, and when a customer message names an active quote id of the same customer that differs from `offer_context`, the gateway makes it the current `offer_context`.
- **Concise replies:** a shared `UI_CARDS_INSTRUCTION` (in `JOURNEY_CONTEXT_INSTRUCTION`) tells agents that the chat shows these cards and to reply in one or two sentences without repeating them. Serviceability no longer exposes internal network element details.
- **UI:** suggestion chips are hidden under a message whose card already offers buttons.

## Capabilities

### New Capabilities
- none (extends `generative-ui` from `a2ui-generative-cards`)

### Modified Capabilities
- `generative-ui`: more surfaces, secure payment form, quote selection.
- `conversation-orchestration`: order → fulfillment handoff; payment handoff message; card-number masking of user messages; selected quote restore.
- `agent-services`: payment service REST endpoint for payment methods; concise replies when cards are shown.

## Non-goals

- No real payment processor (tokenization stays simulated).
- No LLM-authored A2UI.
- Golden evals are not re-run or re-recorded (billed); prompt and handoff changes are verified with unit tests and one live journey.

## Impact

- **BASELINE.md sections:** §3 (payment REST endpoint, prompt notes), §5 (handoff rule, masking, `a2ui` surfaces, `/api/payment-methods`), config (safety default).
- **Agents:** payment (prompt, REST route), serviceability (prompt), shared journey instruction (all agents).
- **Gateway:** `server/api/a2ui.py`, `server/api/sse.py`, `server/api/chat.py`, new `server/api/payment_methods.py`, `super_agent/workflow.py`, `super_agent/plugins.py`.
- **Shared lib:** `sales_common/context.py` (instruction), `sales_common/config.py` (safety default), `sales_common/repositories/quotes.py` (load a quote as `offer_context`), `sales_common/a2a_server.py` (`extra_routes`).
- **UI:** `src/a2ui/salesUI.js`, new `src/a2ui/SecurePaymentForm.jsx`, `src/utils/api.js`, `MessageBubble.jsx`.
- **Data:** none (existing `customer_payment_methods`).
- **Docs:** BASELINE, SuperAgent/README.md, client AGENTS.md, PaymentAgent/AGENTS.md, `.env.example`.
