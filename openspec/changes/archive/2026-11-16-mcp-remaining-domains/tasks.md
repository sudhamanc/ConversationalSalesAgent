# Tasks: REST + MCP for the Remaining Domain Tools

## 1. Notifications service

- [ ] 1.1 Create `services/notifications/` (outbox write API, history API, MCP tools); tests for enqueue and history via REST and MCP
- [ ] 1.2 Switch `customer_communication_agent` and all producers to the notifications API; verify no agent writes `notifications` directly

## 2. CRM, pricing, orders, payments, fulfillment services

- [ ] 2.1 CRM service from discovery tools; discovery agent uses MCP; tests
- [ ] 2.2 Pricing service using catalog prices; delete `PRODUCT_PRICE_BOOK`; unknown-SKU test
- [ ] 2.3 Orders service (single writer of carts/orders/quotes status); order agent uses MCP; tests
- [ ] 2.4 Payments service calling orders API for status; idempotency-key test
- [ ] 2.5 Fulfillment service calling orders/crm APIs; tests

## 3. Operations

- [ ] 3.1 Add 6 rows to `scripts/services.conf`, Dockerfiles, compose entries; verify local start is healthy
- [ ] 3.2 Update `AGENTS.md`, architecture brief, `db/README.md` ownership table
