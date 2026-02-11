# Standalone Agent Testing Guide

## Overview

These standalone test scripts allow you to test each agent **independently** without requiring the Super Agent or any other dependencies. This is perfect for:

- Understanding each agent's capabilities
- Testing during development
- Debugging specific agent functionality
- Demonstrating features to stakeholders

## Quick Start

### 1. Test Payment Agent Standalone

```bash
python test_payment_agent_standalone.py
```

**What it tests:**
- ✅ Credit verification (multiple businesses)
- ✅ Payment method validation (Credit Card, ACH, Wire)
- ✅ Fraud risk assessment (low/medium/high risk scenarios)
- ✅ Payment authorization
- ✅ Payment capture
- ✅ Complete payment flows (end-to-end)
- ✅ Agent state and memory management

**Expected Output:**
```
████████████████████████████████████████████████████████████████████████████████
█                                                                              █
█                 PAYMENT AGENT - STANDALONE TEST SUITE                        █
█                        No Super Agent Required                               █
█                                                                              █
████████████████████████████████████████████████████████████████████████████████

================================================================================
  TEST 1: Credit Check
================================================================================

Business: Acme Corporation
  EIN: 12-3456789
  Credit Score: 745
  Credit Tier: Good
  Approved: ✓ YES
  Recommended Credit Limit: $250,000.00
  Factors: Good payment history, Moderate credit utilization
...
```

### 2. Test Service Fulfillment Agent Standalone

```bash
python test_service_agent_standalone.py
```

**What it tests:**
- ✅ Serviceability checks (multiple locations)
- ✅ Network capacity analysis
- ✅ Installation scheduling (standard/expedited/premium)
- ✅ Service provisioning (Internet, Voice, Cloud)
- ✅ Provision status tracking
- ✅ Complete fulfillment flows
- ✅ Multiple service types at same location
- ✅ Agent state and memory management

**Expected Output:**
```
████████████████████████████████████████████████████████████████████████████████
█                                                                              █
█            SERVICE FULFILLMENT AGENT - STANDALONE TEST SUITE                 █
█                        No Super Agent Required                               █
█                                                                              █
████████████████████████████████████████████████████████████████████████████████

================================================================================
  TEST 1: Serviceability Checks
================================================================================

Location: Philadelphia (Serviceable)
  Address: 123 Market Street, Philadelphia, PA
  Serviceable: ✓ YES
  Status: AVAILABLE
  Available Services: 2
    - Business Internet (internet)
      Speeds: 100M, 500M, 1G, 10G
    - Business Voice (voice)
...
```

## Test Coverage

### Payment Agent Tests (7 Test Suites)

1. **Credit Check**
   - Multiple business EINs
   - Different credit scores
   - Credit tier classification
   - Credit limit recommendations

2. **Payment Validation**
   - Valid credit cards (Visa, Mastercard)
   - Valid ACH
   - Invalid/expired cards
   - Wire transfers

3. **Fraud Assessment**
   - Low risk scenarios
   - Medium risk (high amounts)
   - High risk (new customer, VPN, rapid checkout)
   - Risk factor analysis

4. **Payment Authorization**
   - Multiple authorization amounts
   - Success/decline scenarios
   - Authorization ID generation

5. **Payment Capture**
   - Full capture
   - Partial capture
   - Authorization expiration

6. **Complete Payment Flow**
   - End-to-end credit → validation → fraud → authorization
   - Multiple payment types
   - Success/failure paths

7. **State & Memory**
   - Agent state inspection
   - Memory timeline
   - Filtered memory queries

### Service Fulfillment Tests (8 Test Suites)

1. **Serviceability Checks**
   - Serviceable locations
   - Non-serviceable locations
   - Multiple service types
   - Speed tier availability

2. **Network Capacity**
   - Small business bandwidth
   - Enterprise bandwidth
   - Capacity exceeded scenarios
   - Utilization analysis

3. **Installation Scheduling**
   - Standard installation
   - Expedited installation
   - Premium installation
   - Slot availability
   - Appointment creation

4. **Service Provisioning**
   - Internet provisioning
   - Voice provisioning (multi-line)
   - Enterprise services
   - Credential generation

5. **Status Tracking**
   - Active order status
   - Non-existent order handling
   - Provisioning queue

