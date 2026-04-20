# OrderAgent Documentation

**B2B Conversational Sales Agent - Order Management System**


## Agent Overview

**Name**: `order_agent`  
**Type**: Deterministic Tool-Based Agent  
**Phase**: PRE-FULFILLMENT  
**Location**: `OrderAgent/order_agent/`  
**Integration**: `SuperAgent/super_agent/sub_agents/order/`

---

## Responsibilities

### What OrderAgent DOES (PRE-FULFILLMENT):

✅ Shopping cart management (create, add, remove, view, clear)  
✅ Order creation with **auto-generated customer IDs**  
✅ Order modification (draft and pending_payment orders only)  
✅ Service contract generation  
✅ Order status updates through lifecycle  
✅ Order cancellation with reason tracking  

### What OrderAgent DOES NOT DO (POST-ORDER):

❌ Installation scheduling (ServiceFulfillmentAgent)  
❌ Equipment provisioning (ServiceFulfillmentAgent)  
❌ Technician dispatch (ServiceFulfillmentAgent)  
❌ Service activation (ServiceFulfillmentAgent)  
❌ Payment processing (PaymentAgent)  
❌ Pricing calculation (OfferManagementAgent - active)  

---

## Critical Bug Fixed: Auto-Generated Customer IDs

### The Problem (Before OrderAgent)

```python
# ServiceFulfillmentAgent/tools/order_tools.py (OLD)
def create_order(customer_name, customer_id, ...):
    # customer_id was MANDATORY
    # If not provided → ORDER FAILED
```

**User Experience**:
```
User: "I'd like to order Business Fiber 10 Gbps"
Agent: "Please provide your Customer ID"
User: "I don't have one"
Agent: ❌ "Error: customer_id is required"
```

### The Solution (OrderAgent)

```python
# OrderAgent/order_agent/tools/order_tools.py (NEW)
def create_order(customer_name, customer_id=None, ...):
    if not customer_id:
        customer_id = f"CUST-{datetime.now().strftime('%Y%m%d')}-{hash(customer_name) % 1000:03d}"
```

**User Experience**:
```
User: "I'd like to order Business Fiber 10 Gbps for Pizza Hut"
Agent: ✅ "Order ORD-20260218-456 created successfully!"
       "Customer ID: CUST-20260218-456 (auto-generated)"
```

---

## Tools Reference

### Cart Management Tools

#### 1. `create_cart(customer_id: str)`
Creates a new shopping cart for a customer.

**Returns**:
```json
{
  "success": true,
  "cart_id": "CART-20260218143025-456",
  "cart": {...}
}
```

#### 2. `add_to_cart(cart_id: str, service_type: str, price: float, quantity: int = 1)`

Adds a service/product to the cart.

**Example**:

```python
add_to_cart("CART-123", "Business Fiber 10 Gbps", 999.0, 1)
```

#### 3. `remove_from_cart(cart_id: str, service_type: str)`

Removes a service/product from the cart.

#### 4. `get_cart(cart_id: str)`

Retrieves current cart contents.

#### 5. `clear_cart(cart_id: str)`

Empties all items from the cart.

---

### Order Management Tools

#### 1. `create_order(...)`

Creates a new service order.

**Parameters**:

- `customer_name` (required): Customer or business name
- `service_address` (required): Installation address
- `service_type` (required): Type of service ordered
- `contact_phone` (required): Customer phone
- `customer_id` (optional): Customer ID - **AUTO-GENERATED if not provided**
- `contact_email` (optional): Customer email
- `price` (optional): Service price

**Returns**:
```json
{
  "success": true,
  "order_id": "ORD-20260218-456",
  "customer_id": "CUST-20260218-456",
  "customer_name": "Pizza Hut",
  "service_address": "123 Main St, Philadelphia, PA",
  "service_type": "Business Fiber 10 Gbps",
  "status": "draft",
  "total_amount": 999.0,
  "message": "Order created successfully. Customer ID: CUST-20260218-456"
}
```

