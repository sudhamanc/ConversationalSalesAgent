# generative-ui Specification

## Purpose
Interactive UI in the sales chat: the gateway builds A2UI 1.0 surfaces deterministically from remote tool results (no model writes UI), streams them as SSE `a2ui` events, and the React client renders them inside the conversation with CopilotKit's standard catalog. Surface buttons send customer-voice chat messages. Introduced by `a2ui-generative-cards`; extended by `guided-checkout`.
## Requirements
### Requirement: A2UI surfaces from tool results

When `A2UI_ENABLED` is not `false`, the gateway SHALL emit one SSE event `{"type": "a2ui", "surface_id", "tool", "author", "operations"}` for each successful remote result of a quote tool (`generate_offer_quote`, `find_best_bundle_offer`, `get_quote_details` with an `offer_id`), of `check_service_availability`, and of a product listing tool (`list_available_products`, `search_products_by_criteria` with at least one product, `compare_products`). `operations` SHALL be A2UI 1.0 operations (`version` `"1.0"`) whose first operation is `createSurface` with a component whose id is `root`. Every component SHALL be a component of CopilotKit's standard catalog with its required props. All values SHALL come from the tool result; the gateway SHALL NOT call a model to build a surface. Product surfaces SHALL NOT contain prices. A failed or unrecognized tool result SHALL produce no `a2ui` event. When `A2UI_ENABLED` is `false`, no `a2ui` event SHALL be emitted and the other events are unchanged.

#### Scenario: Quote surface
- **WHEN** `generate_offer_quote` returns `offer_id` `OFF-1` with two items and `monthly_total` 450.0
- **THEN** the stream contains an `a2ui` event with `tool` `generate_offer_quote` whose surface shows both items and the monthly total

#### Scenario: Serviceability from an MCP result
- **WHEN** `check_service_availability` returns an MCP result whose `structuredContent` has `serviceable: true`, `infrastructure_type` `FTTP` and `max_speed_mbps` 5000
- **THEN** the stream contains an `a2ui` event whose surface states that service is available with FTTP up to 5000 Mbps

#### Scenario: Product surface without prices
- **WHEN** `list_available_products` returns three products
- **THEN** the `a2ui` surface lists the three products and contains no price

#### Scenario: Disabled
- **WHEN** `A2UI_ENABLED=false` and a quote is generated
- **THEN** the stream contains the `structured_card` event and no `a2ui` event

### Requirement: Surface actions send customer messages

