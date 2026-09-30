# Order Agent

**Order lifecycle management and contract generation for the B2B Conversational Sales Agent**, served as an independent **A2A service** (`order_agent`).

See [AGENTS.md](AGENTS.md) for tools, tables, journey context and output formats, and [docs/agent-service-guide.md](../docs/agent-service-guide.md) for the service contract.

## Overview

The Order Agent handles PRE-FULFILLMENT operations:

- **Cart Management:** create, update and manage shopping carts
- **Order Creation:** create orders (status `pending_payment`); customer IDs are auto-generated when missing
- **Order Modification:** update draft/pending orders
- **Contract Generation:** service contracts with standard terms
- **Order Status Management:** draft → pending_payment → paid → confirmed
- **Order Cancellation:** with reason tracking

Installation scheduling (ServiceFulfillmentAgent) and payment (PaymentAgent) are separate services. After creating an order, this agent tells the customer the next step, and the gateway workflow routes the conversation.

Side effects of `create_order` are transactional:
- the source quote is marked `ordered`
- an `order_confirmation` notification is enqueued in the `notifications` outbox

## Run locally

```bash
uv pip install -e libs/sales_common -e OrderAgent
export GEMINI_MODEL=gemini-3-flash-preview GOOGLE_API_KEY=...
export DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa
export PUBLIC_URL=http://localhost:8205
uvicorn order_agent.server:app --host 0.0.0.0 --port 8205
```

- Agent card: `GET /.well-known/agent-card.json`
- Health: `GET /healthz`

## Container

```bash
docker build -f OrderAgent/Dockerfile -t order-agent .   # from repo root
```

## Tests

```bash
TEST_DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/<scratch_db> pytest OrderAgent/tests -q
```

Database tests are skipped when `TEST_DATABASE_URL` is unset. Agent tests use `sales_common.testing.ScriptLlm` (no API key).

## Layout

```
OrderAgent/
├── pyproject.toml / Dockerfile / README.md / AGENTS.md
├── order_agent/
│   ├── agent.py        # build_agent(), root_agent
│   ├── server.py       # A2A app
│   ├── prompts.py
│   ├── models/         # Order, OrderStatus
│   ├── tools/          # cart_tools.py, order_tools.py
│   └── utils/          # database.py (PostgreSQL), logger.py
└── tests/
```
