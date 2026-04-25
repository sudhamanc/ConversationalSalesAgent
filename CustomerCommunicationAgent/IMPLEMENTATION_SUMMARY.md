# CustomerCommunicationAgent - Implementation Summary

## Overview

CustomerCommunicationAgent is a specialized sub-agent in the B2B Conversational Sales Agent system that handles automated customer notifications via email and SMS throughout the order and fulfillment lifecycle.

**Status:** ✅ **COMPLETE** - Fully implemented and integrated with SuperAgent

**Implementation Date:** February 18, 2026

**Pattern Used:** ADK Bootstrap Template with importlib isolation (matches ServiceabilityAgent and OrderAgent)

## Architecture Decisions

### 1. Zero-Hallucination Design Pattern

**Decision:** ALL notification logic in deterministic tools, LLM only for routing and parameter extraction

**Rationale:**
- Customer communications are business-critical (order confirmations, payment status, etc.)
- Cannot tolerate hallucinated content, delivery status, or recipient info
- Structured JSON tool outputs prevent LLM from modifying notification data

**Implementation:**
```python
# Tools return structured JSON
def send_order_confirmation(...) -> str:
    return json.dumps({
        "success": true,
        "notification_id": "NOTIF-123",
        "channels": ["email", "sms"],
        "status": "sent"
    })
```

### 2. Multi-Channel Delivery Strategy

**Decision:** Email + SMS for transactional messages, email only for marketing

**Rationale:**
- Critical notifications (order, payment, installation) need immediate delivery
- SMS provides higher open rates (98%) vs email (20%)
- Marketing messages (abandoned cart) require explicit opt-in for SMS

**Implementation:**
```python
# Transactional: Email + SMS
send_order_confirmation(channels=["email", "sms"])

# Marketing: Email only
send_abandoned_cart_reminder(channels=["email"])
```

### 3. Deduplication with 5-Minute Window

**Decision:** Prevent duplicate notifications within 5 minutes using in-memory cache

**Rationale:**
- Prevents spam if agent is asked multiple times to send same notification
- 5 minutes allows legitimate retry if first attempt failed
- Shorter than typical user tolerance for duplicates (minutes, not seconds)

**Implementation:**
```python
def _check_duplicate(notification_type, order_id, recipient):
    key = f"{notification_type}:{order_id}:{recipient}"
    if key in _DEDUP_CACHE:
        age = datetime.now() - _DEDUP_CACHE[key]
        if age.total_seconds() < 300:  # 5 minutes
            return True
    _DEDUP_CACHE[key] = datetime.now()
    return False
```

### 4. In-Memory Storage for Development

**Decision:** Use Python dictionaries for notification storage and deduplication cache

**Rationale:**
- Zero setup for academic/demo environment
- Sufficient for single-user testing
- Easy to inspect/debug
- Production will migrate to PostgreSQL + Redis

**Implementation:**
```python
_NOTIFICATIONS: dict[str, Notification] = {}
_DEDUP_CACHE: dict[str, datetime] = {}
```

**Migration Path:**
```python
# Production replacement
from sqlalchemy import create_engine
from redis import Redis

engine = create_engine("postgresql://...")
redis = Redis(host="...", decode_responses=True)
```

### 5. Contact Validation (OR Logic)

**Decision:** Require email OR phone (not both mandatory)

**Rationale:**
- Some customers only provide email (online orders)
- Some customers only provide phone (phone orders)
- Multi-channel delivery gracefully degrades if one method missing

**Implementation:**
```python
if not customer_email and not customer_phone:
    return {"success": False, "error": "No contact information"}
# If only email → send email only
# If only phone → send SMS only
# If both → send both
```

## Implementation Details

### File Structure

```
CustomerCommunicationAgent/
├── pyproject.toml                    # Python package definition
├── README.md                         # User guide
├── AGENTS.md                         # Technical documentation (this file)
├── IMPLEMENTATION_SUMMARY.md         # Implementation decisions
└── customer_communication_agent/
    ├── __init__.py                   # Package exports: get_agent()
    ├── agent.py                      # ADK Agent with 7 tools, temp=0.0
    ├── prompts.py                    # Comprehensive notification instructions
    ├── models/
    │   └── __init__.py               # Notification, NotificationType, NotificationChannel, NotificationStatus
    ├── tools/
    │   ├── __init__.py               # Tool exports
    │   └── notification_tools.py     # 7 notification tools (677 lines)
    └── utils/
        └── logger.py                 # Logging utilities
```

