# Customer Communication Agent

**Purpose:** Automated notification system for B2B telecommunications sales. Sends email and SMS notifications to customers throughout the order and fulfillment lifecycle.

## Overview

The CustomerCommunicationAgent handles all automated customer communications from order creation through service activation. It provides multi-channel delivery (email + SMS), deduplication to prevent spam, and comprehensive notification history tracking.

## Architecture

### Components

```
CustomerCommunicationAgent/
├── customer_communication_agent/
│   ├── __init__.py              # Package exports
│   ├── agent.py                 # ADK Agent instance with 7 tools
│   ├── prompts.py               # Comprehensive notification instructions
│   ├── models/
│   │   └── __init__.py          # Notification, NotificationType, NotificationChannel, NotificationStatus
│   ├── tools/
│   │   ├── __init__.py          # Tool exports
│   │   └── notification_tools.py # 7 notification tools
│   └── utils/
│       └── logger.py            # Logging utilities
└── README.md                    # This file
```

### Integration with SuperAgent

The CustomerCommunicationAgent is integrated into SuperAgent using the **importlib isolation pattern** to prevent parent-binding conflicts with ADK. Located at: `SuperAgent/super_agent/sub_agents/customer_communication/agent.py`

## Notification Tools (7 Total)

### 1. Order Confirmation
**Tool:** `send_order_confirmation(order_id, customer_name, customer_email, customer_phone, service_type, total_amount)`

**When to Use:**
- Immediately after OrderAgent creates a new order
- When customer requests order confirmation resend

**Channels:** Email + SMS

**Content Includes:**
- Order ID and service type
- Total amount
- Next steps (payment, installation)
- Support contact information

**Example:**
```python
send_order_confirmation(
    order_id="ORD-20260218-456",
    customer_name="Pizza Hut",
    customer_email="john@pizzahut.com",
    customer_phone="215-555-1234",
    service_type="Fiber 5G Business Internet",
    total_amount=999.00
)
```

### 2. Payment Notification
**Tool:** `send_payment_notification(order_id, customer_name, payment_status, amount, payment_method, customer_email=None, customer_phone=None)`

**When to Use:**
- After PaymentAgent successfully processes payment (`payment_status="success"`)
- After PaymentAgent fails payment processing (`payment_status="failed"`)

**Channels:** Email + SMS

**Content Includes:**
- Payment status (success/failure)
- Amount and payment method
- Next steps or action required
- Transaction confirmation/error details

**Example:**
```python
send_payment_notification(
    order_id="ORD-20260218-456",
    customer_name="Pizza Hut",
    payment_status="success",
    amount=999.00,
    payment_method="Credit Card (Visa ending in 1234)",
    customer_email="john@pizzahut.com",
    customer_phone="215-555-1234"
)
```

### 3. Installation Reminder
**Tool:** `send_installation_reminder(order_id, customer_name, installation_date, installation_time, service_address, customer_email=None, customer_phone=None)`

**When to Use:**
- 24 hours before scheduled installation appointment
- When customer requests installation reminder

**Channels:** Email + SMS

**Content Includes:**
- Installation date and time window
- Service address
- Preparation checklist:
  - Authorized representative on-site
  - Access to telecom room/MDF
  - Parking availability for service van
- Contact info for rescheduling

**Example:**
```python
send_installation_reminder(
    order_id="ORD-20260218-456",
    customer_name="Pizza Hut",
    installation_date="2026-02-20",
    installation_time="9:00 AM - 12:00 PM",
    service_address="123 Main Street, Philadelphia, PA 19103",
    customer_email="john@pizzahut.com",
    customer_phone="215-555-1234"
)
```

### 4. Service Activated
**Tool:** `send_service_activated_notification(order_id, customer_name, service_type, account_number, circuit_id, customer_email=None, customer_phone=None)`

**When to Use:**
- After ServiceFulfillmentAgent successfully activates service
- When customer requests service activation confirmation

**Channels:** Email + SMS

**Content Includes:**
- Welcome message
- Account number and circuit ID
- Service status: ACTIVE
- Customer portal access
- Support contact information

**Example:**
```python
send_service_activated_notification(
    order_id="ORD-20260218-456",
    customer_name="Pizza Hut",
    service_type="Fiber 5G Business Internet",
    account_number="ACC-123456789",
    circuit_id="CKT-987654321",
    customer_email="john@pizzahut.com",
    customer_phone="215-555-1234"
)
```

### 5. Abandoned Cart Reminder
**Tool:** `send_abandoned_cart_reminder(cart_id, customer_name, cart_items, total_amount, customer_email=None, customer_phone=None)`

