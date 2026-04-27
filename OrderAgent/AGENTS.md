# Order Agent

**Type:** Transactional Agent (Transaction Phase)
**Framework:** Google ADK 1.20.0+
**Package:** `order_agent`
**Status:** ✅ Deployed in SuperAgent

---

## Purpose

The Order Agent manages the **cart-to-order lifecycle**: cart creation, order placement, contract generation, order modification, and cancellation. It creates orders from accepted quotes and manages the full order state machine.

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `order_agent` (hardcoded) |
| **Model** | `os.getenv("GEMINI_MODEL")` — no default |
| **Temperature** | 0.0 (deterministic) |
| **Max Tokens** | 2048 |
| **Database** | Unified `sales_agent.db` → `carts`, `cart_items`, `orders`, `order_items` tables |
| **Fallback DB** | `OrderAgent/data/orders.db` |

### Component Structure

```
OrderAgent/
├── order_agent/
│   ├── __init__.py
│   ├── agent.py                    # Agent definition
│   ├── prompts.py                  # System instructions
│   ├── models/                     # Order/OrderStatus Pydantic models
│   ├── tools/
│   │   └── order_tools.py          # Order CRUD operations
│   └── utils/
│       └── database.py             # SQLite persistence (carts + orders)
└── tests/
```

### Database Tables (4 tables — Order Domain)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `carts` | Shopping cart state | cart_id (PK), customer_id, total_amount, status, expires_at |
| `cart_items` | Items in cart | id (PK), cart_id (FK), service_type, price, quantity |
| `orders` | Placed orders | order_id (PK), customer_id, offer_id (FK→quotes), status, total_amount |
| `order_items` | Items in order | id (PK), order_id (FK), service_type, price, quantity |

---

## Tools (6 Functions)

| Tool | Signature | Tables Written | Purpose |
|------|-----------|----------------|---------|
| `create_order` | `(customer_name, service_address, service_type, contact_phone, customer_id, contact_email, price, offer_id)` | `orders`, `order_items`, `carts`, `cart_items` INSERT | Create cart + order from quote |
| `update_order_status` | `(order_id, new_status, notes)` | `orders` UPDATE | Transition order state |
| `get_order` | `(order_id)` | — (SELECT only) | Retrieve order details |
| `modify_order` | `(order_id, service_type, price)` | `orders`, `order_items` DELETE+INSERT | Modify order items |
| `generate_contract` | `(order_id)` | — (read only) | Generate contract summary |
| `cancel_order` | `(order_id, reason)` | `orders` UPDATE status→cancelled | Cancel an order |

### Order State Machine

```
draft → pending_payment → paid → fulfilled
                      └→ cancelled (TTL: 48h)
                              └→ escalated (stuck >7 days)
```

### Cross-Agent Integration
- Calls `mark_quote_ordered(offer_id)` on OfferManagementAgent via `sys.modules`
- Auto-sends `ORDER_CONFIRMATION` notification via CustomerCommunicationAgent
- PaymentAgent updates `orders.status` → `paid`
- ServiceFulfillmentAgent updates `orders.status` → `fulfilled`

---

## Conversation Behavior

### When Invoked
SuperAgent routes to OrderAgent for: "Place order", "Add to cart", "Checkout", "Proceed with this quote"

### Response Pattern
> "Order #ORD-12345 created! Total: $X,XXX/mo. Status: pending_payment. Would you like to proceed with payment?"

---

## Integration with SuperAgent

Loaded via **importlib isolation** in `SuperAgent/super_agent/sub_agents/order/agent.py`. Agent name `order_agent` is hardcoded.
