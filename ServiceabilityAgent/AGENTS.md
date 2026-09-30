# Serviceability Agent

**Type:** Deterministic PRE-SALE agent (A2A service)
**Framework:** Google ADK 2.10 + A2A, tools over MCP
**Package:** `serviceability_agent`
**Build guide:** [docs/agent-service-guide.md](../docs/agent-service-guide.md)

---

## Purpose

Validates a business address and reports whether it can receive service, with
infrastructure details, speed capabilities and the product SKU ids sold there.
It runs **before** product recommendations and pricing.

The agent has **no local tools and no coverage data**. All deterministic logic
(address parsing, coverage lookup, optional upstream GIS) lives in the
**serviceability service** ([services/serviceability](../services/serviceability/README.md)),
which the agent consumes over MCP (streamable HTTP) with `McpToolset`.

---

## Architecture

| Attribute | Value |
|-----------|-------|
| **Agent name** | `serviceability_agent` (hardcoded; the gateway routes by it) |
| **Model** | `GEMINI_MODEL` (required, no default) |
| **Temperature** | 0.0, max 2048 tokens |
| **Tools** | `sales_common.mcp_client.mcp_toolset(SERVICEABILITY_MCP_URL)` |
| **Callbacks** | `before_agent_callback=[import_forwarded_context]`, `after_tool_callback=[record_serviceability_context, export_context_delta]` |
| **Served by** | `serviceability_agent/server.py` → `create_a2a_app(root_agent)` |
| **Data source** | serviceability service → PostgreSQL `coverage_zones` (or upstream GIS API) |

```text
ServiceabilityAgent/
├── pyproject.toml / Dockerfile (build context = repo root)
├── serviceability_agent/
│   ├── __init__.py      # build_agent, root_agent
│   ├── agent.py         # Agent + McpToolset
│   ├── callbacks.py     # record_serviceability_context
│   ├── prompts.py       # static domain prompt (UI-parsed output format)
│   └── server.py        # A2A app
└── tests/               # construction + callback tests (no network, no API key)
```

---

## Tools (MCP, served by services/serviceability)

| Tool | Arguments | Result (JSON object) |
|------|-----------|----------------------|
| `validate_and_parse_address` | `address_string` | `{valid, address{street,city,state,zip_code}}` or `{valid:false, error}` |
| `normalize_address` | `street, city, state, zip_code` | `{normalized_address}` |
| `extract_zip_code` | `address_string` | `{zip_code}` (`""` if none) |
| `check_service_availability` | `street, city, state, zip_code` | see below |
| `get_infrastructure_by_technology` | `technology, zone="all"` | `{technology, zone, infrastructure:[...]}` |
| `get_coverage_zones` | – | `{zones:[...], count}` |

`check_service_availability` result:

```json
{"serviceable": true, "address": {...}, "infrastructure": {"type", "network_element",
 "speed_capability", "service_class", "redundancy_available"}, "infrastructure_type": "FTTP",
 "max_speed_mbps": 5000, "service_zone": "Metro-Center-PA", "estimated_install_days": 5,
 "available_product_categories": ["Internet","Voice","SD-WAN","Mobile"],
 "available_products": ["FIB-1G", "..."]}
```

Unserviceable: `{"serviceable": false, "address", "reason", "available_products": [], "available_product_categories": []}`.
Invalid input (e.g. unknown state) is an MCP tool error.

---

## Journey context

`record_serviceability_context` (in `callbacks.py`) handles every successful
`check_service_availability` result (serviceable or not) and writes:

```python
state["serviceability_context"] = {
    "is_serviceable", "infrastructure_type", "max_speed_mbps", "available_products",
    "available_product_categories", "service_zone", "estimated_install_days", "service_address",
}
```

It returns `None`, so the shared `export_context_delta` runs next and adds
`_context_update.serviceability_context` to the tool response; the gateway merges
it into its session. Tool errors and other tools leave state unchanged.

---

## Conversation behaviour

- Invoked by the gateway workflow: the deterministic Discovery → Serviceability
  handoff after company registration, or when the user asks about coverage.
- The agent cannot transfer. For pricing or product specs it says what comes next;
  the gateway routes the next message.
- **Output format is parsed by the UI** (`SuperAgent/client/src/utils/responseFormatters.js`):
  keep the "location is serviceable / not serviceable" summary, the `Key: Value`
  lines (Infrastructure Type, Service Zone, Switch ID, Cabinet ID, Available Fiber
  Pairs, OLT Equipment, Minimum/Maximum Speed, Symmetrical, Service Class,
  Redundancy, Installation Timeline) and product lines `• **SKU** - Name`.

---

## Environment

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_MODEL`, `GOOGLE_API_KEY` | yes | model |
| `SERVICEABILITY_MCP_URL` | yes | e.g. `http://serviceability:8102/mcp/` (trailing slash) |
| `DATABASE_URL`, `PUBLIC_URL` | yes | A2A sessions/tasks, agent card |
| `SERVICE_AUTH` | no | `gcp_id_token` on Cloud Run (ID token for the MCP call) |
| `MCP_TIMEOUT_SECONDS`, `MCP_TOOL_CACHE_SECONDS` | no | defaults 15 / 300 |

---

## Tests

```bash
pytest ServiceabilityAgent/tests -q                  # agent (no DB, no network)
TEST_DATABASE_URL=postgresql://... pytest services/serviceability/tests -q   # service
```

**Critical distinction:** ServiceabilityAgent (PRE-SALE) answers "can we serve
this address?"; ServiceFulfillmentAgent (POST-SALE) answers "when can we install?".
