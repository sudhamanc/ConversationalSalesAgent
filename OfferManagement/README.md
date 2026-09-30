# Offer Management Agent

Deterministic pricing, discounts and quotes for the Conversational Sales Agent, served as an independent **A2A service** (`offer_management_agent`).

See [AGENTS.md](AGENTS.md) for tools, pricing rules and journey context, and [docs/agent-service-guide.md](../docs/agent-service-guide.md) for the service contract.

## Run locally

```bash
uv pip install -e libs/sales_common -e OfferManagement
export GEMINI_MODEL=gemini-3-flash-preview GOOGLE_API_KEY=...
export DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa
export PUBLIC_URL=http://localhost:8204
uvicorn offer_management.server:app --host 0.0.0.0 --port 8204
```

- Agent card: `GET /.well-known/agent-card.json`
- Health: `GET /healthz`

## Container

```bash
docker build -f OfferManagement/Dockerfile -t offer-management-agent .   # from repo root
```

## Tests

```bash
TEST_DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/<scratch_db> pytest OfferManagement/tests -q
```

Database tests are skipped when `TEST_DATABASE_URL` is unset. Agent tests use `sales_common.testing.ScriptLlm` (no API key).
