# Serviceability Service

US business address validation and network coverage lookup, exposed as a REST
API (for any system) and an MCP server (for agents). One implementation
(`core.py`) backs both. Stateless; horizontally scalable.

```text
FastAPI /api/v1 ─┐
                 ├─> core.py ─> repository.py ─> PostgreSQL coverage_zones   (USE_MOCK_DATA=true)
MCP /mcp/ ───────┘         └──> gis_client.py ─> upstream GIS API            (USE_MOCK_DATA=false)
                 address.py: parsing / validation / normalization (pure)
```

## REST API

| Method & path | Body / params | Response |
|---|---|---|
| `POST /api/v1/addresses/validate` | `{"address": "123 Market St, Philadelphia, PA 19107"}` | `{"valid": true, "address": {street, city, state, zip_code}}` or `{"valid": false, "error": "..."}` |
| `POST /api/v1/addresses/normalize` | `{street, city, state, zip_code}` | `{"normalized_address": "123 Market St, Philadelphia, PA 19107"}` |
| `POST /api/v1/serviceability/check` | `{street, city, state, zip_code}` | serviceability result (below) |
| `GET /api/v1/infrastructure/{technology}` | `?zone=` (ignored) | `{technology, zone, infrastructure: [capability]}` (empty list when unknown) |
| `GET /api/v1/coverage-zones` | – | `{zones: [...], count}` |
| `GET /healthz` | – | `{"status": "ok"}` (503 when the database is unreachable) |

Invalid input (unknown state code, malformed ZIP, missing/blank fields) returns
HTTP 422 with FastAPI's JSON `{"detail": [...]}` body. A PO box or non-US
address is not a 422: `validate` answers `{"valid": false, "error": ...}`.

Serviceability result (fields that are null are omitted):

```json
{
  "serviceable": true,
  "address": {"street": "123 Main St", "city": "Philadelphia", "state": "PA", "zip_code": "19103"},
  "infrastructure": {"type": "Fiber", "network_element": {"switch_id": "PHI-SW-002", "...": "..."},
                     "speed_capability": {"min_speed_mbps": 100, "max_speed_mbps": 5000, "symmetrical": true},
                     "service_class": "Business", "redundancy_available": true},
  "infrastructure_type": "FTTP",
  "max_speed_mbps": 5000,
  "service_zone": "Metro-Center-PA",
  "estimated_install_days": 5,
  "available_product_categories": ["Internet", "Voice", "SD-WAN", "Mobile"],
  "available_products": ["FIB-1G", "FIB-5G", "VOICE-BAS", "..."]
}
```

Unserviceable: `{"serviceable": false, "address": {...}, "reason": "...", "available_product_categories": [], "available_products": []}`.

## MCP server

Streamable HTTP at `/mcp/` (stateless, JSON responses; client URL must end in
`/mcp/`). Tools keep the legacy agent tool names; each returns the same JSON
object as the matching REST route (as `structuredContent` and JSON text):

`validate_and_parse_address(address_string)`, `normalize_address(street, city, state, zip_code)`,
`extract_zip_code(address_string)`, `check_service_availability(street, city, state, zip_code)`,
`get_infrastructure_by_technology(technology, zone="all")`, `get_coverage_zones()`.

Invalid input raises an MCP tool error (`isError: true`), the analogue of 422.
Agents connect with `sales_common.mcp_client.mcp_toolset(url)`.

## Data

- Table `coverage_zones` (`db/migrations/004_coverage.sql`), one row per ZIP.
- Seed `db/seed/003_coverage.sql` (38 ZIPs, 35 serviceable), generated from the
  legacy `MOCK_COVERAGE_DATA` by `scripts/export_coverage_seed.py`. Serviceable
  ZIPs that had no infrastructure object get one from the technology defaults
  (max speed capped at the fastest internet SKU sold there). Regenerate with
  `python scripts/export_coverage_seed.py`.
- Apply with `python -m sales_common.migrate --seed`.

## Environment

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | required | `postgresql://user:pw@host:5432/db` |
| `USE_MOCK_DATA` | `true` | `true`: coverage from `coverage_zones`; `false`: upstream GIS API |
| `GIS_API_URL`, `GIS_API_KEY` | – | upstream (`POST {url}/serviceability/check`, bearer key; key never logged) |
| `GIS_TIMEOUT_SECONDS` | `10` | upstream timeout |
| `GIS_CACHE_TTL_SECONDS` | `86400` | in-memory cache of upstream results (0 disables) |
| `PORT` | `8080` | container port |
| `LOG_LEVEL` | `INFO` | |

## Run

```bash
pip install -e libs/sales_common -e services/serviceability
DATABASE_URL=postgresql://... uvicorn serviceability_service.app:app --host 0.0.0.0 --port 8102
docker build -f services/serviceability/Dockerfile -t serviceability-service .   # context = repo root
```

## Tests

```bash
TEST_DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/<scratch_db> \
  venv/bin/python -m pytest services/serviceability/tests -q
```

Database tests apply migrations and seeds to the scratch DB and are skipped when
`TEST_DATABASE_URL` is unset. The MCP test serves the app with uvicorn on a free
port and calls it through ADK `McpToolset`.
