# Payment Agent

Deterministic transactional agent for credit and payment authorization steps.

## Current Role

PaymentAgent handles payment-phase checks after order creation/checkout.

This agent is **active in SuperAgent**.

## Scope Boundaries

### PaymentAgent does
- Credit/financial validation workflows
- Payment method validation and authorization
- Transaction status handling for downstream updates

### PaymentAgent does not do
- Quote pricing/discount computation (OfferManagementAgent)
- Cart/order creation (OrderAgent)
- Installation scheduling (ServiceFulfillmentAgent)

## Determinism Rules

- Deterministic tool-driven execution
- Structured outputs for reliable orchestration handoff
- No freeform financial inventing

## Package Layout

```text
PaymentAgent/
├── payment_agent/
│   ├── agent.py
│   ├── prompts.py
│   ├── tools/
│   └── models/
├── main.py
└── tests/
```

## SuperAgent Integration

- Wrapper location: `SuperAgent/super_agent/sub_agents/payment/agent.py`
- Triggered after order flow reaches payment stage

## Local Run

```bash
cd PaymentAgent
pip install -e .
python main.py
```

## Tests

```bash
cd /Users/sudhamanc/Desktop/Github/ConversationalSalesAgent
./venv/bin/python -m pytest PaymentAgent/tests -q
```

## Security Note

This repository is an academic/demo system. Production deployment requires full PCI/PII controls and hardened secrets/observability.

## References

- Root architecture: `AGENTS.md`
- SuperAgent runtime: `SuperAgent/README.md`
- Scenario validation: `Scenarios.md`
