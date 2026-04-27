# Customer Communication Agent

**Type:** Cross-Cutting Agent (Notification & Communication)
**Framework:** Google ADK 1.20.0+
**Package:** `customer_communication_agent`
**Status:** ✅ Deployed in SuperAgent

---

## Purpose

The Customer Communication Agent handles **automated and manual notifications** across the entire sales lifecycle. It sends confirmations, reminders, and status updates via email (SMTP) and maintains a full notification history with deduplication.

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `customer_communication_agent` (hardcoded) |
| **Model** | `os.getenv("GEMINI_MODEL")` — no default |
| **Temperature** | 0.0 (deterministic) |
| **Max Tokens** | 2048 |
| **Database** | Unified `sales_agent.db` → `notifications`, `dedup_cache` tables |
| **SMTP** | Real email when `SMTP_ENABLED=true` |

### Component Structure

```
CustomerCommunicationAgent/
├── customer_communication_agent/
│   ├── __init__.py
│   ├── agent.py                    # Agent definition
│   ├── prompts.py                  # System instructions
│   ├── models/
│   │   └── __init__.py             # Notification, NotificationType, NotificationStatus
│   ├── tools/
│   │   └── notification_tools.py   # All notification functions
│   └── utils/
│       └── db.py                   # SQLite persistence helpers
└── tests/
```

### Database Tables (2 tables — Communication Domain)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `notifications` | Notification history | notification_id (PK), notification_type, recipient_email, subject, message, customer_id, order_id, status, sent_at |
| `dedup_cache` | Prevent duplicate sends | dedup_key (PK), sent_at |

---

## Tools (10 Functions)

### Notification Senders

| Tool | Trigger Event | Notification Type |
|------|--------------|-------------------|
| `send_order_confirmation` | OrderAgent creates order | `ORDER_CONFIRMATION` |
| `send_quote_confirmation` | OfferManagement generates quote | `QUOTE_CONFIRMATION` |
| `send_payment_notification` | PaymentAgent processes payment | `PAYMENT_SUCCESS` / `PAYMENT_FAILED` |
| `send_installation_reminder` | Before scheduled install date | `INSTALL_REMINDER` |
| `send_service_activated_notification` | Activation completes | `SERVICE_ACTIVATED` |
| `send_abandoned_cart_reminder` | Cart expires (TTL cleanup) | `ABANDONED_CART` |
| `send_order_status_update` | Any order status change | `ORDER_STATUS_UPDATE` |
| `send_install_scheduled_notification` | Install scheduled | `INSTALL_SCHEDULED` |
| `send_install_dispatched_notification` | Technician dispatched | `INSTALL_DISPATCHED` |

### Query Tools

| Tool | Signature | Purpose |
|------|-----------|---------|
| `get_notification_history` | `(customer_id, order_id, notification_type, limit)` | Query past notifications |

### Features

- **Deduplication** — 5-minute window prevents duplicate sends for same event
- **Dual storage** — In-memory cache + SQLite persistence
- **Real SMTP** — When `SMTP_ENABLED=true`, sends actual emails
- **Cross-agent triggers** — Other agents call notification tools via `sys.modules`

---

## Cross-Agent Integration Pattern

Other agents trigger notifications using `sys.modules`:

```python
comms = sys.modules.get("customer_communication_agent.tools.notification_tools")
if comms:
    comms.send_order_confirmation(order_id=..., customer_name=..., ...)
```

### Notification Timeline

| Stage | Triggered By | Notification |
|-------|-------------|--------------|
| Quote generated | OfferManagementAgent | `QUOTE_CONFIRMATION` |
| Order placed | OrderAgent | `ORDER_CONFIRMATION` |
| Payment processed | PaymentAgent | `PAYMENT_SUCCESS` |
| Install scheduled | ServiceFulfillmentAgent | `INSTALL_SCHEDULED` |
| Technician dispatched | ServiceFulfillmentAgent | `INSTALL_DISPATCHED` |
| Install complete | ServiceFulfillmentAgent | `INSTALL_COMPLETE` |
| Service activated | ServiceFulfillmentAgent | `SERVICE_ACTIVATED` |
| Cart abandoned | DB lifecycle cleanup | `ABANDONED_CART` |
| Order cancelled | DB lifecycle cleanup | `ORDER_CANCELLED` |

---

## Conversation Behavior

### When Invoked
SuperAgent routes to CustomerCommunicationAgent for: "Send confirmation", "Resend reminder", "Show notification history"

---

## Integration with SuperAgent

Loaded via **importlib isolation** in `SuperAgent/super_agent/sub_agents/customer_communication/agent.py`. Agent name `customer_communication_agent` is hardcoded.
