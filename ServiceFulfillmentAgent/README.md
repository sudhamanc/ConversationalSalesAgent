# Service Fulfillment Agent

A2A service `service_fulfillment_agent`: installation scheduling for created orders, equipment
provisioning, technician dispatch and service activation (prospect → customer). Details and
the tool/table/journey-key matrix are in [AGENTS.md](AGENTS.md); the shared service contract is
[README: Agent Service Guide](../README.md#agent-service-guide).

## Scope

Does: installation slots and booking, reschedule/cancel, provisioning and dispatch, installation
completion, service activation, fulfillment status.

Does not: address/coverage checks (serviceability_agent), product recommendation
(product_agent), pricing (offer_management_agent), order creation (order_agent), payment
(payment_agent). After a successful booking the gateway continues with payment_agent.

## Environment

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_MODEL` | yes | no default |
| `GOOGLE_API_KEY` | yes (or Vertex AI env) | |
| `DATABASE_URL` | yes | `postgresql://user:pw@host:5432/db` |
| `PUBLIC_URL` | yes | e.g. `http://localhost:8207` (agent card) |
| `SERVICE_AUTH`, `LOG_LEVEL`, `COMPACTION_*`, `CONTEXT_CACHE_*` | no | see the guide |

## Local run

```bash
uv pip install -p venv/bin/python -e libs/sales_common -e ServiceFulfillmentAgent
venv/bin/python -m sales_common.migrate --seed
GEMINI_MODEL=gemini-3-flash-preview PUBLIC_URL=http://localhost:8207 \
DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa \
  venv/bin/uvicorn service_fulfillment_agent.server:app --host 0.0.0.0 --port 8207
```

Agent card: `GET /.well-known/agent-card.json`; health: `GET /healthz`.

## Docker

```bash
docker build -f ServiceFulfillmentAgent/Dockerfile -t service-fulfillment-agent .   # repo root context
```

## Tests

```bash
TEST_DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa_test_fulfillment \
  venv/bin/python -m pytest ServiceFulfillmentAgent/tests -q
```
