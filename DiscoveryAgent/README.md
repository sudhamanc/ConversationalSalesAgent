# Discovery Agent

Discovery-phase agent for company identification, prospect lookup/creation, and BANT-oriented qualification context.

## Overview

The DiscoveryAgent handles early sales-intelligence tasks in the conversational flow:
- company discovery and matching,
- contact and insight retrieval,
- lead qualification context,
- structured handoff data for downstream agents.

It includes read/write database operations for company/contact/opportunity/insight records and is used as the first business-context step in SuperAgent.

## Current Role

The DiscoveryAgent is the first major business-context agent in the sales flow. It:
- extracts company + location details from conversation,
- looks up existing records in SQLite,
- creates/updates prospect records when needed,
- supports qualification signals used downstream.

This agent is **active in SuperAgent**.

## Scope Boundaries

### DiscoveryAgent does
- Prospect/company lookup and enrichment
- New company/contact record creation
- Qualification context capture (BANT-related fields)
- Structured data return for reliable handoff
- Opportunity context updates for downstream sales stages

### DiscoveryAgent does not do
- Serviceability verification (ServiceabilityAgent)
- Product technical fit (ProductAgent)
- Pricing/discounting (OfferManagementAgent)
- Order/payment/fulfillment execution

## Data Model (High-Level)

Primary SQLite entities used by Discovery flow:
- `accounts`: company profile, region, customer/prospect status, products
- `contacts`: stakeholders and decision roles
- `opportunities`: BANT components, score, and prioritization bucket
- `insights`: buying signals, pain points, positioning notes
- `spend`: spend profile and media breakdown (when available)

## API/Run Modes

- `main.py`: local/agent bootstrap entrypoint
- `main_server.py`: FastAPI server mode for chat-style requests
- Typical endpoint in standalone mode: `POST /chat`

## Package Layout

```text
DiscoveryAgent/
├── bootstrap_agent/
│   ├── agent.py
│   ├── sub_agents/
│   │   ├── discovery/
│   │   └── lead_gen/
│   └── ...
├── data/
│   └── discover_prospecting_clean.db
├── main.py
├── main_server.py
└── tests/
```

## SuperAgent Integration

- Wrapper location: `SuperAgent/super_agent/sub_agents/discovery/agent.py`
- Integration pattern: importlib isolation (ADK parent-binding safe)
- Routed when user provides company/business identity details.

## Typical Conversation Responsibilities

- Parse company and location from user message
- Determine existing customer vs new prospect path
- Capture qualification context (BANT-related signals)
- Return structured fields so Serviceability/Product/Offer flows can continue deterministically

## Local Run

```bash
cd DiscoveryAgent
pip install -e .
python main.py
```

## Tests

```bash
cd /Users/sudhamanc/Desktop/Github/ConversationalSalesAgent
./venv/bin/python -m pytest DiscoveryAgent -q
```

## References

- Root architecture: `AGENTS.md`
- SuperAgent runtime: `SuperAgent/README.md`
- Scenario validation: `Scenarios.md`
