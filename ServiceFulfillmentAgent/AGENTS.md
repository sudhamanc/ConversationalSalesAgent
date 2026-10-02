# Service Fulfillment Agent

**Type:** Transactional agent — installation scheduling and post-sale fulfillment
**Framework:** Google ADK 2.10 (`google-adk==2.10.0` via `sales-common`)
**Package:** `service_fulfillment_agent` (distribution `service-fulfillment-agent`)
**Runtime:** independent A2A service (`uvicorn service_fulfillment_agent.server:app`), port 8207 locally
**Contract:** [README: Agent Service Guide](../README.md#agent-service-guide)

---

## Purpose

Books the installation appointment for a created order (before payment), then handles
provisioning, technician dispatch, installation completion and service activation. Activation is
the only point where a prospect becomes a customer (`customer_master`).

---

## Agent Configuration

| Attribute | Value |
|-----------|-------|
| Agent name | `service_fulfillment_agent` (hardcoded; the gateway routes by it) |
| Model | `sales_common.config.model_name()` — `GEMINI_MODEL`, no default |
| Temperature | 0.3 (0.0 produced empty replies after tool calls) |
| Max tokens | 2048 |
| `static_instruction` | `prompts.SERVICE_FULFILLMENT_AGENT_INSTRUCTION` (long, cacheable) |
| `instruction` | `sales_common.prompts.JOURNEY_CONTEXT_INSTRUCTION` (templated journey context) |
| Callbacks | `before_agent_callback=[import_forwarded_context]`, `after_tool_callback=[export_context_delta]` |
| Database | PostgreSQL via `sales_common.db` (`DATABASE_URL`, required — no fallback) |

### Layout

```text
ServiceFulfillmentAgent/
├── pyproject.toml / Dockerfile / README.md / AGENTS.md
├── service_fulfillment_agent/
│   ├── __init__.py          # build_agent, root_agent
│   ├── agent.py             # build_agent(model=None) -> Agent
│   ├── prompts.py
│   ├── server.py            # app = create_a2a_app(root_agent)
│   └── tools/
│       ├── _common.py           # order/fulfillment lookups, journey-state helpers
│       ├── scheduling_tools.py
│       ├── equipment_tools.py   # simulated, deterministic
│       ├── installation_tools.py
│       ├── activation_tools.py
│       └── order_tools.py       # read-only get_fulfillment_status
└── tests/                   # conftest.py, test_tools.py, test_agent.py
```

---

## Tools

Tools return JSON-serializable dicts with `success`. Errors are `{"success": false, "error": ...}`
(only `psycopg.Error` / validation errors are caught). IDs derive from `uuid4` or `sha256`
(never the per-process salted `hash()`).

| Tool | Tables | Journey keys written | Notification |
|------|--------|----------------------|--------------|
| `check_availability` | — (business rules) | — | — |
| `schedule_installation` | `orders` R, `fulfillments` INSERT/UPDATE | `order_context.installation` | `installation_scheduled` |
| `reschedule_appointment` | `fulfillments` UPDATE date | `order_context.installation` | — |
| `cancel_appointment` | `fulfillments` status → `cancelled` | `order_context.installation` | — |
| `provision_equipment` / `track_equipment` / `verify_equipment_delivery` | — (simulated) | — | — |
| `dispatch_technician` | `fulfillments` → `dispatched`, `dispatch_id`, `orders`/`customer_master` R | `order_context.installation` | `install_dispatched` (first dispatch only; to `orders.contact_email`, else `customer_master.contact_email`; skipped when neither is set) |
| `update_installation_status` | — (simulated) | — | — |
| `complete_installation` | `fulfillments` → `installed`, `orders` R | `order_context.installation` | `installation_complete` |
| `activate_service` | `fulfillments` → `activated`, `customer_master` UPSERT, `accounts` UPDATE, `orders` → `fulfilled`, `order_items` R | `order_context.status/activation/installation` | `service_activated` |
| `run_service_tests` | — (simulated) | — | — |
| `get_fulfillment_status` | `orders`, `fulfillments` R | — | — |
| `get_service_details` (not registered) | `fulfillments`, `order_items` R | — | — |

Tools read `order_context` / `payment_context` from `tool_context.state` (forwarded by the gateway)
to default `order_id`, `service_address`, `customer_id`, `customer_name`, `service_type`,
`appointment_id` and `scheduled_date`. `order_context` is updated only when its `order_id` matches.

### `schedule_installation` response (gateway contract)

The gateway's `ContextBridgePlugin` sets `temp:appointment_confirmed` when this tool returns
`success == true`; `HandoffPolicyNode` then runs `payment_agent` in the same turn.

```json
{"success": true, "appointment_id": "APT-20261005-3F9A1C", "fulfillment_id": "APT-20261005-3F9A1C",
 "order_id": "ORD-...", "customer_id": "CUST-...", "customer_name": "...", "service_address": "...",
 "scheduled_date": "2026-10-05", "window": "AM", "start_time": "08:00", "end_time": "12:00",
 "customer_contact": "...", "customer_phone": "...", "special_instructions": null,
 "status": "scheduled", "notification_queued": true, "message": "Installation scheduled for ...",
 "_context_update": {"order_context": {"...": "...", "installation": {"appointment_id": "...",
   "scheduled_date": "...", "window": "AM", "start_time": "08:00", "end_time": "12:00", "status": "scheduled"}}}}
```

Failure: `{"success": false, "error": "..."}` (no order, unknown order, cancelled/fulfilled order,
past date, weekend, bad window, database error). Re-booking an order with an open
(`scheduled`/`dispatched`) appointment moves that appointment and keeps its id.

### Activation capstone (`activate_service`, one transaction)

1. `fulfillments` → `activated` with `activation_id`, `circuit_id`, `account_id` (inserts a row if none was booked)
2. `customer_master` upsert (`first_order_id` and `created_at` kept on conflict)
3. `accounts."Existing Customer" = 'Y'`, `accounts."Current Products"` merged with ordered services
4. `orders.status = 'fulfilled'`
5. `service_activated` notification enqueued

Idempotent: a second call for an activated order returns the same ids and does not re-notify.

State machine: `scheduled → dispatched → installed → activated` (or `cancelled`).

---

## Handoffs

The agent cannot transfer. After booking it confirms the appointment and says payment is next;
the gateway's `HandoffPolicyNode` continues with `payment_agent` in the same turn (conditions:
`success == true`, payment not completed, `order_context.status` in pending_payment/draft/None).
The former SuperAgent `after_agent_callback` phrase-matching transfer was removed.

---

## Tests

```bash
TEST_DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa_test_fulfillment \
  venv/bin/python -m pytest ServiceFulfillmentAgent/tests -q
```

DB tests run `sales_common.migrate.run(seed=True)` and create their own account/order rows; they
skip without `TEST_DATABASE_URL`. Agent tests use `sales_common.testing.ScriptLlm`.