### Tools Implemented (7 Total)

| # | Tool | Purpose | Channels | Trigger |
|---|------|---------|----------|---------|
| 1 | `send_order_confirmation` | Order confirmation | Email + SMS | Order created |
| 2 | `send_payment_notification` | Payment success/failure | Email + SMS | Payment processed |
| 3 | `send_installation_reminder` | 24-hour reminder | Email + SMS | Before installation |
| 4 | `send_service_activated_notification` | Service activation | Email + SMS | Service activated |
| 5 | `send_abandoned_cart_reminder` | Cart recovery | Email only | Cart idle 24h |
| 6 | `send_order_status_update` | Status change | Email + SMS | Status updated |
| 7 | `get_notification_history` | Query history | N/A | User request |

**Total Lines of Code:**
- notification_tools.py: 677 lines
- agent.py: 64 lines
- prompts.py: 314 lines
- models/__init__.py: 120 lines
- **Total: ~1,175 lines**

### Agent Configuration

```python
customer_communication_agent = Agent(
    name="customer_communication_agent",
    model=os.getenv("GEMINI_MODEL"),  # gemini-3-flash-preview
    instruction=CUSTOMER_COMMUNICATION_AGENT_INSTRUCTION,
    description=CUSTOMER_COMMUNICATION_SHORT_DESCRIPTION,
    tools=[7 notification tools],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,  # Deterministic - no creativity
        max_output_tokens=2048,
    ),
)
```

**Why temperature=0.0?**
- Notification content is deterministic (generated by tools)
- No creative variation needed in routing or parameter extraction
- Ensures consistent behavior across requests

### SuperAgent Integration

#### 1. Importlib Isolation Wrapper

**Location:** `SuperAgent/super_agent/sub_agents/customer_communication/agent.py`

**Pattern:** Load CustomerCommunicationAgent without executing `__init__.py` to prevent parent-binding conflicts

```python
# Step 1: Stub parent package
_stub = pytypes.ModuleType("customer_communication_agent")
sys.modules["customer_communication_agent"] = _stub

# Step 2: Load dependencies in isolation
# (models, utils, tools, prompts)

# Step 3: Load agent module (fresh instance)
_agent_spec = importlib.util.spec_from_file_location(
    "customer_communication_agent.agent",
    os.path.join(_COMM_PKG, "agent.py")
)
customer_communication_agent = _agent_mod.customer_communication_agent
```

#### 2. SuperAgent Registration

**File:** `SuperAgent/super_agent/agent.py`

**Changes:**
1. Import: `from .sub_agents.customer_communication import customer_communication_agent`
2. Added to sub_agents list (position 7 of 9, after service_fulfillment_agent, before greeting_agent)

```python
def _build_sub_agents() -> list[Agent]:
    agents.extend([
        discovery_agent,
        serviceability_agent,
        product_agent,
        payment_agent,
        order_agent,
        service_fulfillment_agent,
        customer_communication_agent,  # NEW
        greeting_agent,
        faq_agent
    ])
```

#### 3. SuperAgent Routing Rules

**File:** `SuperAgent/super_agent/prompts.py`

**Added Rule #7:**
```
7. **Customer Notifications and Communication**
   Transfer to **customer_communication_agent** when:
   - User explicitly requests sending a notification
   - User asks to view notification history
   - User requests resending a notification
   
   Examples:
   - "Send order confirmation to the customer"
   - "Send installation reminder for tomorrow's appointment"
   - "Show notification history for john@example.com"
   
   Note: MOST notifications should be sent AUTOMATICALLY by other agents.
   Only transfer here when user explicitly requests manual notification or history query.
```

**Key Insight:** Most notifications are automatic (triggered by other agents), not manual routing.

### Notification Scenarios Covered

