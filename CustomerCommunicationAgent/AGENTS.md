# Customer Communication Agent - Technical Documentation

## Agent Profile

| Property | Value |
|----------|-------|
| **Agent Name** | `customer_communication_agent` |
| **Type** | Sub-Agent (Specialist) |
| **Parent** | SuperAgent (root orchestrator) |
| **Purpose** | Automated customer notifications via email and SMS throughout order lifecycle |
| **Model** | `gemini-3-flash-preview` (via `GEMINI_MODEL` env var) |
| **Temperature** | 0.0 (deterministic - no creativity needed) |
| **Max Tokens** | 2048 |
| **Tools** | 7 notification tools |
| **Dependencies** | None (standalone notification system) |

## Architecture

### Design Pattern: Zero-Hallucination Notification System

CustomerCommunicationAgent follows the **deterministic execution pattern** where ALL notification logic is in tools (not LLM). The LLM's role is limited to:
1. Understanding which notification type to send
2. Extracting parameters from context
3. Calling appropriate tool
4. Formatting response for user

**Critical Design Decision:** All tools return structured JSON to prevent LLM from hallucinating notification content, delivery status, or recipient info.

### Integration with Multi-Agent System

```
SuperAgent (Orchestrator)
    ↓ (routes manual notification requests)
CustomerCommunicationAgent
    ↓ (calls 7 notification tools)
Notification Tools
    ↓ (deterministic execution)
Email/SMS Gateway (production) or In-Memory Storage (dev)
```

**Automatic Notification Flow:**
```
OrderAgent creates order
    → OrderAgent calls customer_communication_agent.send_order_confirmation()
    → Notification sent via email + SMS

PaymentAgent processes payment
    → PaymentAgent calls customer_communication_agent.send_payment_notification()
    → Notification sent via email + SMS

ServiceFulfillmentAgent activates service
    → ServiceFulfillmentAgent calls customer_communication_agent.send_service_activated_notification()
    → Notification sent via email + SMS
```

**Manual Notification Flow (User Request):**
```
User: "Send order confirmation for ORD-123"
    → SuperAgent routes to customer_communication_agent
    → Agent parses request, extracts order_id
    → Agent calls send_order_confirmation()
    → Returns confirmation to user
```

## Tools (7 Total)

### 1. send_order_confirmation

**Purpose:** Send order confirmation immediately after order creation

**Signature:**
```python
def send_order_confirmation(
    order_id: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    service_type: str,
    total_amount: float
) -> str  # Returns JSON
```

**Parameters:**
- `order_id` (required): Order identifier (e.g., "ORD-20260218-456")
- `customer_name` (required): Company/customer name
- `customer_email` (required): Customer email address
- `customer_phone` (required): Customer phone number (format: "215-555-1234")
- `service_type` (required): Service description (e.g., "Fiber 5G Business Internet")
- `total_amount` (required): Order total in dollars (e.g., 999.00)

**Returns:** JSON with notification_id, channels, status

**Trigger Conditions:**
- OrderAgent creates new order with status "draft" or "confirmed"
- User manually requests order confirmation

**Channels:** Email + SMS (multi-channel)

**Deduplication:** 5-minute window per order_id

### 2. send_payment_notification

**Purpose:** Notify customer of payment success or failure

**Signature:**
```python
def send_payment_notification(
    order_id: str,
    customer_name: str,
    payment_status: str,  # "success" or "failed"
    amount: float,
    payment_method: str,
    customer_email: str = None,
    customer_phone: str = None
) -> str  # Returns JSON
```

**Parameters:**
- `payment_status`: Must be "success" or "failed"
- `payment_method`: Description (e.g., "Credit Card (Visa ending in 1234)")
- At least one of `customer_email` or `customer_phone` required

**Returns:** JSON with notification details

**Trigger Conditions:**
- PaymentAgent successfully processes payment
- PaymentAgent fails payment processing

**Channels:** Email + SMS

### 3. send_installation_reminder

**Purpose:** Send reminder 24 hours before scheduled installation