**When to Use:**
- 24 hours after cart creation with no order
- When customer leaves items in cart without completing purchase

**Channels:** Email only (marketing message)

**Content Includes:**
- Cart contents and total amount
- Quote expiration notice (7 days)
- Call to action to complete order
- Support contact for questions

**Example:**
```python
send_abandoned_cart_reminder(
    cart_id="CART-20260218-123",
    customer_name="Pizza Hut",
    cart_items="Fiber 5G Business Internet (1x)",
    total_amount=999.00,
    customer_email="john@pizzahut.com"
)
```

### 6. Order Status Update
**Tool:** `send_order_status_update(order_id, customer_name, old_status, new_status, status_message, customer_email=None, customer_phone=None)`

**When to Use:**
- When OrderAgent updates order status
- When order progresses through lifecycle (draft → pending_payment → confirmed → completed)

**Channels:** Email + SMS

**Content Includes:**
- Old status and new status
- Customizable status message
- Next steps
- Support contact

**Example:**
```python
send_order_status_update(
    order_id="ORD-20260218-456",
    customer_name="Pizza Hut",
    old_status="pending_payment",
    new_status="confirmed",
    status_message="Payment received. Your order is now confirmed and ready for installation scheduling.",
    customer_email="john@pizzahut.com",
    customer_phone="215-555-1234"
)
```

### 7. Notification History Query
**Tool:** `get_notification_history(customer_email=None, customer_phone=None, notification_type=None, limit=10)`

**When to Use:**
- User requests notification history for a customer
- Debugging notification delivery issues
- Audit trail for customer communications

**Returns:** List of notifications with details:
- Notification ID, type, status
- Channels used (email, SMS, both)
- Timestamp
- Recipient contact info

**Example:**
```python
get_notification_history(
    customer_email="john@pizzahut.com",
    limit=5
)
```

## Key Features

### 1. Deduplication (5-Minute Window)
Prevents duplicate notifications from being sent within 5 minutes of each other. Uses in-memory cache `_DEDUP_CACHE` with composite key: `{notification_type}:{order_id}:{customer_email/phone}`

**Why:** Prevents spam if agent is asked multiple times to send the same notification.

### 2. Multi-Channel Delivery
- **Transactional messages** (order, payment, installation, activation): Email + SMS
- **Marketing messages** (abandoned cart): Email only (unless SMS opt-in confirmed)

### 3. Contact Validation
All notification tools require **at least one** contact method:
- Customer email OR customer phone (not both mandatory)
- Validates presence before attempting send
- Returns error if no contact info available

### 4. Structured JSON Responses
All tools return JSON to prevent LLM hallucination:

```json
{
  "success": true,
  "notification_id": "NOTIF-20260218143025-456",
  "notification_type": "order_confirmation",
  "channels": ["email", "sms"],
  "recipient_email": "john@pizzahut.com",
  "recipient_phone": "215-555-1234",
  "status": "sent",
  "message": "Order confirmation sent successfully via email, sms"
}
```

### 5. In-Memory Storage
- **_NOTIFICATIONS dict**: Stores all sent notifications with full details
- **_DEDUP_CACHE dict**: Tracks recent notifications for deduplication
- **Production Note:** Replace with persistent storage (database) in production

## Usage Patterns

### Automatic Notifications (Recommended)
Most notifications should be triggered automatically by other agents:

```python
# OrderAgent creates order → automatically sends order confirmation
order_agent.create_order(...) 
→ customer_communication_agent.send_order_confirmation(...)

# PaymentAgent processes payment → automatically sends payment notification
payment_agent.process_payment(...)
→ customer_communication_agent.send_payment_notification(payment_status="success", ...)

# ServiceFulfillmentAgent activates service → automatically sends activation notification
service_fulfillment_agent.activate_service(...)
→ customer_communication_agent.send_service_activated_notification(...)
```

### Manual Notifications (User Request)
User can explicitly request notifications via SuperAgent:

```
User: "Send order confirmation for ORD-20260218-456 to Pizza Hut"
→ SuperAgent routes to customer_communication_agent
→ Sends notification via send_order_confirmation()

User: "Show notification history for john@pizzahut.com"
→ SuperAgent routes to customer_communication_agent
→ Queries history via get_notification_history()
```

## Configuration

### Environment Variables
Set in `SuperAgent/server/.env`:

```bash
GEMINI_MODEL=gemini-3-flash-preview  # Model for agent
```