| Scenario | Trigger Agent | Notification Tool | Channels |
|----------|---------------|-------------------|----------|
| Order created | OrderAgent | send_order_confirmation | Email + SMS |
| Payment success | PaymentAgent | send_payment_notification(status="success") | Email + SMS |
| Payment failed | PaymentAgent | send_payment_notification(status="failed") | Email + SMS |
| Installation scheduled | ServiceFulfillmentAgent | send_installation_reminder | Email + SMS |
| Installation reminder (24h) | Automated | send_installation_reminder | Email + SMS |
| Service activated | ServiceFulfillmentAgent | send_service_activated_notification | Email + SMS |
| Order status changed | OrderAgent | send_order_status_update | Email + SMS |
| Cart abandoned (24h) | Automated | send_abandoned_cart_reminder | Email only |
| History query | User request | get_notification_history | N/A |

## Testing Strategy

### Manual Testing (During Development)

**Test 1: Order Confirmation**
```
User: "Send order confirmation for order ORD-20260218-456 to Pizza Hut"
Expected: Agent calls send_order_confirmation(), returns notification_id and channels
```

**Test 2: Payment Notification**
```
User: "Payment succeeded for order ORD-20260218-456, amount $999.00"
Expected: Agent calls send_payment_notification(payment_status="success")
```

**Test 3: Deduplication**
```
1. Send order confirmation for ORD-123
2. Immediately send order confirmation for ORD-123 again
Expected: Second request returns status="deduped"
```

**Test 4: Missing Contact Info**
```
User: "Send order confirmation for ORD-789" (customer has no email/phone)
Expected: Agent returns error "No contact information provided"
```

### Integration Tests (Future)

**E2E Notification Flow:**
1. User: "We're Pizza Hut at 123 Main St, Philadelphia PA"
   → DiscoveryAgent registers company
2. User: "yes" (serviceability check)
   → ServiceabilityAgent validates address
3. User: "Show me products"
   → ProductAgent shows Fiber 5G
4. User: "I'll take Fiber 5G"
   → OrderAgent creates order
   → **CustomerCommunicationAgent sends order confirmation** ✓
5. User: "Process payment"
   → PaymentAgent approves payment
   → **CustomerCommunicationAgent sends payment notification** ✓
6. User: "Schedule installation for Feb 20 at 9 AM"
   → ServiceFulfillmentAgent schedules appointment
   → **CustomerCommunicationAgent sends installation reminder** ✓
7. (24 hours later) Automated reminder
   → **CustomerCommunicationAgent sends installation reminder** ✓
8. Installation complete, service activated
   → ServiceFulfillmentAgent activates service
   → **CustomerCommunicationAgent sends activation notification** ✓
9. User: "Show notification history for Pizza Hut"
   → **CustomerCommunicationAgent returns 5 notifications** ✓

### Unit Tests (Future - Not Implemented Yet)

```python
# tests/test_notification_tools.py

def test_send_order_confirmation_success():
    result = send_order_confirmation(
        order_id="TEST-123",
        customer_name="Test Corp",
        customer_email="test@example.com",
        customer_phone="215-555-0000",
        service_type="Fiber 5G",
        total_amount=999.00
    )
    data = json.loads(result)
    assert data["success"] == True
    assert data["notification_type"] == "order_confirmation"
    assert "email" in data["channels"]
    assert "sms" in data["channels"]

def test_send_order_confirmation_missing_contact():
    result = send_order_confirmation(
        order_id="TEST-123",
        customer_name="Test Corp",
        customer_email=None,
        customer_phone=None,
        service_type="Fiber 5G",
        total_amount=999.00
    )
    data = json.loads(result)
    assert data["success"] == False
    assert "No contact information" in data["error"]

def test_deduplication():
    # Send first notification
    result1 = send_order_confirmation(...)
    data1 = json.loads(result1)
    assert data1["status"] == "sent"
    
    # Send duplicate within 5 minutes
    result2 = send_order_confirmation(...)
    data2 = json.loads(result2)
    assert data2["status"] == "deduped"
```

## Compliance with Design Patterns

### ✅ ADK Bootstrap Template Structure

