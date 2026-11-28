## ADDED Requirements

### Requirement: Payment methods REST endpoint

The payment service SHALL expose `POST /payment-methods` taking `customer_id`, `payment_type` (`credit_card` or `ach`) and the card (`card_number`, `expiry_month`, `expiry_year`, `cvv`) or bank (`routing_number`, `account_number`, `account_type`) fields. It SHALL validate and tokenize without a model call, save only the masked method and opaque token to `customer_payment_methods`, and return the payment type, brand, last four digits and whether it was saved, never the token or full numbers. Invalid details SHALL return HTTP 400 with the validation error. The gateway SHALL proxy it as `POST /api/payment-methods` for an authenticated chat session, taking `customer_id` only from the session state.

#### Scenario: Invalid card
- **WHEN** the card number fails the Luhn check
- **THEN** the endpoint returns 400 with "Invalid card number (failed Luhn check)" and nothing is saved

### Requirement: Replies do not repeat cards

Agents SHALL keep a reply to at most two short sentences when their tool result is shown as a card in the chat (serviceability, product lists and details, quotes, cart, orders, installation slots and confirmations, payment methods and receipts), and SHALL NOT repeat the card's rows, prices, slots or identifiers. The serviceability agent SHALL NOT disclose internal network element details (switch, cabinet, OLT, splice point or fiber pair identifiers).

#### Scenario: Serviceable address
- **WHEN** serviceability_agent confirms service at an FTTP address
- **THEN** its reply is a one- or two-sentence confirmation with a next question and contains no switch or cabinet id