#### 2. `update_order_status(order_id: str, new_status: str, notes: str = None)`

Updates order status.

**Valid Statuses**:

- `draft` - Initial state
- `pending_payment` - Awaiting payment
- `payment_approved` - Payment confirmed
- `confirmed` - Order finalized
- `cancelled` - Order cancelled
- `failed` - Order failed

#### 3. `get_order(order_id: str)`

Retrieves order details.

#### 4. `modify_order(order_id: str, service_type: str = None, price: float = None)`

Modifies an existing order (only draft/pending_payment).

**Restrictions**:

- Only `draft` or `pending_payment` orders can be modified
- `confirmed`, `cancelled`, `failed` orders cannot be changed

#### 5. `generate_contract(order_id: str)`

Generates a service contract for an order.

**Returns**:

```json
{
  "success": true,
  "contract": {
    "contract_id": "CONT-ORD-20260218-456",
    "order_id": "ORD-20260218-456",
    "terms": {
      "duration": "12 months",
      "auto_renewal": true,
      "early_termination_fee": 2997.0,
      "billing_cycle": "monthly",
      "payment_terms": "NET-30"
    }
  }
}
```

#### 6. `cancel_order(order_id: str, reason: str = None)`

Cancels an order.

---

## Order Lifecycle

```
┌───────────┐
│   DRAFT   │ ← Order created (default status)
└─────┬─────┘
      │ update_order_status("pending_payment")
      ▼
┌────────────────┐
│PENDING_PAYMENT │ ← Awaiting payment validation
└────────┬───────┘
         │ PaymentAgent validates → update_order_status("payment_approved")
         ▼
┌──────────────────┐
│ PAYMENT_APPROVED │ ← Payment confirmed
└────────┬─────────┘
         │ Customer confirms → update_order_status("confirmed")
         ▼
┌───────────┐
│ CONFIRMED │ ← Order finalized, ready for fulfillment
└───────────┘
         │ Transfer to ServiceFulfillmentAgent for installation

Alternative paths:
- cancel_order() → CANCELLED
- Payment fails → FAILED
```

---

## Integration with SuperAgent

### Routing Rules

**SuperAgent routes to OrderAgent when**:

- User says: "I'd like to order [product]"
- User says: "Create an order"
- User says: "Add to cart"
- User says: "Modify my order"
- User says: "Generate contract"
- User says: "Cancel order [ID]"

**Example Conversation Flow**:
```
1. User: "Hi"
   → GreetingAgent

2. User: "We're Pizza Hut at 123 Main St, Philadelphia, PA"
   → DiscoveryAgent (registers company)

3. User: "yes" (confirms serviceability check)
   → ServiceabilityAgent (validates address)

4. User: "Show me products"
   → ProductAgent (presents Business Fiber options)

5. User: "I'll take Business Fiber 10 Gbps"
   → OrderAgent ✨ (creates order with auto-generated customer_id)

6. OrderAgent: "Order ORD-20260218-456 created. Customer ID: CUST-20260218-456. Would you like to proceed with payment?"

7. User: "Yes"
   → PaymentAgent (validates payment)

8. User: "Schedule installation"
   → ServiceFulfillmentAgent (books appointment)
```

---

## SuperAgent Integration Files

### 1. Wrapper (Importlib Isolation)

**File**: `SuperAgent/super_agent/sub_agents/order/agent.py`

```python
# Loads OrderAgent using importlib to avoid parent-binding conflicts
import importlib.util
# ... loads all dependencies (models, utils, tools, prompts)
order_agent = _agent_mod.order_agent
```

### 2. SuperAgent Updates

**File**: `SuperAgent/super_agent/agent.py`

```python
from .sub_agents.order import order_agent

sub_agents=[
    discovery_agent,
    serviceability_agent,
    product_agent,
    payment_agent,
    order_agent,  # ← NEW
    service_fulfillment_agent,
    greeting_agent,
    faq_agent
]
```

