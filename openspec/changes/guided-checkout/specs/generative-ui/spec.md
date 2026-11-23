## ADDED Requirements

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
