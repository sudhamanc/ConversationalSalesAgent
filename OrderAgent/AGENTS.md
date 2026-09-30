# Order Agent

**Type:** Transactional Agent (Transaction Phase)
**Framework:** Google ADK 2.10 (A2A service)
**Package:** `order_agent` (project `order-agent`)
**A2A name:** `order_agent` (hardcoded) · local port 8205
**Contract:** [docs/agent-service-guide.md](../docs/agent-service-guide.md)

---

## Purpose

The Order Agent manages the **cart-to-order lifecycle**: cart creation, order placement, contract generation, order modification, status updates and cancellation. Installation scheduling and payment are separate services; the gateway workflow routes the customer to them (this agent only tells the customer the next step).

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `order_agent` (hardcoded) |
| **Model** | `GEMINI_MODEL` via `sales_common.config.model_name()` — no default |
| **Instructions** | `static_instruction` = `ORDER_AGENT_INSTRUCTION`; `instruction` = `JOURNEY_CONTEXT_INSTRUCTION` |
| **Callbacks** | `before_agent_callback=[import_forwarded_context]`, `after_tool_callback=[export_context_delta]` |
| **Temperature** | 0.0 (deterministic) · max 2048 output tokens (`generate_config`) |
| **Database** | PostgreSQL (`DATABASE_URL`) → `carts`, `cart_items`, `orders`, `order_items` via `sales_common.db` |

### Component Structure

```
OrderAgent/
├── pyproject.toml                  # order-agent, depends on sales-common
├── Dockerfile                      # build context = repo root
├── order_agent/
│   ├── __init__.py                 # exports build_agent, root_agent
│   ├── agent.py                    # build_agent(model=None) -> Agent
│   ├── prompts.py                  # static domain prompt
│   ├── server.py                   # app = create_a2a_app(root_agent)
│   ├── models/                     # Order / OrderStatus
│   ├── tools/
│   │   ├── cart_tools.py           # cart CRUD
│   │   └── order_tools.py          # order lifecycle + contract
│   └── utils/database.py           # carts/orders persistence (sales_common.db)
└── tests/                          # cart->order flow (Postgres) + ScriptLlm agent test
```

Persistence is PostgreSQL only (see `db/README.md`); the legacy SQLite file was removed.

### Database Tables (Order domain)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `carts` | Shopping cart state | cart_id (PK), customer_id, total_amount, status, expires_at |
| `cart_items` | Items in cart | id (identity PK), cart_id (FK), service_type, price, quantity, subtotal |
| `orders` | Placed orders | order_id (PK), customer_id, offer_id (FK → quotes), status, total_amount |
| `order_items` | Items in order | id (identity PK), order_id (FK), service_type, price, quantity, subtotal |

Schema lives in `db/migrations/001_sales_schema.sql`; the agent never creates tables. Writes use `INSERT ... ON CONFLICT DO UPDATE` and replace item rows.

---

## Tools (11 functions)

| Tool | Signature | Tables | Purpose |
|------|-----------|--------|---------|
| `create_cart` | `(customer_id)` | `carts` | New cart (`cart_id` = `CART-<timestamp>-<nnn>`) |
| `add_to_cart` | `(cart_id, service_type, price, quantity)` | `carts`, `cart_items` | Add/merge line item |
| `remove_from_cart` | `(cart_id, service_type)` | `carts`, `cart_items` | Remove line item |
| `get_cart` | `(cart_id)` | SELECT | Cart with items |
| `clear_cart` | `(cart_id)` | `carts`, `cart_items` | Empty cart |
| `create_order` | `(customer_name, service_address, service_type, contact_phone, customer_id, contact_email, price, offer_id)` | `orders`, `order_items`, `quotes`, `notifications` | Create order (pending_payment) |
| `update_order_status` | `(order_id, new_status, notes)` | `orders` | Transition status |
| `get_order` | `(order_id)` | SELECT | Order with items |
| `modify_order` | `(order_id, service_type, price)` | `orders`, `order_items` | Change a draft/pending order |
| `generate_contract` | `(order_id)` | SELECT | Contract summary |
| `cancel_order` | `(order_id, reason)` | `orders` | Cancel |

Cart tool responses: `{success, cart_id, cart: {cart_id, customer_id, items[{service_type, price, quantity, subtotal}], total_amount, status, created_at, updated_at, expires_at}, message}`.

### create_order

One transaction:
1. `orders` upsert and `order_items` rows (status `pending_payment`).
2. `sales_common.repositories.quotes.mark_ordered(offer_id, conn=conn)`.
3. `notifications.enqueue("order_confirmation", ..., conn=conn)` (outbox; delivered by the communication service).

- `customer_id`, `offer_id` and `price` fall back to `customer_context` / `offer_context` from state.
- `orders.offer_id` is a foreign key to `quotes`. An unknown `offer_id` is dropped (stored as NULL), and the response carries a `warning`.
- Writes `order_context` = `{order_id, customer_id, customer_name, contact_email, contact_phone, service_address, service_type, price, offer_id, total_amount, status}`. `export_context_delta` returns it as `_context_update.order_context`.
- Response: `success, order_id, customer_name, customer_id, service_address, service_type, contact_phone, contact_email, offer_id, status, total_amount, created_at, email_confirmation_sent, email_notification_id, message[, warning]`.

### Order State Machine

```
draft → pending_payment → paid (payment service) → confirmed → fulfilled (fulfillment service)
                      └→ cancelled (maintenance: expired pending orders)
```

### Output format parsed by the UI

After payment, the agent confirms the order and emits one line of JSON:
`{"order_confirmation": true, "order_id": ..., "customer": ..., "service": ..., "address": ..., "monthly_total": ..., "installation_date": ..., "payment_status": "Paid", "order_status": "Confirmed", "contact_email": ..., "whats_next": [...]}`

---

## Conversation Behavior

- The gateway routes: "Place order", "Add to cart", "Checkout", "Proceed with this quote".
- After `create_order` the agent says the next step is installation scheduling, then payment. It never transfers; the gateway workflow routes the next turn.

## Running

```bash
uv pip install -e libs/sales_common -e OrderAgent
GEMINI_MODEL=... DATABASE_URL=postgresql://... PUBLIC_URL=http://localhost:8205 \
  uvicorn order_agent.server:app --host 0.0.0.0 --port 8205
TEST_DATABASE_URL=postgresql://.../scratch pytest OrderAgent/tests -q
```

## Known issues

Fixed: `order_id`, `cart_id` and fallback `customer_id` now come from `sales_common.ids.new_id`, so repeat orders no longer collide.

- Carts and orders are written with `expires_at = NULL`, so `sales_common.maintenance` never expires them.
