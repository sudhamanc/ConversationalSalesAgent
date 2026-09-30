# Proposal: Catalog and Serviceability as REST APIs + MCP Servers

## Why

Product catalog and coverage data live as Python dicts inside agent modules. The 16-SKU list is duplicated in three places: ProductAgent, OfferManagement's price book, and Serviceability's `available_products`. Other systems cannot reuse these tools, and any change requires redeploying an LLM agent. Serving them as standalone services with a REST API and an MCP interface makes them reusable deterministic tools and gives one source of truth.

## What Changes

- New **catalog service** (`services/catalog/`):
  - PostgreSQL `products` table (the 16 SKUs, including price and family) seeded from the current `PRODUCT_CATALOG` and `PRODUCT_PRICE_BOOK`
  - ChromaDB product-knowledge RAG (moved from ProductAgent)
  - REST API under `/api/v1`
  - MCP server at `/mcp/` exposing the 8 existing product tool names
- New **serviceability service** (`services/serviceability/`):
  - PostgreSQL `coverage_zones` table seeded from `MOCK_COVERAGE_DATA`
  - address validation/normalization
  - optional upstream GIS API
  - REST API under `/api/v1` and an MCP server at `/mcp/` exposing the 6 existing serviceability tool names
- **BREAKING:** `product_agent` and `serviceability_agent` no longer contain tool implementations. They consume the MCP servers via ADK `McpToolset` over streamable HTTP.
  - Serviceability's `serviceability_context` state write moves to an agent-side `after_tool_callback`.
- Serviceability responses include `available_products` (SKU ids) directly, not only in state.
- The product agent image no longer bundles PyTorch or the embedding model; only the catalog service does.

## Capabilities

### New Capabilities

- `product-catalog-service`: product catalog and knowledge search as REST + MCP.
- `serviceability-service`: address validation and coverage lookup as REST + MCP.

### Modified Capabilities

None.

## Non-goals

- Making OfferManagement read prices from the catalog service (tracked in `mcp-remaining-domains`).
- Real GIS integration (the upstream client is kept behind `USE_MOCK_DATA`).
- Fixing known catalog logic defects beyond what the API contract needs. The design lists which defects are fixed.

## Impact

- **Code:** `services/catalog/`, `services/serviceability/`; `ProductAgent/product_agent/tools/*` and `ServiceabilityAgent/serviceability_agent/tools/*` move into the services; the agents' `agent.py` switch to `McpToolset`.
- **Data:** new `products` and `coverage_zones` tables (migration `002`).
- **Dependencies:** `mcp>=2.2,<3` (`MCPServer`); chromadb + sentence-transformers only in the catalog service.
- **Docs:** `ProductAgent/AGENTS.md`, `ServiceabilityAgent/AGENTS.md`, `services/*/README.md`, `AGENTS.md`.