**Signature:**
```python
def send_installation_reminder(
    order_id: str,
    customer_name: str,
    installation_date: str,  # Format: "YYYY-MM-DD"
    installation_time: str,  # Format: "9:00 AM - 12:00 PM"
    service_address: str,
    customer_email: str = None,
    customer_phone: str = None
) -> str  # Returns JSON
```

**Parameters:**
- `installation_date`: ISO format date (e.g., "2026-02-20")
- `installation_time`: Time window (e.g., "9:00 AM - 12:00 PM")
- `service_address`: Full address including city, state, zip

**Returns:** JSON with notification details

**Trigger Conditions:**
- 24 hours before scheduled installation (automated)
- ServiceFulfillmentAgent schedules installation
- User manually requests reminder

**Channels:** Email + SMS

**Content Includes:**
- Preparation checklist (representative on-site, telecom room access, parking)
- Contact info for rescheduling

### 4. send_service_activated_notification

**Purpose:** Welcome message when service goes live

**Signature:**
```python
def send_service_activated_notification(
    order_id: str,
    customer_name: str,
    service_type: str,
    account_number: str,
    circuit_id: str,
    customer_email: str = None,
    customer_phone: str = None
) -> str  # Returns JSON
```

**Parameters:**
- `account_number`: Customer account number (e.g., "ACC-123456789")
- `circuit_id`: Circuit identifier (e.g., "CKT-987654321")

**Returns:** JSON with notification details

**Trigger Conditions:**
- ServiceFulfillmentAgent successfully activates service
- User manually requests activation confirmation

**Channels:** Email + SMS

**Content Includes:**
- Account details (account number, circuit ID)
- Customer portal access
- Support contact information

### 5. send_abandoned_cart_reminder

**Purpose:** Cart recovery marketing message

**Signature:**
```python
def send_abandoned_cart_reminder(
    cart_id: str,
    customer_name: str,
    cart_items: str,  # Description of items (e.g., "Fiber 5G Business Internet (1x)")
    total_amount: float,
    customer_email: str = None,
    customer_phone: str = None
) -> str  # Returns JSON
```

**Parameters:**
- `cart_items`: Text description of cart contents
- `total_amount`: Cart total in dollars

**Returns:** JSON with notification details

**Trigger Conditions:**
- 24 hours after cart creation with no order
- Cart idle without purchase

**Channels:** Email only (marketing message - SMS requires explicit opt-in)

**Content Includes:**
- Cart contents and total
- Quote expiration notice (7 days)
- Call to action

### 6. send_order_status_update

**Purpose:** Generic notification for order status changes

**Signature:**
```python
def send_order_status_update(
    order_id: str,
    customer_name: str,
    old_status: str,
    new_status: str,
    status_message: str,
    customer_email: str = None,
    customer_phone: str = None
) -> str  # Returns JSON
```

**Parameters:**
- `old_status`: Previous order status (e.g., "pending_payment")
- `new_status`: New order status (e.g., "confirmed")
- `status_message`: Customizable message explaining the change

**Returns:** JSON with notification details

**Trigger Conditions:**
- OrderAgent updates order status
- Order progresses through lifecycle

**Channels:** Email + SMS

### 7. get_notification_history

**Purpose:** Query notification history for audit/debugging

**Signature:**
```python
def get_notification_history(
    customer_email: str = None,
    customer_phone: str = None,
    notification_type: str = None,
    limit: int = 10
) -> str  # Returns JSON array
```

**Parameters:**
- At least one of `customer_email` or `customer_phone` required
- `notification_type`: Optional filter (e.g., "order_confirmation")
- `limit`: Max results (default 10, max 100)

**Returns:** JSON array of notifications with:
- notification_id
- notification_type
- channels used
- timestamp
- status
- recipient info

**Use Cases:**
- User requests notification history
- Debugging delivery issues
- Audit trail for customer communications

## Data Models

### Notification
```python
@dataclass
class Notification:
    notification_id: str
    notification_type: NotificationType
    order_id: str
    customer_name: str
    recipient_email: str | None
    recipient_phone: str | None
    channels: list[NotificationChannel]
    status: NotificationStatus
    message: str
    created_at: str
    sent_at: str | None
    
    def to_dict(self) -> dict
    def mark_sent(self)
    def mark_failed(self, error: str)
```

