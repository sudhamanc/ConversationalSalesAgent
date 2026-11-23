## ADDED Requirements

### Requirement: Order-to-scheduling handoff

When `create_order` succeeded in the current turn and the order has no scheduled installation, the gateway SHALL hand off from `order_agent` to `service_fulfillment_agent` in the same turn with a message asking it to show the available installation slots. The handoff counts toward the per-turn hop limit and fires once per created order.

#### Scenario: Order created
- **WHEN** order_agent creates order ORD-1 with status `pending_payment`
- **THEN** the same turn continues with service_fulfillment_agent, which offers installation slots

### Requirement: Payment details are masked before routing

The gateway SHALL replace card numbers that pass the Luhn check, CVV codes and bank account numbers in a user chat message with `[REDACTED_CARD]`, `[REDACTED_CVV]` and `[REDACTED_ACCOUNT]` before the message is stored, routed or sent to any agent.

#### Scenario: Card typed into chat
- **WHEN** the customer sends "my card is 4111 1111 1111 1111 cvv 123"
- **THEN** the router and agents receive "my card is [REDACTED_CARD] cvv [REDACTED_CVV]"