Every Button in a gateway-built surface SHALL bind its action to the client function `sendChatMessage` with a non-empty, first-person customer `message` authored by the gateway, plus `surface` (the surface id) and `button` (the Button's component id). When the customer clicks the button, the UI SHALL send that message as the customer's next chat message, exactly as if typed. A click while a reply is still streaming (a card can arrive before its turn ends, for example before a handoff) SHALL be accepted and its message sent as soon as that reply ends; at most one such click is held at a time.

#### Scenario: Accepting a quote from the card
- **WHEN** the customer clicks "Accept this quote and place my order" on a quote surface
- **THEN** the chat shows that text as the customer's message and sends it to `POST /api/chat`

#### Scenario: Button args identify the surface
- **WHEN** the gateway builds a surface with id `check_availability-3f9a1c0b2e7d`
- **THEN** every Button's `sendChatMessage` args contain `surface: "check_availability-3f9a1c0b2e7d"` and `button` equal to that Button's component id

### Requirement: Surfaces render in the chat with the standard catalog

The UI SHALL render each `a2ui` event inside the assistant message of that turn with CopilotKit's standard catalog (`standardUI`, extended only by the `sendChatMessage` function), themed with `--a2ui-*` variables matching the app. A message that has an A2UI surface for a quote, serviceability result or product list SHALL NOT also render the legacy card of the same kind. Messages without a surface SHALL render as before. The UI SHALL NOT require a CopilotKit runtime or send requests to one.

#### Scenario: Quote surface replaces the legacy quote card
- **WHEN** a turn delivers both a `structured_card` quote and an `a2ui` quote surface
- **THEN** the assistant message shows the A2UI surface and not `QuoteCard`

### Requirement: Checkout surfaces

When A2UI is enabled the gateway SHALL emit surfaces for successful results of the cart tools (`add_to_cart`, `remove_from_cart`, `get_cart`), `create_order`, `get_order`, `check_availability`, `schedule_installation`, `get_payment_methods`, `process_payment` and `get_product_by_id`. An installation-slots surface SHALL offer one button per available slot whose message names the full date and time window. A payment surface SHALL show the order total from the session's `order_context`, one button per saved payment method, and the secure payment form. Whole numbers SHALL be shown without a decimal part. Product list surfaces SHALL list only the internet plans available at the checked address when the session's `serviceability_context` lists `available_products`; other categories are not filtered.

#### Scenario: Slot buttons
- **WHEN** `check_availability` returns a morning slot on 2026-11-27
- **THEN** the surface has a button whose message is "Please book my installation for Thursday, November 27, 2026, 8 AM–12 PM (morning)."

#### Scenario: Plans at an FTTP address
- **WHEN** `serviceability_context.available_products` is `["FIB-1G", "FIB-5G"]` and `list_available_products` returns 16 products
- **THEN** the only internet plans on the plans surface are Business Fiber 1 Gbps and Business Fiber 5 Gbps (Voice, SD-WAN and Mobile plans remain, since they work on any access)

#### Scenario: Integer display
- **WHEN** a tool result carries `max_speed_mbps: 5000.0` and `term_months: 12.0`
- **THEN** the surfaces show "5,000 Mbps" and "12 months"

### Requirement: Secure payment form

Card and bank account details SHALL be entered only in the `SecurePaymentForm` component of a payment surface. The form SHALL keep the details in component state, send them only to `POST /api/payment-methods`, clear them after submitting, and then send a chat message naming only the method type and last four digits. No card number, CVV, routing or account number SHALL appear in a chat message, an A2UI data model, an SSE event or a model request.

#### Scenario: New customer adds a card
- **WHEN** the customer enters a valid Visa card in the form and submits
- **THEN** the card is tokenized and saved to their account
- **AND** the chat sends "I've added my Visa ending 1111. Please use it to pay for my order."
- **AND** the payment agent pays the order with the saved token

### Requirement: Quote selection

Every quote surface button that accepts a quote SHALL name that quote's id. A quote surface SHALL offer one button per other contract term (12, 24, 36 months) that asks to re-quote the same quote on that term, and an "Add a service" button; the offer agent SHALL re-quote the same items on the requested term without asking questions first. When a customer message names an active quote id of the session's customer that differs from `offer_context.offer_id`, the gateway SHALL load that quote into `offer_context` before routing the turn.

#### Scenario: Accepting the 24-month quote of two
- **WHEN** quotes OFF-24 (24 months) and OFF-36 (36 months) were shown and `offer_context` is OFF-36
- **AND** the customer clicks Accept on OFF-24
- **THEN** `offer_context.offer_id` is OFF-24 before order_agent runs

#### Scenario: Changing the term from the card
- **WHEN** a 12-month quote OFF-1 is shown and the customer clicks "24 months"
- **THEN** the chat sends "Please re-quote OFF-1 on a 24-month term."
- **AND** the offer agent calls generate_offer_quote with the same items and term_months 24

### Requirement: Contact details before the order

After a new company is registered without a contact email on file, the gateway SHALL show a contact card (name, email, optional phone) whose Save button is disabled until a name and a valid email are entered and then sends "My contact details: name <name>, email <email>, phone <phone>.". The discovery agent SHALL save these details as a CRM contact and record them as `customer_context.contact`. `create_order` SHALL refuse to create an order without a valid contact email (taken from the call or from `customer_context.contact.email`) and return `error: contact_email_required`; the gateway SHALL then show the contact card, and once discovery has saved the contact the gateway SHALL hand off to order_agent in the same turn to create the order. Quote, order, payment and installation emails SHALL go to the contact email, and no notification SHALL contain a payment-method token.

#### Scenario: Contact skipped at registration
- **WHEN** a new customer accepts a quote without having given an email
- **THEN** no order is created and the contact card is shown
- **AND** after the customer saves name and email, the order is created in the same turn with that email

#### Scenario: Payment receipt email
- **WHEN** a payment succeeds for a customer whose contact email is jane@acme.com
- **THEN** the payment confirmation is queued to jane@acme.com and names the method as "Visa card ending 1111", not its token

### Requirement: Acted surfaces show completion

When the customer clicks a Button of a surface, the UI SHALL update that surface in place: the clicked Button SHALL be the only highlighted (`primary`) Button, every Button and input of the surface SHALL be disabled, and the surface SHALL show a status badge. While the turn runs, the clicked Button SHALL show a loading state and the badge SHALL read "Sending…". When the turn completes, the clicked Button SHALL show a check icon and the badge SHALL read "Saved" for a contact surface and "Selected: <button label>" otherwise. When the turn fails, the surface SHALL return to its original, clickable state.

#### Scenario: Choosing a later installation slot
- **WHEN** the slots surface highlights the earliest slot and the customer clicks another slot
- **THEN** after the turn completes the clicked slot is the highlighted Button with a check icon, the earliest slot is no longer highlighted, all slot Buttons are disabled, and the badge reads "Selected: <slot label>"

#### Scenario: Saving contact details
- **WHEN** the customer clicks "Save contact details" on the contact surface
- **THEN** the name, email and phone fields and the Save Button are disabled, the typed values stay visible, and the badge reads "Saved"

#### Scenario: Saving contact details while the reply that showed the card is still streaming
- **WHEN** the contact surface arrives with the registration result, the turn continues with a handoff, and the customer clicks "Save contact details" before that turn ends
- **THEN** the surface immediately shows the Save Button loading and the badge "Sending…", the contact message is sent to `POST /api/chat` once the running turn ends, and after it completes the badge reads "Saved"

#### Scenario: Turn fails after a click
- **WHEN** the customer clicks a Button and the turn ends with an `error` event
- **THEN** the surface shows its original Buttons, enabled, without a badge

### Requirement: Completed steps close their surfaces

A surface whose step was completed without a click on it SHALL be closed the same way as an acted surface, without a highlighted Button: when `create_order` succeeds the UI SHALL close every open cart, quote and contact surface with the badge "Order placed"; when `schedule_installation` succeeds it SHALL close every open scheduling surface with the badge "Installation booked". A surface that already shows a choice keeps it.

#### Scenario: Order placed in the same turn as the cart
- **WHEN** the order agent shows the cart surface and places the order in the same turn (the customer never clicks "Place my order")
- **THEN** the cart surface's Buttons are disabled, none is highlighted, and its badge reads "Order placed"