### NotificationType (Enum)
```python
class NotificationType(str, Enum):
    ORDER_CONFIRMATION = "order_confirmation"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    INSTALLATION_SCHEDULED = "installation_scheduled"
    INSTALLATION_REMINDER = "installation_reminder"
    SERVICE_ACTIVATED = "service_activated"
    ORDER_STATUS_UPDATE = "order_status_update"
    ABANDONED_CART = "abandoned_cart"
    GENERIC = "generic"
```

### NotificationChannel (Enum)
```python
class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    BOTH = "both"
```

### NotificationStatus (Enum)
```python
class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DEDUPED = "deduped"
```

## Deduplication Logic

**Implementation:** `_check_duplicate()` helper function

**Algorithm:**
1. Create composite key: `{notification_type}:{order_id}:{customer_email or phone}`
2. Check if key exists in `_DEDUP_CACHE` with timestamp < 5 minutes ago
3. If exists, return True (duplicate detected)
4. If not exists, add to cache with current timestamp
5. Return False (not duplicate)

**Cache Storage:**
```python
_DEDUP_CACHE = {
    "order_confirmation:ORD-123:john@example.com": datetime(2026, 2, 18, 14, 30, 0),
    "payment_success:ORD-123:john@example.com": datetime(2026, 2, 18, 15, 0, 0),
    ...
}
```

**Production Note:** Replace with Redis with 5-minute TTL for distributed systems.

## Error Handling

### Contact Validation
```python
if not customer_email and not customer_phone:
    return {
        "success": False,
        "error": "No contact information provided. Requires email or phone."
    }
```

### Invalid Parameters
```python
if payment_status not in ["success", "failed"]:
    return {
        "success": False,
        "error": "Invalid payment_status. Must be 'success' or 'failed'."
    }
```

### Gateway Failures (Production)
```python
try:
    email_result = send_email_via_gateway(...)
except EmailGatewayError as e:
    logger.error(f"Email gateway failure: {e}")
    # Fall back to SMS only
```

### Exception Handling
```python
try:
    # Notification logic
    return {"success": True, ...}
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {"success": False, "error": str(e)}
```

## Logging

All tools log key events:

```python
# Info logs (successful operations)
logger.info(f"Sending order confirmation for order {order_id} to {customer_name}")
logger.info(f"Order confirmation sent successfully: {notification_id}")

# Error logs (failures)
logger.error(f"Failed to send order confirmation: {e}")
logger.error(f"No contact information for customer {customer_name}")
```

**Log Format:**
```
2026-02-18 14:30:15 INFO [customer_communication_agent.tools.notification_tools] Sending order confirmation for order ORD-20260218-456 to Pizza Hut
2026-02-18 14:30:15 INFO [customer_communication_agent.tools.notification_tools] Order confirmation sent successfully: NOTIF-20260218143015-789
```

## Testing Strategy

### Unit Tests (Future)
- Test each tool with valid inputs → success
- Test missing contact info → error
- Test deduplication → DEDUPED status
- Test invalid parameters → error

### Integration Tests (Future)
- Test end-to-end notification flow:
  1. OrderAgent creates order
  2. Verify order confirmation sent
  3. PaymentAgent processes payment
  4. Verify payment notification sent
  5. ServiceFulfillmentAgent schedules installation
  6. Verify installation reminder sent
  7. ServiceFulfillmentAgent activates service
  8. Verify activation notification sent
  9. Query notification history
  10. Verify all 4 notifications in history

### E2E Tests (Matches Scenarios.md 10.1-10.18)
See [Scenarios.md](../Scenarios.md) for comprehensive test scenarios including:
- Order confirmation notification (10.1)
- Payment success notification (10.2)
- Installation reminder (10.3)
- Abandoned cart recovery (10.4)
- Installation confirmation (10.5)
- Payment failure notification (10.6)
- Order status update (10.7)
- Multi-channel delivery (10.8)
- Missing contact info handling (10.9)
- Email/SMS gateway failures (10.10-10.11)
- Invalid email/phone handling (10.12-10.13)
- Duplicate notification deduplication (10.14)
- Unsubscribe handling (10.15)
- Notification history queries (10.16-10.18)

