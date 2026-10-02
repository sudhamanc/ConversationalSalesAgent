# Payment Agent

**Type:** Transactional agent (payment phase)
**Framework:** Google ADK 2.10 (A2A service)
**Package:** `payment_agent` (project `payment-agent`)
**A2A name:** `payment_agent` (hardcoded) - local port 8206
**Contract:** [README: Agent Service Guide](../README.md#agent-service-guide)

---

## Purpose

Credit checks, payment method validation/tokenization, and payment processing for an
order. On success the order is marked `paid`, a `payment_confirmation` notification is
queued in the outbox, and `payment_context` is exported to the gateway.

## Layout

```text
PaymentAgent/
├── pyproject.toml            # depends on sales-common
├── Dockerfile                # build context = repo root
├── payment_agent/
│   ├── __init__.py           # build_agent, root_agent
│   ├── agent.py              # build_agent(model=None) -> Agent
│   ├── prompts.py            # PAYMENT_AGENT_INSTRUCTION (static_instruction)
│   ├── server.py             # app = create_a2a_app(root_agent)
│   └── tools/
│       ├── payment_tools.py  # validate / tokenize / process / saved methods
│       ├── credit_tools.py   # simulated credit check + report
│       └── billing_tools.py  # invoice, history, installment plan (simulated)
└── tests/                    # conftest.py, test_tools.py, test_agent.py
```

## Agent configuration

| Attribute | Value |
|---|---|
| `static_instruction` | `PAYMENT_AGENT_INSTRUCTION` (no transfer instructions) |
| `instruction` | `sales_common.prompts.JOURNEY_CONTEXT_INSTRUCTION` |
| Callbacks | `before_agent_callback=[import_forwarded_context]`, `after_tool_callback=[export_context_delta]` |
| Generation | `generate_config(temperature=0.0, max_output_tokens=2048)` (safety from `SAFETY_*` env) |
| Model | `GEMINI_MODEL` (required, no default) |

## Tools

| Tool | Persistence | Notes |
|---|---|---|
| `validate_payment_method` | none | Luhn check (cards), 9-digit routing (ACH) |
| `tokenize_payment_method` | `customer_payment_methods` (when a customer is known) | Opaque random token `tok_<secrets.token_urlsafe(24)>`, never derived from card/account data |
| `add_payment_method` | `customer_payment_methods` | Upsert by token (default flag, nickname); returns a dict |
| `get_payment_methods` | SELECT `customer_payment_methods` | Customer's active methods (masked) + static `supported_methods` |
| `process_payment` | `payments`, `payment_events`, `payment_rate_limit`, `orders.status`, `notifications` | See below |
| `check_business_credit`, `get_credit_report` | none | Rule-based simulation |
| `generate_invoice`, `get_payment_history`, `setup_payment_plan` | none | Simulated |

### Saved payment methods (`customer_payment_methods`)

- Tokenization is simulated, but tokens are opaque: `tok_` + `secrets.token_urlsafe(24)`, random per call.
- Only masked data is stored: `payment_type`, `card_brand`, `last_four`, `account_type` (ACH),
  `token_expiry` (card expiry `MM/YYYY`), `is_default`, `nickname`, `status='active'`. Full card or
  account numbers and CVV are never stored, logged or returned.
- `customer_id` comes from the argument, else `state["customer_context"]`, else `state["order_context"]`.
  `tokenize_payment_method` persists only when a customer is known (`saved: true|false` in the response).
- `add_payment_method` upserts by token (a token owned by another customer is refused). Legacy
  `tok_{brand}_{last4}` tokens are still accepted (brand/last four parsed from them).
- `get_payment_methods` returns `{payment_methods: [{method_id, token, payment_type, card_brand, last_four,
  account_type, expiry, is_default, nickname, status, created_at}], count, supported_methods}`.
- `process_payment` accepts any non-empty token (new opaque and legacy `tok_...` formats).

### `process_payment`

Arguments: `amount, payment_method_token, description, invoice_id, order_id, customer_name,
customer_email, customer_phone, idempotency_key, currency`. Missing `order_id` / customer
contact fields default from `state["order_context"]` (`order_id`, `customer_name`,
`contact_email`, `contact_phone`). An `order_id` is required and must exist in `orders`.

One PostgreSQL transaction (`sales_common.db.transaction()`):

1. `pg_advisory_xact_lock(hashtext(idempotency_key))`; replay of a known key returns the stored result (`idempotent: true`).
2. `SELECT ... FROM orders ... FOR UPDATE`; an already `completed` payment for the order is returned (`idempotent: true`).
   Otherwise only orders in `pending_payment` or `draft` are payable: any other status returns
   `{success: false, error: "Order <id> cannot be paid in status <status>"}` with no charge, no `payments` row,
   no rate-limit increment and no notification.
3. Hourly rate limit (5 attempts/customer) via `payment_rate_limit`.
4. `payments` row `initiated -> processing -> completed | failed`, each transition in `payment_events`.
5. Velocity check (10 completed payments or $500k per customer per 24h).
6. On success `UPDATE orders SET status='paid'`.
7. `notifications.enqueue("payment_confirmation", ..., conn=conn)` with args
   `order_id, customer_name, payment_status ("success"|"failed"), amount, currency, payment_method, transaction_id, failure_reason`.

Success response fields: `success, payment_id, transaction_id, idempotency_key, order_id, amount,
currency, status="completed", payment_method_token, description, invoice_id, order_status="paid",
email_confirmation_queued, notification_id, message` (+ `_context_update` added by the callback).
Decline: `success=false, payment_id, idempotency_key, status="failed", failure_reason, error`.

Session state written on success (exported to the gateway as `_context_update.payment_context`):

```json
{"transaction_id": "TXN-...", "order_id": "ORD-...", "customer_id": "CUST-...",
 "amount": 249.0, "status": "completed", "payment_method": "tok_Qm9w..."}
```

There is no in-memory fallback: without `DATABASE_URL`, `sales_common.db` raises.

## Conversation behaviour

- The gateway workflow engages this agent after installation scheduling with an explicit
  message ("Installation is scheduled for order <id>; total <amount>. Start payment.").
  The agent asks for payment details immediately (no SuperAgent opener callback any more).
- After payment the agent replies with the one-line JSON block the UI parses:
  `{"payment_confirmation": true, "amount": ..., "payment_method": "...", "transaction_id": "...", "status": "Approved"}`
- The agent cannot transfer; the gateway routes the next step (order confirmation).

## Tests

```bash
TEST_DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa_test_payment \
  venv/bin/python -m pytest PaymentAgent/tests -q
```

DB tests run `sales_common.migrate.run(seed=True)` and are skipped without `TEST_DATABASE_URL`.
Agent tests use `sales_common.testing.ScriptLlm`.

## Known issues

Fixed: `process_payment` refuses orders that are not `pending_payment`/`draft` (cancelled, expired,
paid, fulfilled); tokens are opaque random values and saved methods are persisted (masked) in
`customer_payment_methods`; the unused pydantic-v1 `models/schemas.py` package was removed.
