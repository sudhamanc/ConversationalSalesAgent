# Customer Communication Agent

A2A service (`customer_communication_agent`) that delivers customer notifications for the
Conversational Sales Agent: quote, order, payment, installation, activation, abandoned-cart,
cancellation and escalation messages.

It has two parts:

- **Outbox dispatcher.** Other services enqueue `pending` rows in the PostgreSQL
  `notifications` table (`sales_common.notifications.enqueue`). A background loop in this
  service renders and delivers them every `NOTIFY_POLL_SECONDS`, with de-duplication and retries.
- **LLM agent.** It handles explicit requests such as "resend the order confirmation", "send the
  installation reminder" or "show notification history". Its `send_*` tools enqueue a row and
  dispatch it immediately, so the reply reports the real delivery status.

Architecture details, template args and statuses are in [AGENTS.md](AGENTS.md). Service
conventions are in [docs/agent-service-guide.md](../docs/agent-service-guide.md).

## Run locally

```bash
uv pip install -p venv/bin/python -e libs/sales_common -e CustomerCommunicationAgent
python -m sales_common.migrate --seed           # once per database

export DATABASE_URL=postgresql://csa:...@127.0.0.1:5432/csa
export GEMINI_MODEL=gemini-3-flash-preview GOOGLE_API_KEY=...
export PUBLIC_URL=http://localhost:8093
uvicorn customer_communication_agent.server:app --host 0.0.0.0 --port 8093
```

- `GET /healthz`: returns 503 when the database is unreachable.
- `GET /.well-known/agent-card.json`: the A2A agent card.

### Docker

The build context is the repo root:

```bash
docker build -f CustomerCommunicationAgent/Dockerfile -t customer-communication-agent .
```

## Sending a notification from another service

```python
from sales_common import db, notifications

with db.transaction() as conn:
    conn.execute("INSERT INTO orders ...", (...))
    notifications.enqueue(
        "order_confirmation",
        recipient_email=email,
        order_id=order_id,
        customer_id=customer_id,
        args={"order_id": order_id, "customer_name": company, "service_type": "Fiber 1G",
              "total_amount": 1234.50},
        conn=conn,
    )
```

The notification is committed with the order. If the order transaction rolls back, the
notification is discarded too. If this service is down, the notification is delivered when it
starts.

## Delivery outcomes

| Status | Meaning |
|---|---|
| `pending` | Waiting for delivery, or retrying after an SMTP error (`error` holds the reason; next try after `NOTIFY_RETRY_SECONDS * attempts`) |
| `sent` | Delivered through SMTP |
| `simulated` | `SMTP_ENABLED` is off, so delivery was only logged |
| `deduped` | The same template, recipient and reference was sent within the last 5 minutes |
| `failed` | Delivery failed 3 times, or the row has no deliverable channel |

SMS is always simulated. Abandoned-cart reminders go by email only.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `GEMINI_MODEL` | — (required) | |
| `GOOGLE_API_KEY` | — | or Vertex AI env |
| `DATABASE_URL` | — (required) | PostgreSQL libpq URL |
| `PUBLIC_URL` | — (required) | URL advertised in the agent card |
| `SMTP_ENABLED` | `false` | `true` sends real email |
| `SMTP_HOST` | `smtp.gmail.com` | |
| `SMTP_PORT` | `587` | STARTTLS |
| `SMTP_USER` | — | Required when SMTP is enabled. Also used as the From address |
| `SMTP_PASSWORD` | — | Required when SMTP is enabled. Secret, never logged. For Gmail, use an App Password |
| `SMTP_FROM_NAME` | `B2B Sales Notifications` | |
| `NOTIFY_POLL_SECONDS` | `10` | Dispatcher poll interval |
| `NOTIFY_RETRY_SECONDS` | `60` | Retry backoff base; a failed row waits `value * attempts` seconds before the next try |
| `LOG_LEVEL` | `INFO` | |

If `SMTP_ENABLED=true` is set without `SMTP_USER`/`SMTP_PASSWORD`, the service fails at startup.

`NOTIFICATION_DB_PATH` and `SALES_AGENT_DB_PATH` have been removed. The SQLite files in `data/`
are legacy data and are not used at runtime.

## Tests

```bash
TEST_DATABASE_URL=postgresql://csa:...@127.0.0.1:5432/csa_test_comms \
  venv/bin/python -m pytest CustomerCommunicationAgent/tests -q
```

Without `TEST_DATABASE_URL`, the PostgreSQL tests are skipped. Template and agent-construction
tests still run. The tests never send real email.