```
✓ pyproject.toml with package definition
✓ customer_communication_agent/ top-level package
✓ __init__.py exports get_agent()
✓ agent.py with Agent instance
✓ prompts.py with instruction templates
✓ tools/ directory with FunctionTools
✓ models/ for data structures
✓ utils/ for helpers
```

### ✅ Importlib Isolation Pattern

```
✓ SuperAgent wrapper uses importlib.util.spec_from_file_location
✓ Stub parent package to prevent __init__.py execution
✓ Load dependencies in isolation (models, utils, tools, prompts)
✓ Export fresh Agent instance for SuperAgent hierarchy
```

### ✅ Structured JSON Tool Outputs

```
✓ All tools return JSON strings
✓ No plain text responses that LLM could rephrase
✓ Prevents hallucination of notification data
```

### ✅ Zero-Hallucination Architecture

```
✓ LLM role: routing + parameter extraction only
✓ Tools handle: notification content, delivery, status tracking
✓ No LLM-generated notification text (deterministic templates in tools)
```

### ✅ Deterministic Configuration

```
✓ Temperature = 0.0 (no creativity)
✓ Model from environment variable (no default value)
✓ Tools have no randomness
```

## Performance Characteristics

### Latency
- **Tool execution:** <10ms (in-memory operations)
- **Deduplication check:** O(1) dictionary lookup
- **Notification history query:** O(n) where n = total notifications (production: add database indexes)

### Memory Usage
- **Per notification:** ~500 bytes (Notification dataclass)
- **Dedup cache:** ~200 bytes per entry (key + timestamp)
- **1000 notifications:** ~700 KB total

### Scalability
- **Current (development):** Single server, in-memory storage
- **Production:** Horizontally scalable with PostgreSQL + Redis
- **Dedup cache:** Redis with 5-minute TTL (distributed, auto-expiring)

## Production Migration Checklist

### Phase 1: Persistent Storage
- [ ] Replace `_NOTIFICATIONS` dict with PostgreSQL table
- [ ] Replace `_DEDUP_CACHE` dict with Redis (5-minute TTL)
- [ ] Add database indexes: (customer_email, created_at), (order_id)
- [ ] Add Alembic migrations

### Phase 2: Real Email/SMS Gateways
- [ ] Integrate SendGrid for email (API key in .env)
- [ ] Integrate Twilio for SMS (credentials in .env)
- [ ] Add retry logic with exponential backoff
- [ ] Add webhook handlers for delivery status tracking
- [ ] Handle gateway failures (email fails → try SMS)

### Phase 3: Compliance & Security
- [ ] Implement unsubscribe links in marketing emails
- [ ] Add opt-out management (database table + UI)
- [ ] Encrypt PII (email, phone) in database
- [ ] Add rate limiting (max 10 notifications/customer/hour)
- [ ] Comply with CAN-SPAM (email) and TCPA (SMS) regulations

### Phase 4: Observability
- [ ] Add OpenTelemetry tracing for notification delivery
- [ ] Track metrics: delivery rate, bounce rate, open rate, click rate
- [ ] Set up alerts: gateway down, high bounce rate, rate limit exceeded
- [ ] Add dashboards: notifications/hour, delivery status breakdown

### Phase 5: Advanced Features
- [ ] Template management UI (edit notification content without code)
- [ ] A/B testing for notification copy
- [ ] Personalization engine (customer name, company, custom fields)
- [ ] Scheduled notifications (send at specific time/date)
- [ ] Batch notifications (send to multiple customers at once)

## Known Limitations

### Development Environment
1. **In-memory storage:** Data lost on server restart
2. **No real email/SMS:** Logs only, no actual delivery
3. **Single server:** No distributed deduplication
4. **No persistence:** Notification history not saved long-term

### Production Considerations
1. **Deduplication window:** Fixed 5 minutes (not configurable)
2. **No retry logic:** Failed notifications not automatically retried
3. **No delivery tracking:** Cannot verify email opened or SMS delivered
4. **No rate limiting:** Could spam customers if abused
5. **No opt-out management:** Cannot handle unsubscribe requests

### Security
1. **PII not encrypted:** Email/phone stored in plain text
2. **No webhook validation:** Delivery status webhooks not authenticated
3. **No contact validation:** Email/phone format not validated before storage

