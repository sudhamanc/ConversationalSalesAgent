# Spec Delta: conversation-orchestration

## ADDED Requirements

### Requirement: Company introductions route to discovery

The router SHALL send a message in which the customer introduces their company (with or without an address) to discovery_agent, not serviceability_agent. The deterministic handoff then runs the serviceability check after registration.

#### Scenario: Company with address
- **WHEN** the message is "We're Crane.io at 123 Main St, Philadelphia PA 19103"
- **THEN** the router chooses discovery_agent
