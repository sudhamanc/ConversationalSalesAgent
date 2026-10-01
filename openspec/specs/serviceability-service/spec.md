# serviceability-service Specification

## Purpose
TBD - created by archiving change catalog-serviceability-mcp. Update Purpose after archive.
## Requirements
### Requirement: REST API

The serviceability service SHALL expose these JSON endpoints:
- `POST /api/v1/addresses/validate` (body `{address}`)
- `POST /api/v1/addresses/normalize` (body `{street, city, state, zip_code}`)
- `POST /api/v1/serviceability/check` (body `{street, city, state, zip_code}`)
- `GET /api/v1/infrastructure/{technology}`
- `GET /api/v1/coverage-zones`

Invalid input SHALL return HTTP 422 with a JSON error body.

#### Scenario: Serviceable address
- **WHEN** a client checks `{"street":"123 Main St","city":"Philadelphia","state":"PA","zip_code":"19103"}`
- **THEN** the response has `serviceable: true`, `infrastructure_type`, `max_speed_mbps`, `service_zone`, `estimated_install_days` and a non-empty `available_products` list of SKU ids

#### Scenario: Unserviceable address
- **WHEN** a client checks an address whose ZIP is not in coverage
- **THEN** the response has `serviceable: false` and an empty `available_products` list

#### Scenario: PO box rejected
- **WHEN** a client validates "PO Box 12, Philadelphia, PA 19103"
- **THEN** the response has `valid: false` with an error explaining PO boxes are not serviceable

### Requirement: MCP server

The serviceability service SHALL expose an MCP server over streamable HTTP at `/mcp/`. It SHALL provide these tools, with the same semantics as the REST API:
- `validate_and_parse_address`
- `normalize_address`
- `extract_zip_code`
- `check_service_availability`
- `get_infrastructure_by_technology`
- `get_coverage_zones`

Results SHALL be JSON objects, and the server SHALL operate statelessly.

#### Scenario: Agent tool call
- **WHEN** an MCP client calls `check_service_availability` for ZIP 19103
- **THEN** the result equals the REST response for the same address

### Requirement: Serviceability context recorded by the agent

When `serviceability_agent` receives a `check_service_availability` result, it SHALL record `serviceability_context` in session state with these fields: `is_serviceable`, `infrastructure_type`, `max_speed_mbps`, `available_products`, `available_product_categories`, `service_zone`, `estimated_install_days`, `service_address`. It SHALL return the value as a `_context_update` to the gateway.

#### Scenario: Context update after check
- **WHEN** the serviceability agent checks ZIP 19103
- **THEN** the gateway session's `serviceability_context.is_serviceable` is `true`

### Requirement: Consistent coverage records

Every serviceable coverage record SHALL include infrastructure details. Records lacking infrastructure data SHALL derive them from the zone's technology defaults, rather than returning `infrastructure: null`.

#### Scenario: Previously sparse ZIP
- **WHEN** checking a serviceable ZIP that had no infrastructure object in the legacy mock data
- **THEN** the response's `infrastructure` object is populated from the technology defaults

