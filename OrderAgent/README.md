# Order Agent

**Order lifecycle management and contract generation for B2B Conversational Sales Agent.**

## Overview

The Order Agent handles PRE-FULFILLMENT operations in the sales pipeline:

- **Cart Management**: Create, update, and manage shopping carts
- **Order Creation**: Create orders with auto-generated customer IDs
- **Order Modification**: Update orders before confirmation
- **Contract Generation**: Generate service contracts with standard terms
- **Order Status Management**: Track orders through lifecycle (draft → pending_payment → payment_approved → confirmed)
- **Order Cancellation**: Cancel orders with reason tracking

## Separation of Concerns

**OrderAgent** (PRE-FULFILLMENT):
- Cart management
- Order creation & modification
- Contract generation
- Order finalization

**ServiceFulfillmentAgent** (POST-ORDER):
- Installation scheduling
- Equipment provisioning
- Technician dispatch
- Service activation

## Key Features

### 1. Auto-Generated Customer IDs
- If customer_id is not provided, the system automatically generates one
- Format: `CUST-YYYYMMDD-XXX` (XXX is hash of customer_name)
- Fixes critical bug where customers don't have pre-existing IDs

### 2. Order Lifecycle Management
Order statuses:
- `draft`: Initial state, can be modified
- `pending_payment`: Awaiting payment validation
- `payment_approved`: Payment confirmed, ready for finalization
- `confirmed`: Order confirmed, ready for fulfillment
- `cancelled`: Order cancelled
- `failed`: Order failed

### 3. JSON Tool Outputs
All tools return structured JSON to prevent LLM hallucination:
```json
{
  "success": true,
  "order_id": "ORD-20260218-456",
  "customer_id": "CUST-20260218-456",
  "customer_name": "Pizza Hut",
  "status": "draft",
  "message": "Order created successfully"
}
```

## Tools

### Cart Tools
- `create_cart(customer_id)` - Create shopping cart
- `add_to_cart(cart_id, service_type, price, quantity)` - Add items
- `remove_from_cart(cart_id, service_type)` - Remove items
- `get_cart(cart_id)` - Retrieve cart
- `clear_cart(cart_id)` - Empty cart

### Order Tools
- `create_order(customer_name, service_address, service_type, contact_phone, customer_id=None, contact_email=None, price=None)` - Create order (customer_id optional)
- `update_order_status(order_id, new_status, notes=None)` - Update status
- `get_order(order_id)` - Retrieve order details
- `modify_order(order_id, service_type=None, price=None)` - Modify draft/pending orders
- `generate_contract(order_id)` - Generate service contract
- `cancel_order(order_id, reason=None)` - Cancel order

## Integration with SuperAgent

This agent is integrated as a sub-agent of SuperAgent using the importlib isolation pattern (see `SuperAgent/super_agent/sub_agents/order/agent.py`).

### Routing Rules
SuperAgent routes to OrderAgent when:
- User wants to place/create an order
- User wants to modify a draft order
- User wants to generate a contract
- User wants to cancel an order
- Cart management operations needed

## Environment Configuration

The agent uses environment variables from SuperAgent's `.env`:
- `GEMINI_MODEL` - Model name (e.g., gemini-3-flash-preview)
- Temperature: 0.0 (deterministic)
- Max tokens: 2048

## Example Usage

```python
from order_agent import order_agent

# Create order (customer_id auto-generated)
result = order_agent.run(
    "Create order for Pizza Hut at 123 Main St, Philadelphia, PA. "
    "Service: Business Fiber 10 Gbps. Contact: 215-555-1234"
)

# Result includes auto-generated customer_id:
# Order ORD-20260218-456 created for Pizza Hut (Customer ID: CUST-20260218-456)
```

## Architecture

Follows ADK Bootstrap Template Structure:
```
OrderAgent/
├── pyproject.toml              # Package definition
├── requirements.txt            # Dependencies
├── README.md                   # This file
├── order_agent/                # Main package
│   ├── __init__.py             # Package exports
│   ├── agent.py                # Agent instance
│   ├── prompts.py              # Instruction templates
│   ├── models/                 # Data models (Order, OrderStatus)
│   ├── tools/                  # Tool functions
│   │   ├── cart_tools.py       # Cart management
│   │   └── order_tools.py      # Order operations
│   └── utils/                  # Utilities
│       └── logger.py           # Logging
└── tests/                      # Test suite
```

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=order_agent --cov-report=html
```

## References

- **System Architecture**: [AGENTS.md](../AGENTS.md)
- **Test Scenarios**: [Scenarios.md](../Scenarios.md) - Section 8 (Order Agent)
- **SuperAgent Integration**: [SuperAgent/super_agent/sub_agents/](../SuperAgent/super_agent/sub_agents/)