### Agent Parameters
- **Temperature:** 0.0 (deterministic - no creativity needed for notifications)
- **Max Tokens:** 2048
- **Model:** Inherits from `GEMINI_MODEL` environment variable

## Error Handling

All notification tools implement comprehensive error handling:

```python
try:
    # Validate contact info
    if not customer_email and not customer_phone:
        return {"success": False, "error": "No contact information provided"}
    
    # Check deduplication
    if _check_duplicate(...):
        return {"success": True, "status": "deduped", "message": "..."}
    
    # Send notification
    notification = Notification(...)
    _NOTIFICATIONS[notification_id] = notification
    
    return {"success": True, "notification_id": notification_id, ...}
    
except Exception as e:
    logger.error(f"Failed to send notification: {e}")
    return {"success": False, "error": str(e)}
```

## Testing

### Unit Tests (Future)
```python
def test_send_order_confirmation():
    result = send_order_confirmation(
        order_id="TEST-123",
        customer_name="Test Company",
        customer_email="test@example.com",
        customer_phone="215-555-0000",
        service_type="Fiber 5G",
        total_amount=999.00
    )
    assert result["success"] == True
    assert result["notification_type"] == "order_confirmation"
    assert "email" in result["channels"]
    assert "sms" in result["channels"]
```

### Integration Tests (Future)
Test end-to-end notification flow:
1. Create order via OrderAgent
2. Verify order confirmation sent via CustomerCommunicationAgent
3. Process payment via PaymentAgent
4. Verify payment notification sent
5. Schedule installation via ServiceFulfillmentAgent
6. Verify installation reminder sent 24 hours before
7. Activate service
8. Verify service activation notification sent

## Routing Rules (SuperAgent)

**SuperAgent transfers to customer_communication_agent when:**
- User explicitly requests sending a notification
- User asks for notification history
- User requests resending a notification

**Examples that trigger routing:**
- "Send order confirmation to the customer"
- "Send installation reminder for tomorrow's appointment"
- "Notify customer their service is activated"
- "Show notification history for john@example.com"
- "Resend payment confirmation"

**Note:** Most notifications are automatic (triggered by other agents), not manual routing.

## Production Considerations

### 1. Replace In-Memory Storage
Current implementation uses dictionaries. Production requires:
- **PostgreSQL** or **MongoDB** for persistent notification storage
- **Redis** for deduplication cache (5-minute TTL)

### 2. Implement Real Email/SMS Gateways
Current implementation is a stub. Production requires:
- **SendGrid** or **AWS SES** for email
- **Twilio** or **AWS SNS** for SMS
- Proper error handling, retry logic, delivery tracking

### 3. Add Opt-Out Management
- Implement unsubscribe links in marketing emails
- Respect customer communication preferences
- Comply with CAN-SPAM and TCPA regulations

### 4. Enhance Deduplication
- Use sliding window algorithm (not fixed 5-minute cache)
- Track delivery attempts vs. successful deliveries
- Implement exponential backoff for retries

### 5. Add Observability
- Log all notification attempts with delivery status
- Track metrics: delivery rate, bounce rate, open rate
- Alert on gateway failures or high bounce rates

### 6. Security Enhancements
- Encrypt PII (email, phone) in database
- Implement rate limiting per customer
- Add webhook validation for delivery status callbacks

## Troubleshooting

### Notification Not Sent
**Symptoms:** Tool returns `{"success": False, "error": "..."}`

**Possible Causes:**
1. Missing contact info - Check customer_email and customer_phone parameters
2. Invalid contact format - Validate email/phone format
3. Gateway failure - Check email/SMS gateway logs (production)

**Resolution:**
- Ensure at least one contact method provided
- Validate contact info format before calling tool
- Check error message in response for specific cause

### Duplicate Notification Detected
**Symptoms:** Tool returns `{"success": True, "status": "deduped"}`

**Cause:** Same notification sent within 5 minutes

**Resolution:**
- Wait 5+ minutes before resending
- Use different notification type if update needed (e.g., order_status_update instead of order_confirmation)
- Clear deduplication cache if testing (`_DEDUP_CACHE.clear()`)

### Notification History Empty
**Symptoms:** `get_notification_history()` returns empty list

**Cause:** No notifications sent yet (in-memory storage cleared on restart)

**Resolution:**
- Send test notification first
- In production, use persistent database to survive restarts

## Contact

For questions or issues with CustomerCommunicationAgent, refer to:
- **AGENTS.md** - Detailed agent documentation
- **CLAUDE.md** - Development guidelines
- **Scenarios.md** - Test scenarios including notification tests (10.1-10.18)
