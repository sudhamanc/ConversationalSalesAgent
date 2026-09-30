# Payment Agent

A2A service `payment_agent` (ADK 2.10, PostgreSQL). It handles credit checks, payment method
validation/tokenization, and payment processing for an order. Details: [AGENTS.md](AGENTS.md).
Service contract: [docs/agent-service-guide.md](../docs/agent-service-guide.md).

## Scope

- **Does:** credit checks, payment method validation, opaque tokenization and saved (masked)
  payment methods in `customer_payment_methods`, payment processing for orders in `pending_payment`
  or `draft` (other statuses are refused without charging), marking the order `paid`, queueing the
  `payment_confirmation` notification, and exporting `payment_context`.
- **Does not:** quote pricing (offer management), cart/order creation (order agent), or
  installation scheduling (service fulfillment).

## Run locally

```bash
uv pip install -p venv/bin/python -e libs/sales_common -e PaymentAgent
export GEMINI_MODEL=gemini-3-flash-preview GOOGLE_API_KEY=... \
       DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa \
       PUBLIC_URL=http://localhost:8206
venv/bin/python -m sales_common.migrate --seed      # once per database
venv/bin/uvicorn payment_agent.server:app --host 0.0.0.0 --port 8206
```

- Agent card: `GET /.well-known/agent-card.json`
- Health: `GET /healthz`
- See `.env.example` for the variables.

## Container

```bash
docker build -f PaymentAgent/Dockerfile -t payment-agent .   # from the repo root
```

## Tests

```bash
TEST_DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa_test_payment \
  venv/bin/python -m pytest PaymentAgent/tests -q
```

## Security note

This is an academic/demo system. Tokenization, credit checks and gateway approval are
simulated. A production deployment needs a real payment gateway and full PCI/PII controls.
