# Proposal: REST + MCP for the Remaining Domain Tools (Follow-up)

> **Status:** planned follow-up. Not implemented in the initial rewrite, per the decision "Catalog + serviceability now, rest later".

## Why

After `catalog-serviceability-mcp`, six agents still run their deterministic tools in-process against shared PostgreSQL tables:
- discovery
- offer management
- order
- payment
- service fulfillment
- customer communication

This keeps cross-domain writes (e.g. Payment → `orders`) and duplicated data (Offer's own price book) inside LLM agent containers. It also prevents reuse by non-agent clients (CRM, billing, portals).

## What Changes

- Add a REST + MCP service per domain, following the `services/<domain>/` pattern from `catalog-serviceability-mcp`:
  - `crm` (discovery tools)
  - `pricing` (offer tools, reading SKU prices from the catalog service)
  - `orders` (cart/order tools)
  - `payments`
  - `fulfillment`
  - `notifications`
- Agents switch from in-process tools to `McpToolset`.
- Cross-domain writes become API calls, so each table has exactly one writing service:
  - Payment → `orders` becomes `POST /api/v1/orders/{id}/payment-status` on the orders service
  - Fulfillment → `orders`/`accounts` updates become orders/crm service calls
- OfferManagement's `PRODUCT_PRICE_BOOK` is deleted; pricing reads `unit_price` from the catalog service.
- The notification outbox is written only through the notifications service API.

## Capabilities

### New Capabilities

- `domain-tool-services`: REST + MCP interfaces for CRM, pricing, orders, payments, fulfillment and notifications, with single-writer table ownership.

### Modified Capabilities

None. The catalog price lookup for the pricing service is added as a requirement delta once `catalog-serviceability-mcp` is archived into `openspec/specs/`.

## Non-goals

- Splitting PostgreSQL into per-service databases (possible after single-writer ownership is in place).

## Impact

- **Services:** 6 new services, all agents' `agent.py` updated to use `McpToolset`, and `scripts/services.conf` gains 6 rows.
- **Deployment:** 6 more Cloud Run services.
