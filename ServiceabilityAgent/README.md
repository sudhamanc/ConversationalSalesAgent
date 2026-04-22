# Serviceability Agent

Deterministic PRE-SALE coverage and infrastructure validation agent.

## Current Role

ServiceabilityAgent validates whether a customer address is serviceable and what infrastructure capabilities exist at that location **before** pricing/order operations.

This agent is **active in SuperAgent**.

## Scope Boundaries

### ServiceabilityAgent does
- Address parsing/normalization/validation
- Coverage verification via GIS-style deterministic tools
- Infrastructure capability output (technology, speed range, zone)

### ServiceabilityAgent does not do
- Product recommendation/comparison (ProductAgent)
- Pricing/discount/totals (OfferManagementAgent)
- Installation scheduling (ServiceFulfillmentAgent)

## Determinism Rules

- Tool-driven outputs only
- Temperature set for deterministic behavior
- No invented infrastructure or coverage claims

## Package Layout

```text
ServiceabilityAgent/
├── serviceability_agent/
│   ├── agent.py
│   ├── prompts.py
│   ├── tools/
│   │   ├── address_tools.py
│   │   └── gis_tools.py
│   └── utils/
├── main.py
└── tests/
```

## SuperAgent Integration

- Wrapper location: `SuperAgent/super_agent/sub_agents/serviceability/agent.py`
- Routing trigger: address/coverage/service availability requests
- Typical downstream handoff: ProductAgent for technical fit, then OfferManagementAgent for pricing

## Local Run

```bash
cd ServiceabilityAgent
pip install -e .
python main.py
```

## Tests

```bash
cd /Users/sudhamanc/Desktop/Github/ConversationalSalesAgent
./.venv/bin/python -m pytest ServiceabilityAgent/tests -q
```

## References

- Root architecture: `AGENTS.md`
- SuperAgent runtime: `SuperAgent/README.md`
- Scenario validation: `Scenarios.md`
