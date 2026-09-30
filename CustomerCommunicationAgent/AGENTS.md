# Customer Communication Agent

**Type:** A2A agent service + notification outbox dispatcher
**Framework:** Google ADK 2.10 (`sales_common`), PostgreSQL
**Package:** `customer_communication_agent` (distribution `customer-communication-agent`)
**Contract:** [docs/agent-service-guide.md](../docs/agent-service-guide.md)

---

## Purpose

Delivers every customer notification in the system. Other services never call this agent: they
insert a `pending` row into the shared `notifications` outbox with
`sales_common.notifications.enqueue(...)` inside their business transaction. This service's
dispatcher renders and delivers those rows (SMTP or simulated). The LLM agent handles explicit
user requests (resend a confirmation, send an installation/activation notice, show history).

## Layout

```text
CustomerCommunicationAgent/
├── pyproject.toml                 # customer-communication-agent; depends on sales-common
├── Dockerfile                     # build context = repo root
├── customer_communication_agent/
│   ├── agent.py                   # build_agent(model=None) ; root_agent
│   ├── prompts.py                 # static_instruction (not templated)
│   ├── server.py                  # create_a2a_app(root_agent, extra_lifespan=dispatcher_lifespan)
│   ├── dispatcher.py              # dispatch_pending(), background loop, dedup, retries
│   ├── templates.py               # subject/body per notification type (TEMPLATES, TEMPLATE_ARGS)
│   ├── delivery.py                # SMTP settings + send_email (never logs passwords)
│   ├── models/__init__.py         # NotificationStatus, legacy type aliases
│   ├── tools/notification_tools.py# send_* tools + get_notification_history
│   └── utils/db.py                # read queries (history, single row)
├── data/                          # legacy SQLite files (unused at runtime; kept for reference)
└── tests/                         # pytest; PostgreSQL tests need TEST_DATABASE_URL
```

## Outbox flow

1. Producer: `notifications.enqueue(type, recipient_email=..., args={...}, order_id=..., conn=conn)`
   → `notifications(status='pending', metadata_json={"template": type, "args": {...}})`.
2. `dispatch_pending(limit=50)` (one transaction):
   `SELECT * FROM notifications WHERE status='pending' AND <retry backoff elapsed>
   ORDER BY created_at, notification_id FOR UPDATE SKIP LOCKED LIMIT n`.
3. Render with `templates.render(template, args)`; unknown templates use `generic`.
4. Dedup: key `<template>:<recipient>[:<quote_id|cart_id|order_id>][:<new_status|payment_status>]`
   in `dedup_cache`, 5-minute window, guarded by `pg_advisory_xact_lock` → `status='deduped'`.
5. Deliver: email via SMTP when `SMTP_ENABLED=true` → `sent`; otherwise `simulated`.
   SMS is always simulated. `abandoned_cart` is email-only.
6. Every processed row: `attempts += 1`, `updated_at`, `subject`, `message`; success sets `sent_at`
   and `dedup_cache`. An SMTP error leaves the row `pending` with `error`; after 3 attempts it is
   `failed`. A row with no deliverable channel fails immediately.
   Retry backoff: a row with `attempts > 0` is not picked again until `updated_at` is at least
   `NOTIFY_RETRY_SECONDS * attempts` seconds old (60 s, then 120 s with the default).
7. `dispatcher_lifespan` runs `dispatch_pending` every `NOTIFY_POLL_SECONDS` via
   `asyncio.to_thread`; on shutdown it lets an in-flight batch finish (max 30 s), then stops.

Statuses: `pending`, `sent`, `simulated`, `deduped`, `failed`.

## Template args (producers must supply these in `args`)

`customer_name` falls back to `company_name`, then "Valued Customer". `order_id` falls back to the
row's `order_id` column. Missing values render as `N/A` / `TBD`.

| Type | Args |
|---|---|
| `quote_confirmation` | `quote_id`, `customer_name`, `items_summary`, `monthly_total`, `term_months`, `total_discount` |
| `order_confirmation` | `order_id`, `customer_name`, `service_type`, `total_amount` |
| `payment_confirmation` | `order_id`, `customer_name`, `payment_status` (`success`/`failed`), `amount`, `currency`, `payment_method`, `transaction_id`, `failure_reason` (shown when failed) |
| `installation_scheduled` | `order_id`, `customer_name`, `appointment_date`, `window`, `service_address` |
| `installation_reminder` | `order_id`, `customer_name`, `installation_date`, `installation_time`, `service_address` |
| `installation_complete` | `order_id`, `customer_name`, `equipment_installed` (list) |
| `service_activated` | `order_id`, `customer_name`, `service_type`, `account_number` (or `account_id`), `circuit_id` |
| `abandoned_cart` | `cart_id`, `customer_name`, `cart_items`, `total_amount` |
| `order_status_update` | `order_id`, `customer_name`, `old_status`, `new_status`, `status_message` |
| `quote_expired` | `quote_id`, `customer_name`, `expired_at` |
| `order_cancelled` | `order_id`, `customer_name`, `reason` |
| `escalation` | `order_id`, `customer_name`, `reason`, `status` |
| `install_dispatched` | `order_id`, `customer_name`, `technician_name`, `technician_phone` |
| any other (`generic`) | `subject`, `message`, `customer_name` (else lists the args) |

`install_dispatched` is enqueued by ServiceFulfillment `dispatch_technician`.

## Tools (LLM-facing)

`send_order_confirmation`, `send_quote_confirmation`, `send_payment_notification`,
`send_installation_reminder`, `send_service_activated_notification`,
`send_abandoned_cart_reminder`, `send_order_status_update`, `get_notification_history`.

Each `send_*` tool enqueues one row and immediately calls
`dispatch_pending(limit=1, notification_id=...)`, then returns the real status
(`sent` / `simulated` / `deduped` / `queued` / failure with `error`). Missing email/phone fall back
to `order_context.contact_email` / `contact_phone`; `customer_id` comes from `customer_context`.

## Environment

Standard agent variables (`GEMINI_MODEL`, `GOOGLE_API_KEY`, `DATABASE_URL`, `PUBLIC_URL`, ...) from
the guide, plus:

| Variable | Default | Notes |
|---|---|---|
| `SMTP_ENABLED` | `false` | `true` sends real email; startup fails without `SMTP_USER`/`SMTP_PASSWORD` |
| `SMTP_HOST` | `smtp.gmail.com` | |
| `SMTP_PORT` | `587` | STARTTLS |
| `SMTP_USER` | — | login and From address |
| `SMTP_PASSWORD` | — | secret (Gmail App Password); never logged |
| `SMTP_FROM_NAME` | `B2B Sales Notifications` | |
| `NOTIFY_POLL_SECONDS` | `10` | dispatcher poll interval (> 0) |
| `NOTIFY_RETRY_SECONDS` | `60` | retry backoff base (>= 0); a failed row waits `value * attempts` seconds |

## Known issues

- Fixed: pending rows are dispatched in insertion order (`notifications.seq`, migration
  `005_notifications_seq.sql`), including rows created within the same second.

## Tests

```bash
TEST_DATABASE_URL=postgresql://... venv/bin/python -m pytest CustomerCommunicationAgent/tests -q
```

Tests never send email: `SMTP_ENABLED` is removed from the environment, and SMTP paths
monkeypatch `customer_communication_agent.dispatcher.send_email`.
