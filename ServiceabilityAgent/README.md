# Serviceability Agent

Deterministic PRE-SALE coverage and infrastructure validation agent, served over
A2A. Details: [AGENTS.md](AGENTS.md). Build conventions:
[docs/agent-service-guide.md](../docs/agent-service-guide.md).

## Scope

Does: address parsing/validation, coverage check, infrastructure and speed
details, product SKU ids available at the address (via the serviceability
service MCP tools).

Does not: product recommendation/specs (product agent), pricing/quotes (offer
management), installation scheduling (service fulfillment).

## How it works

```text
gateway --A2A--> serviceability_agent --MCP (streamable HTTP)--> services/serviceability
                        |                                            |
                 after_tool_callback                          PostgreSQL coverage_zones
      serviceability_context + _context_update                (or upstream GIS API)
```

- Tools come from `McpToolset` at `SERVICEABILITY_MCP_URL`; there are no local tools.
- `callbacks.record_serviceability_context` writes `serviceability_context` from
  the `check_service_availability` result; `export_context_delta` returns it to
  the gateway as `_context_update`.

## Run locally

```bash
# 1. serviceability service (see services/serviceability/README.md)
DATABASE_URL=postgresql://... uvicorn serviceability_service.app:app --port 8102
# 2. the agent
pip install -e libs/sales_common -e ServiceabilityAgent
export GEMINI_MODEL=... GOOGLE_API_KEY=... DATABASE_URL=postgresql://... \
       PUBLIC_URL=http://localhost:8002 SERVICEABILITY_MCP_URL=http://localhost:8102/mcp/
cd ServiceabilityAgent && uvicorn serviceability_agent.server:app --port 8002
```

Docker (build context = repo root): `docker build -f ServiceabilityAgent/Dockerfile .`

## Tests

```bash
venv/bin/python -m pytest ServiceabilityAgent/tests -q
```

Agent tests need no API key, database or network: they check construction
(toolset URL, callbacks, prompt format) and the callback with a recorded MCP
result (`tests/recorded_check_19103.json`).
