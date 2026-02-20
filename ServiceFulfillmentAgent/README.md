# Service Fulfillment Agent

Deterministic POST-SALE agent for installation/provisioning and service activation workflows.

## Current Role

ServiceFulfillmentAgent executes fulfillment after payment/order confirmation.

This agent is **active in SuperAgent**.

## Scope Boundaries

### ServiceFulfillmentAgent does
- Installation slot coordination/scheduling workflows
- Provisioning and activation progression
- Fulfillment status transitions and completion signaling

### ServiceFulfillmentAgent does not do
- PRE-SALE address/coverage checks (ServiceabilityAgent)
- Product recommendation (ProductAgent)
- Pricing/discounting (OfferManagementAgent)
- Payment authorization (PaymentAgent)

## Package Layout

```text
ServiceFulfillmentAgent/
├── service_fulfillment_agent/
│   ├── agent.py
│   ├── prompts.py
│   ├── tools/
│   └── models/
├── main.py
└── tests/
```

## SuperAgent Integration

- Wrapper location: `SuperAgent/super_agent/sub_agents/service_fulfillment/agent.py`
- Triggered after successful order + payment flow

## Local Run

```bash
cd ServiceFulfillmentAgent
pip install -e .
python main.py
```

## Tests

```bash
cd /Users/sudhamanc/Desktop/Github/ConversationalSalesAgent
./venv/bin/python -m pytest ServiceFulfillmentAgent/tests -q
```

## References

- Root architecture: `AGENTS.md`
- SuperAgent runtime: `SuperAgent/README.md`
- Scenario validation: `Scenarios.md`