## Production Enhancements

### 1. Persistent Storage
**Current:** In-memory dictionaries (_NOTIFICATIONS, _DEDUP_CACHE)
**Production:** PostgreSQL + Redis

```python
# Replace in-memory storage with database
from sqlalchemy import create_engine
from redis import Redis

# Notification storage
engine = create_engine("postgresql://...")
Session = sessionmaker(engine)

# Deduplication cache
redis_client = Redis(host="...", port=6379)
redis_client.setex(dedup_key, 300, "1")  # 5-minute TTL
```

### 2. Real Email/SMS Gateways
**Current:** Stub implementation (logs only)
**Production:** SendGrid + Twilio

```python
# Email via SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email="noreply@telecom.com",
    to_emails=customer_email,
    subject="Order Confirmation",
    html_content=notification_html
)
sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
response = sg.send(message)

# SMS via Twilio
from twilio.rest import Client

client = Client(account_sid, auth_token)
message = client.messages.create(
    body=notification_text,
    from_="+12155551234",
    to=customer_phone
)
```

### 3. Delivery Tracking
Track email opens, link clicks, SMS delivery confirmations:

```python
# Add webhook handlers for delivery status
@app.post("/webhooks/sendgrid/events")
async def sendgrid_webhook(request: Request):
    events = await request.json()
    for event in events:
        if event["event"] == "open":
            update_notification_status(event["notification_id"], "opened")
```

### 4. Opt-Out Management
Respect customer communication preferences:

```python
# Check opt-out before sending
def is_opted_out(customer_email, notification_type):
    if notification_type == "abandoned_cart":
        return check_marketing_opt_out(customer_email)
    return check_transactional_opt_out(customer_email)
```

### 5. Rate Limiting
Prevent abuse:

```python
# Limit notifications per customer per hour
from redis import Redis
redis = Redis()

key = f"rate_limit:{customer_email}"
count = redis.incr(key)
if count == 1:
    redis.expire(key, 3600)  # 1 hour
if count > 10:
    return {"success": False, "error": "Rate limit exceeded"}
```

## Security Considerations

### 1. PII Encryption
Encrypt email/phone in database:

```python
from cryptography.fernet import Fernet
cipher = Fernet(encryption_key)
encrypted_email = cipher.encrypt(customer_email.encode())
```

### 2. Contact Validation
Validate format before storing/sending:

```python
import re
email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
phone_pattern = r'^\d{3}-\d{3}-\d{4}$'

if not re.match(email_pattern, customer_email):
    return {"success": False, "error": "Invalid email format"}
```

### 3. API Key Protection
Never log or expose API keys:

```python
# ❌ WRONG
logger.info(f"Sending email via SendGrid with key {sendgrid_api_key}")

# ✅ CORRECT
logger.info("Sending email via SendGrid")
```

## Troubleshooting

### Issue: Notification Not Sent
**Symptoms:** Tool returns `{"success": False, "error": "No contact information"}`

**Root Cause:** Missing customer_email and customer_phone

**Resolution:**
1. Check OrderAgent database - ensure customer has contact info
2. Update customer record with email/phone
3. Retry notification

### Issue: Duplicate Detected
**Symptoms:** Tool returns `{"success": True, "status": "deduped"}`

**Root Cause:** Same notification sent < 5 minutes ago

**Resolution:**
1. Wait 5+ minutes before resending
2. Use different notification type if update needed
3. Clear deduplication cache if testing: `_DEDUP_CACHE.clear()`

### Issue: Notification History Empty
**Symptoms:** `get_notification_history()` returns `[]`

**Root Cause:** In-memory storage cleared on server restart

**Resolution:**
1. Send test notification first
2. In production, use persistent database

## References

- **Project Documentation:** [README.md](README.md)
- **Test Scenarios:** [../Scenarios.md](../Scenarios.md) (10.1-10.18)
- **Architecture:** [../AGENTS.md](../AGENTS.md)
- **Development Guidelines:** [../CLAUDE.md](../CLAUDE.md)