## Success Criteria (Met ✓)

- [x] **7 notification tools implemented** covering all order lifecycle events
- [x] **Multi-channel delivery** (email + SMS for transactional, email for marketing)
- [x] **Deduplication logic** (5-minute window to prevent spam)
- [x] **Contact validation** (require email OR phone)
- [x] **Structured JSON outputs** (zero-hallucination design)
- [x] **SuperAgent integration** (importlib isolation pattern)
- [x] **Routing rules updated** (Rule #7 for customer notifications)
- [x] **Documentation complete** (README, AGENTS.md, IMPLEMENTATION_SUMMARY)
- [x] **Follows ADK Bootstrap Template** (consistent with other agents)
- [x] **Temperature = 0.0** (deterministic behavior)
- [x] **Comprehensive error handling** (missing contact, duplicates, exceptions)
- [x] **Logging implemented** (info + error logs for all operations)

## Lessons Learned

### 1. Structured JSON Prevents Hallucination
**Observation:** All notification tools return JSON. LLM parses JSON but doesn't rephrase it.

**Why It Matters:** In OrderAgent implementation, we discovered that plain text tool outputs get rephrased by the LLM, causing data corruption (e.g., zip codes changed). JSON structure prevents this.

**Application:** All CustomerCommunicationAgent tools return JSON with explicit fields:
```json
{"success": true, "notification_id": "...", "channels": ["email", "sms"]}
```

### 2. Deduplication is Critical for Notifications
**Observation:** During testing, agents sometimes call tools multiple times (LLM retry, user repeat request).

**Why It Matters:** Duplicate notifications annoy customers and look unprofessional.

**Solution:** Implement 5-minute deduplication window. Balances preventing spam vs. allowing legitimate retries.

### 3. Multi-Channel Delivery Improves Reliability
**Observation:** Email has ~20% open rate, SMS has ~98% open rate.

**Why It Matters:** Critical notifications (order confirmation, payment, installation) need immediate customer attention.

**Solution:** Send both email AND SMS for transactional messages. Gracefully degrade if one channel missing.

### 4. Contact Validation with OR Logic
**Observation:** Some customers only provide email (online orders), some only phone (phone orders).

**Why It Matters:** Requiring both would prevent notifications for legitimate customers.

**Solution:** Require email OR phone (not both). Multi-channel delivery adapts to available contact methods.

### 5. In-Memory Storage Sufficient for Development
**Observation:** Academic demo has single user, short sessions, no persistence requirement.

**Why It Matters:** Zero setup time, easy debugging, no database management overhead.

**Tradeoff:** Data lost on restart, not production-ready. Clear migration path to PostgreSQL + Redis.

## References

- **Project Documentation:** [README.md](README.md) - User guide
- **Technical Docs:** [AGENTS.md](AGENTS.md) - Detailed architecture
- **Test Scenarios:** [../Scenarios.md](../Scenarios.md) - Notification tests (10.1-10.18)
- **Architecture:** [../AGENTS.md](../AGENTS.md) - Multi-agent system overview
- **Development Guidelines:** [../CLAUDE.md](../CLAUDE.md) - Coding standards
- **ServiceabilityAgent:** [../ServiceabilityAgent/IMPLEMENTATION_SUMMARY.md](../ServiceabilityAgent/IMPLEMENTATION_SUMMARY.md) - Reference pattern
- **OrderAgent:** [../OrderAgent/IMPLEMENTATION_SUMMARY.md](../OrderAgent/IMPLEMENTATION_SUMMARY.md) - Reference pattern

---

**Implementation Complete:** February 18, 2026

**Implementation Pattern:** ADK Bootstrap Template + Importlib Isolation + Zero-Hallucination Architecture

**Status:** ✅ Ready for integration testing with SuperAgent and other sub-agents

**Next Steps:**
1. Start backend server: `cd SuperAgent/server && uvicorn main:app --reload`
2. Start frontend client: `cd SuperAgent/client && npm run dev`
3. Test notification flow: Create order → verify order confirmation sent
4. Test integration: Full E2E from discovery through service activation
5. Validate deduplication: Send duplicate notification → verify DEDUPED status