### 3. Routing Prompts
**File**: `SuperAgent/super_agent/prompts.py`

Added routing rule #4 for order creation, cart management, contract generation, and order cancellation.

---

## Configuration

### Environment Variables
Uses existing SuperAgent environment:
- `GEMINI_MODEL` - e.g., `gemini-3-flash-preview`

### Agent Settings
```python
name = "order_agent"
model = GEMINI_MODEL
temperature = 0.0  # Deterministic
max_output_tokens = 2048
safety_settings = BLOCK_LOW_AND_ABOVE
```

---

## JSON Tool Outputs (Zero-Hallucination)

All tools return structured JSON with explicit fields:

**Why JSON?**
- Prevents LLM from rephrasing or modifying critical data
- Ensures exact values (order IDs, customer IDs, amounts) are preserved
- Enables deterministic parsing by downstream agents

**Example**:
```json
{
  "success": true,
  "order_id": "ORD-20260218-456",
  "customer_id": "CUST-20260218-456",
  "total_amount": 999.0,
  "status": "draft"
}
```

Agent instructions explicitly state:
> "All tools return JSON responses - parse them to extract the data you need"

---

## Testing

### Unit Tests
```bash
cd OrderAgent
pytest tests/ -v --cov=order_agent
```

**Key Test Cases**:
- `test_create_order_without_customer_id()` - Verify auto-generation
- `test_create_order_with_existing_id()` - Verify existing ID preserved
- `test_json_output_format()` - Verify all tools return valid JSON
- `test_modify_draft_order()` - Verify modification allowed
- `test_modify_confirmed_order()` - Verify modification blocked

### Integration Tests
```bash
cd SuperAgent
pytest test_integration.py::test_order_flow -v
```

**Test Flow**:
1. User selects product
2. User requests order
3. Verify OrderAgent creates order with auto-generated customer_id
4. Verify order status is "draft"
5. Verify order can be modified
6. Update status to "confirmed"
7. Verify order cannot be modified after confirmation

---

## Common Issues & Solutions

### Issue 1: "Customer ID not found"
**Cause**: User provides company name without existing customer_id  
**Solution**: ✅ Auto-generated by OrderAgent (no longer an issue)

### Issue 2: "Cannot modify confirmed order"
**Cause**: User tries to modify order after it's confirmed  
**Solution**: Inform user order is finalized, offer to cancel and create new order

### Issue 3: "Order not found"
**Cause**: User provides invalid order ID  
**Solution**: Verify order ID format, check if order exists

### Issue 4: Agent creates duplicate orders
**Cause**: User submits order request multiple times  
**Solution**: Implement order deduplication logic (future enhancement)

---

## Future Enhancements (Phase 2)

### 1. Order Persistence
- Store orders in SQLite/PostgreSQL
- Enable order retrieval across sessions

### 2. Cart Expiration
- Auto-expire carts after 30 minutes of inactivity
- Send cart abandonment reminders

### 3. Order Deduplication
- Detect duplicate order submissions
- Return existing order instead of creating duplicate

### 4. Order History
- Track all order modifications
- Audit trail for compliance

### 5. Bulk Orders
- Support multiple services in single order
- Discount calculation for bulk purchases

---

## References

1. **System Architecture**: [AGENTS.md](../AGENTS.md)
2. **Test Scenarios**: [Scenarios.md](../Scenarios.md) - Section 8
3. **Implementation Summary**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
4. **ServiceabilityAgent (Pattern Reference)**: [ServiceabilityAgent/serviceability_agent/agent.py](../ServiceabilityAgent/serviceability_agent/agent.py)

---

## Support

For issues or questions:
1. Check [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for setup details
2. Review [Scenarios.md](../Scenarios.md) for expected behavior
3. Run unit tests to verify installation
4. Check SuperAgent logs for routing issues