6. **Complete Fulfillment Flow**
   - End-to-end serviceability → capacity → scheduling
   - Success scenarios
   - Failure scenarios

7. **Multiple Services**
   - Same location, different services
   - Feature availability
   - SLA information

8. **State & Memory**
   - Agent state inspection
   - Operational statistics
   - Memory management

## No Dependencies on Other Agents

These tests are **completely standalone**:

```python
# Only imports needed:
from base_agent import AgentContext
from payment_agent import PaymentAgent
# OR
from service_fulfillment_agent import ServiceFulfillmentAgent

# No Super Agent import required!
# No other agent dependencies!
```

## Understanding the Output

### Success Indicators
- ✓ marks indicate successful operations
- ✗ marks indicate expected failures (for testing error handling)

### Agent State
At the end of each test suite, you'll see:
```
Agent State:
  Agent ID: payment_agent_001
  Agent Name: Payment Agent
  Status: completed
  Tools Available: 5
  Memory Entries: 15
```

This shows:
- The agent's current status
- Available tools/capabilities
- Number of operations tracked in memory

## Customizing Tests

### Modify Test Data

Edit the test files to use your own data:

**Payment Agent:**
```python
# In test_payment_agent_standalone.py
businesses = [
    {"ein": "YOUR-EIN", "name": "Your Business Name"},
    # Add more...
]
```

**Service Fulfillment Agent:**
```python
# In test_service_agent_standalone.py
locations = [
    {
        'address': {
            'street': 'Your Address',
            'city': 'Your City',
            'state': 'ST',
            'zip_code': '12345'
        },
        'service_type': 'internet',
        'speed_tier': '1G'
    }
]
```

### Run Individual Tests

You can run individual test functions:

```python
# In test_payment_agent_standalone.py
async def main():
    # Comment out tests you don't want to run
    await test_credit_check()
    # await test_payment_validation()
    # await test_fraud_assessment()
    # ...
```

## Debugging

### Enable Detailed Logging

Both agents have built-in logging. To see more details:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Agent Memory

After any test:
```python
# Get all operations
memory = agent.get_memory()
for entry in memory:
    print(entry)

# Get specific operations
credit_checks = agent.get_memory(filter_type='credit_check')
```

### Check Agent State

```python
state = agent.get_state()
print(f"Status: {state['status']}")
print(f"Tools: {state['tools']}")
print(f"Memory: {state['memory_size']} entries")
```

## Integration with Your System

Once you've tested the agents standalone, integrate them:

1. **Keep the base agents as-is** - they work independently
2. **Your Super Agent can import them**:
   ```python
   from payment_agent import PaymentAgent
   from service_fulfillment_agent import ServiceFulfillmentAgent
   ```
3. **Coordinate via A2A messages**:
   ```python
   # Your Super Agent sends messages
   message = await super_agent.send_message(
       receiver="payment_agent_001",
       content={...}
   )
   
   # Payment Agent handles it
   response = await payment_agent.receive_message(message)
   ```

## Running All Tests

To run both agent tests in sequence:

```bash
# Run both test suites
python test_payment_agent_standalone.py && python test_service_agent_standalone.py
```

Or create a simple runner:

```bash
# run_all_tests.sh
#!/bin/bash
echo "Testing Payment Agent..."
python test_payment_agent_standalone.py

echo ""
echo "Testing Service Fulfillment Agent..."
python test_service_agent_standalone.py

echo ""
echo "All tests completed!"
```

## What's Next?

After testing standalone:

1. ✅ Verify each agent works independently
2. ✅ Understand the capabilities and APIs
3. ✅ Customize for your business logic
4. ⏭️ Integrate with your Super Agent (when ready)
5. ⏭️ Connect to production APIs
6. ⏭️ Deploy to your infrastructure

## Support

If you encounter issues:

1. Check the agent logs (printed to console)
2. Inspect agent memory: `agent.get_memory()`
3. Verify agent state: `agent.get_state()`
4. Review the source code comments
5. Modify test data to match your scenarios

---

**Happy Testing! 🚀**

These standalone tests prove that each agent is fully functional on its own, ready to be integrated into your B2B sales system whenever your Super Agent is ready.
