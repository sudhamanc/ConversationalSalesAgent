## MODIFIED Requirements

### Requirement: Notification outbox

Services other than customer communication SHALL request customer notifications by inserting a `notifications` row with status `pending`, in the same transaction as the business change that triggers it. The customer communication service SHALL deliver pending notifications:
- at least once
- after de-duplication
- marking each row `sent` or `failed` with an error message

Delivery SHALL run both in the service's background loop and on demand in `POST /dispatch`, so that a service that only has CPU while serving requests (Cloud Run scaled to zero) still delivers notifications.

#### Scenario: Order confirmation
- **WHEN** `order_agent` creates order `ORD-1` for a contact with an email address
- **THEN** a `notifications` row of type `order_confirmation` with status `pending` exists in the same commit, and is later marked `sent` (or `simulated` when SMTP is disabled)

#### Scenario: Communication service down
- **WHEN** the customer communication service is not running while an order is created
- **THEN** order creation still succeeds, and the notification is delivered after the service starts

#### Scenario: Communication service scaled to zero
- **WHEN** a quote confirmation is queued and the customer communication service has no running instance
- **THEN** the next `POST /dispatch` starts the service and the row is marked `sent` within that request
