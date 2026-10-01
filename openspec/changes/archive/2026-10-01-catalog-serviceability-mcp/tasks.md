# Tasks: Catalog and Serviceability REST + MCP Services

## 1. Data

- [x] 1.1 Write `db/migrations/002_catalog.sql` and `004_coverage.sql`; verify it applies after `001`
- [x] 1.2 Implement `scripts/export_catalog_seed.py` and generate `db/seed/002_catalog.sql` and `003_coverage.sql` (16 products, 38 coverage ZIPs with infrastructure filled); verify row counts after seeding

## 2. Catalog service

- [x] 2.1 Move product docs and ingest script into `services/catalog/` (`git mv`); implement `core`, `repository`, `models`, `rag`; unit tests cover lookup, case-insensitivity, compare (fastest), alternatives, categories, no price fields
- [x] 2.2 Implement REST routes under `/api/v1` with validation; `TestClient` tests for 200/404/422 cases
- [x] 2.3 Implement MCP server with the 8 tool names and mount at `/mcp/`; test lists tools and calls `get_product_by_id` through ADK `McpToolset` against a running server
- [x] 2.4 Write `services/catalog/Dockerfile` and `README.md` (endpoints, MCP tools, env vars)

## 3. Serviceability service

- [x] 3.1 Move address and GIS logic into `services/serviceability/` (`git mv`); implement `core`, `repository`, `address`, `gis_client`; unit tests migrated from `ServiceabilityAgent/tests` and updated (stale GIS tests fixed)
- [x] 3.2 Implement REST routes; `TestClient` tests for serviceable, unserviceable, PO box, invalid state
- [x] 3.3 Implement MCP server with 6 tool names; round-trip test via `McpToolset`
- [x] 3.4 Write `services/serviceability/Dockerfile` and `README.md`

## 4. Agents consume MCP

- [x] 4.1 `ProductAgent/product_agent/agent.py` uses `McpToolset` to catalog; remove local tool modules and heavy deps from `pyproject.toml`; construction test asserts toolset URL
- [x] 4.2 `ServiceabilityAgent/serviceability_agent/agent.py` uses `McpToolset` plus `after_tool_callback` for `serviceability_context`; unit test feeds a recorded MCP result and asserts state + `_context_update`
- [x] 4.3 Update `ProductAgent/AGENTS.md`, `ServiceabilityAgent/AGENTS.md`, `AGENTS.md` tool sections; verify tool names documented match `tools/list`
