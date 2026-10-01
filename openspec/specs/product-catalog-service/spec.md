# product-catalog-service Specification

## Purpose
TBD - created by archiving change catalog-serviceability-mcp. Update Purpose after archive.
## Requirements
### Requirement: Catalog is the single SKU source

The catalog service SHALL own the product records for all sellable SKUs. Each record has: `product_id`, `product_name`, `category`, `technology`, `speeds`, `description`, `features`, `available`, `unit_price`, `family`. Agents SHALL obtain product data only through this service.

#### Scenario: Seeded catalog
- **WHEN** the catalog service starts against a seeded database
- **THEN** `GET /api/v1/products` returns 16 products, including `FIB-5G` and `SDWAN-PRO`

### Requirement: REST API

The catalog service SHALL expose these JSON endpoints:
- `GET /api/v1/products?category=`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/products/search?speed=&technology=`
- `GET /api/v1/categories`
- `POST /api/v1/products/compare` (body `{product_ids: [2..5]}`)
- `GET /api/v1/products/{product_id}/alternatives?criteria=faster|similar|different_tech`
- `GET /api/v1/products/best-value?category=`
- `GET /api/v1/knowledge/search?q=&top_k=`

Invalid input SHALL return HTTP 422, and unknown products HTTP 404, each with a JSON error body.

#### Scenario: Case-insensitive lookup
- **WHEN** a client requests `GET /api/v1/products/fib-5g`
- **THEN** the response is HTTP 200 with `product_id` `FIB-5G`

#### Scenario: Compare too many products
- **WHEN** a client posts 6 product ids to `/api/v1/products/compare`
- **THEN** the response is HTTP 422

#### Scenario: Fastest product computed numerically
- **WHEN** comparing `FIB-1G`, `FIB-5G` and `FIB-10G`
- **THEN** the comparison names `FIB-10G` as fastest

#### Scenario: Best value ranked by throughput within a category
- **WHEN** a client requests `GET /api/v1/products/best-value?category=coax`
- **THEN** the response recommends `COAX-1G` and contains no price fields
- **AND** the endpoint takes no budget parameter, because pricing is not disclosed by the catalog

### Requirement: MCP server

The catalog service SHALL expose an MCP server over streamable HTTP at `/mcp/`. It SHALL provide these tools, with the same semantics as the REST API:
- `list_available_products`
- `get_product_by_id`
- `search_products_by_criteria`
- `get_product_categories`
- `compare_products`
- `suggest_alternatives`
- `get_best_value_product`
- `search_product_knowledge`

Each tool result SHALL be a JSON object. The server SHALL operate statelessly, so any replica can serve any request.

#### Scenario: Agent lists tools
- **WHEN** an MCP client calls `tools/list`
- **THEN** it receives the 8 tool names above, each with a description and input schema

#### Scenario: Tool call result
- **WHEN** an MCP client calls `get_product_by_id` with `{"product_id": "FIB-1G"}`
- **THEN** the result contains `found: true` and `product_id` `FIB-1G`

### Requirement: Pricing not disclosed by product tools

Product lookup tools and endpoints SHALL NOT return price fields, preserving the separation where pricing comes only from offer management.

#### Scenario: No price in product lookup
- **WHEN** `get_product_by_id` returns `FIB-5G`
- **THEN** the result has no `unit_price` or `price` field

### Requirement: Knowledge search

`search_product_knowledge` SHALL return up to `top_k` (default 4, max 10) passages from the product documents. Each passage SHALL include its `doc_file`, `section` and `product_ids` metadata. If the index is unavailable, it SHALL return an explicit `available: false` result rather than an error.

#### Scenario: SLA question
- **WHEN** searching "fiber SLA uptime"
- **THEN** at least one passage from `fiber_internet.md` is returned

### Requirement: FAQ knowledge search

The catalog service SHALL index `data/faq_docs/*.md` into a separate Chroma collection `faq_knowledge` and expose `search_faq(query, top_k)` over MCP and `GET /api/v1/faq/search?q=` over REST. Results SHALL include passage text, topic, section and distance. They SHALL return `available: false` instead of raising when the index cannot be used.

#### Scenario: Policy question
- **WHEN** `search_faq("cancellation policy")` is called
- **THEN** the top passages come from the cancellation-policy FAQ document

#### Scenario: Index unavailable
- **WHEN** the embedding model or index cannot be loaded
- **THEN** `search_faq` returns `available: false` with a message

