# Tasks: Guided Checkout

## 1. Shared library (`libs/sales_common`)

- [x] 1.1 `prompts.py`: "Cards in the chat" section in `JOURNEY_CONTEXT_INSTRUCTION` (no braces: it is templated). Verify: all agent suites pass with `TEST_DATABASE_URL` (greeting 3, faq 3, discovery 23, serviceability 11, product 8, offer 13, order 12, payment 33, fulfillment 19, communication 39).
- [x] 1.2 `config.py`: safety default `BLOCK_MEDIUM_AND_ABOVE`; `.env.example`, local `.env`, SuperAgent/README.md and the architecture brief updated. Verify: reproduction call — old prompt at LOW: HARASSMENT MEDIUM, SEXUALLY_EXPLICIT LOW → SAFETY; new prompt: all NEGLIGIBLE.
- [x] 1.3 `repositories/quotes.py`: `OFFER_ID_RE`, `load_offer_context(offer_id, customer_id)` (active quote of that customer only). Verify: live journey — accepting the 24-month card set `offer_context` OFF-02A4CF6C85 (24 months) and the cart used $236.55.
- [x] 1.4 `a2a_server.py`: `extra_routes`. Verify: payment service serves `POST /payment-methods` (live journey saved Visa ending 1111).

## 2. Payment agent (`PaymentAgent`)

- [x] 2.1 Prompt rewrite (no card data in chat; `get_payment_methods` first; pay with the chosen saved token). Verify: `pytest PaymentAgent/tests -q` (33 passed with DB); live journey paid with no SAFETY event.
- [x] 2.2 `payment_agent/rest.py` `POST /payment-methods`. Verify: `tests/test_rest.py` (invalid requests → 400 without echoing numbers, masked response without token, unsaved → 502, DB-backed save).

## 3. Gateway (`SuperAgent`)

- [x] 3.1 `api/payment_methods.py` proxy. Verify: `test_api.py` (customer from session not body, 401/409, 400 passthrough, no token in response).
- [x] 3.2 `chat.py` masking. Verify: `test_card_numbers_are_masked_before_the_workflow`.
- [x] 3.3 `plugins.py` `order_created_order`; `workflow.py` order → fulfillment handoff + graph edge; payment handoff message. Verify: `test_handoff_rules.py`; live journey — slots card in the order-creation turn.
- [x] 3.4 `prepare_turn` quote selection; `EventMapper` emits the selected quote to the quote panel. Verify: `test_handoff_rules.py` quote tests, `test_sse.py::test_selected_quote_updates_the_quote_panel`.
- [x] 3.5 `api/a2ui.py` surfaces (cart, order, slots, scheduled, payment, receipt, product detail), whole numbers, address filter, quote ids in buttons; `EventMapper(state=…)`; payment tokens stripped from all SSE payloads. Verify: `pytest SuperAgent/tests -q` (145 passed with DB).

## 4. UI (`SuperAgent/client`)

- [x] 4.1 `SecurePaymentForm` in `salesUI`; `savePaymentMethod()`; catalog export through Vite SSR (70 components). Verify: `npm run build`; mock and live runs — the card number only reached `/api/payment-methods`, the chat got "I've added my Visa ending 1111…".
- [x] 4.2 Chips hidden under cards with buttons; legacy order/payment cards skipped; stale payment card hidden after a receipt; payment JSON line hidden; token row removed from the activity panel. Verify: `npm run build`; mock run.

## 4b. Quote card follow-up (user feedback 2026-11-23)

- [x] 4b.1 Replace the quote card's "Adjust" button (it only said "I'd like to adjust…", so the agent had to ask) with one button per other contract term and "Add a service"; offer prompt handles these messages without asking first. Verify: `test_a2ui.py::test_quote_offers_the_other_contract_terms`; `pytest OfferManagement/tests -q` (13 passed with DB). Not run live: the Gemini project's prepaid credits were depleted (402 RESOURCE_EXHAUSTED).

## 4c. Contact email (user feedback 2026-11-23: email was never asked; three orders had none)

- [x] 4c.1 Discovery: `customer_context.contact` from `add_new_contact` / `update_contact_info` / contact on file in `get_company_profile`; prompt asks for name and email at registration and saves "My contact details: …" messages. Verify: `pytest DiscoveryAgent/tests -q` (23 passed with DB); `pytest evals -q` (tool schemas unchanged).
- [x] 4c.2 Order: `create_order` defaults the email from the contact and returns `contact_email_required` without one. Verify: `OrderAgent/tests` (14 passed with DB, incl. required-email and contact-default tests).
- [x] 4c.3 Offer and payment default the email from the contact; the payment notification names the masked method instead of the token (it used to contain `tok_…`). Verify: `OfferManagement/tests` 13 passed, `PaymentAgent/tests` 34 passed (with DB).
- [x] 4c.4 Gateway: contact card (registration; `create_order` refusal), `order_waiting_for_contact` flag, discovery → order handoff and graph edge. Verify: `pytest SuperAgent/tests -q` (151 passed with DB); headless browser against the mock: Save disabled until a valid email, click sent "My contact details: name Jane Doe, email jane@crane.io, phone 215-555-0100.".

## 5. Docs and verification

- [x] 5.1 BASELINE §3/§5, SuperAgent/README.md, client AGENTS.md, PaymentAgent/AGENTS.md, ServiceabilityAgent CLAUDE.md/AGENTS.md, `.env.example`. Verify: `pytest tests/test_baseline_doc.py -q` (23 passed).
- [x] 5.2 One live journey (user-approved): new customer Harbor Analytics Inc → plans → quote → 24/36-month quotes → accept 24-month → cart → order (slots shown automatically) → slot click → payment card → secure form → paid. Verify: transcript in the gateway session, screenshots; no SAFETY errors. The product/order prompt shortening and the three UI fixes (stale payment card, token stripping, quote panel) were made after this run and are verified by unit tests and the build only.
- [x] 5.2b README: dedicated "A2UI Generative UI" section (architecture and sequence diagrams, components, surface catalog, wire format, actions, secure payment entry, theming, fallback, adding a surface, testing, limitations) and A2UI folded into the intro, architecture diagram, layers, principles, handoffs, state table, flows, stack, layout, security and limitations; AGENTS.md handoff table and events; `a2ui-generative-cards` archived (spec `generative-ui`). Verify: `openspec validate --specs` (11 passed); `pytest tests/test_baseline_doc.py -q`.
- [x] 5.3 Golden evals: skipped by user decision (no billed Gemini requests). Not re-run (billed): serviceability, product, order, fulfillment and payment goldens and the journeys tier will need `scripts/eval.sh` and re-recording.
