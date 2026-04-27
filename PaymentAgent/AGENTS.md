# Payment Agent

**Type:** Transactional Agent (Transaction Phase)
**Framework:** Google ADK 1.20.0+
**Package:** `payment_agent`
**Status:** ✅ Deployed in SuperAgent

---

## Purpose

The Payment Agent handles **credit checks, payment validation, tokenization, and payment authorization**. It processes payments for confirmed orders and updates order status upon successful payment.

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `payment_agent` (hardcoded) |
| **Model** | `os.getenv("GEMINI_MODEL")` — no default |
| **Temperature** | 0.0 (deterministic) |
| **Max Tokens** | 2048 |
| **Database** | Unified `sales_agent.db` → `payments` table + reads/writes `orders` |

### Component Structure

```
PaymentAgent/
├── payment_agent/
│   ├── __init__.py
│   ├── agent.py                    # Agent definition
│   ├── prompts.py                  # System instructions
│   ├── tools/
│   │   ├── payment_tools.py        # Core payment processing
│   │   ├── credit_tools.py         # Credit check simulation
│   │   └── billing_tools.py        # Invoice/billing utilities
│   └── utils/
│       └── logger.py
└── tests/
```

### Database Tables (1 table — Payment Domain)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `payments` | Payment records | payment_id (PK), order_id (FK), customer_id, transaction_id, amount, status, credit_score, payment_method, expires_at |

---

## Tools

### Core Payment Tools (payment_tools.py)

| Tool | Signature | Tables | Purpose |
|------|-----------|--------|---------|
| `validate_payment_method` | `(payment_type, card_number, routing_number, account_number)` | None | Validate payment details (Luhn check) |
| `process_payment` | `(amount, payment_method_token, description, invoice_id, order_id, customer_name, customer_email, customer_phone)` | `payments` INSERT, `orders` UPDATE→paid | Process payment and update order |
| `get_payment_methods` | `(customer_id)` | None (simulated) | List available payment methods |
| `tokenize_payment_method` | `(payment_type, card_number, expiry_month, expiry_year, cvv, ...)` | None | Generate payment token |

### Credit Tools (credit_tools.py)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `check_business_credit` | `(company_name, tax_id)` | Simulated credit check (returns score 650-800) |
| `get_credit_report` | `(company_name)` | Detailed credit report |

### Billing Tools (billing_tools.py)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `generate_invoice` | `(order_id, ...)` | Generate invoice document |
| `get_payment_history` | `(customer_id)` | Payment history lookup |
| `setup_payment_plan` | `(order_id, num_installments)` | Configure installment plan |

### Cross-Agent Integration
- Reads `orders` table to get customer_id for payment association
- Updates `orders.status` → `paid` on successful payment
- Auto-sends `PAYMENT_SUCCESS` or `PAYMENT_FAILED` notification via CustomerCommunicationAgent

---

## Conversation Behavior

### When Invoked
SuperAgent routes to PaymentAgent for: "Process payment", "Credit check", "Pay for this order"

### Response Pattern
> "✅ Payment authorized! Transaction #TXN-12345. Credit score: 720. Order #ORD-12345 status updated to **paid**."

---

## Integration with SuperAgent

Loaded via **importlib isolation** in `SuperAgent/super_agent/sub_agents/payment/agent.py`. Agent name `payment_agent` is hardcoded.
