# Discovery Agent

Discovery-phase agent for company identification, prospect lookup/registration and conversational BANT qualification. It runs as an independent A2A service (`discovery_agent`) behind the SuperAgent gateway and stores data in PostgreSQL.

See [AGENTS.md](AGENTS.md) for tools, tables and the `customer_context` contract, and [README: Agent Service Guide](../README.md#agent-service-guide) for the service conventions.

## Scope

Does: company lookup and enrichment, new company/location and contact records, BANT opportunity scoring, returning-customer pipeline check, publishing `customer_context`.

Does not: serviceability checks (ServiceabilityAgent, triggered by the gateway after Discovery), product fit, pricing, orders, payment or fulfillment.

## Layout

```text
DiscoveryAgent/
├── discovery_agent/   # agent.py, prompts.py, server.py, tools/
├── tests/
├── pyproject.toml     # discovery-agent (depends on sales-common)
├── Dockerfile
```

## Run locally

```bash
uv pip install -p venv/bin/python -e libs/sales_common -e DiscoveryAgent
DATABASE_URL=postgresql://csa:...@127.0.0.1:5432/csa \
GEMINI_MODEL=gemini-3-flash-preview GOOGLE_API_KEY=... \
PUBLIC_URL=http://127.0.0.1:8201 \
  venv/bin/uvicorn discovery_agent.server:app --port 8201
```

Apply the schema first with `python -m sales_common.migrate --seed`. The agent card is at `/.well-known/agent-card.json` and the health check at `/healthz`.

## Docker

```bash
docker build -f DiscoveryAgent/Dockerfile -t discovery-agent .   # from the repo root
```

## Tests

```bash
TEST_DATABASE_URL=postgresql://user:pw@127.0.0.1:5432/scratch_db \
  venv/bin/python -m pytest DiscoveryAgent/tests -q
```
