# Spec Delta: domain-tool-services

## Purpose

Defines REST + MCP tool services for the CRM, pricing, orders, payments, fulfillment and notifications domains, each the single writer of its tables.

## ADDED Requirements

### Requirement: Domain tool services

Each of the domains crm, pricing, orders, payments, fulfillment and notifications SHALL be served by its own service. Each service SHALL expose a REST API under `/api/v1` and an MCP server at `/mcp/`. The MCP tool names SHALL be identical to the corresponding agent's current tool names.

#### Scenario: Order agent uses MCP
- **WHEN** `order_agent` adds an item to a cart
- **THEN** the call is made to the orders service MCP tool `add_to_cart`, and no SQL runs inside the agent container

### Requirement: Single writer per table

Each business table SHALL be written by exactly one service. Other services SHALL change that data only through the owning service's API.

#### Scenario: Payment updates order status
- **WHEN** a payment completes for order `ORD-1`
- **THEN** the payments service calls the orders service API to set the payment status, and does not write `orders` directly

### Requirement: Pricing uses catalog prices

The pricing service SHALL obtain SKU unit prices from the catalog service, and SHALL reject quote items whose SKU does not exist in the catalog.

#### Scenario: Unknown SKU
- **WHEN** a quote is requested for SKU `FIB-99G`
- **THEN** the pricing service returns a validation error naming the unknown SKU
