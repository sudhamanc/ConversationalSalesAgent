## MODIFIED Requirements

### Requirement: Deterministic discovery-to-serviceability handoff

After `discovery_agent` registers or identifies a customer with a complete service address, and serviceability for that customer has not yet been checked in the session, the system SHALL invoke `serviceability_agent` within the same turn, passing the exact structured address. No additional user message SHALL be required. Exception: in the turn in which a customer already present in the CRM (`returning_customer_context` for the same `customer_id`) is first identified, the handoff SHALL NOT occur, and the gateway SHALL record `returning_acknowledged_customer`. On later turns the rule applies as above.

#### Scenario: New company registration triggers coverage check
- **WHEN** the user says "We're Crane.io at 123 Main St, Philadelphia PA 19103" and discovery registers the company
- **THEN** the same streamed response contains the discovery confirmation followed by a `serviceability_agent` coverage result for ZIP 19103

#### Scenario: Serviceability already checked
- **WHEN** discovery updates a customer whose serviceability was already checked in this session
- **THEN** no automatic serviceability handoff occurs

#### Scenario: Returning customer acknowledged first
- **WHEN** discovery identifies an existing CRM customer whose address has not been checked
- **THEN** no serviceability handoff occurs in that turn
- **AND** when discovery runs on the next turn after the customer confirms the location, the handoff occurs

## ADDED Requirements

### Requirement: Suggestion reply templates match explicit requests

A fill-in reply template SHALL be chosen only when the agent's question explicitly asks for that information. A mention of "your location" in an offer SHALL NOT produce an address template. A question confirming "this location" SHALL produce a confirmation chip. When `returning_customer_context.status` is `active_service` and the session has no quote or order, suggestions SHALL use the `returning_active` stage.

#### Scenario: Location mentioned in an offer
- **WHEN** the agent asks "Add other services? (We also have Voice at your location.) Proceed with this quote?"
- **THEN** no suggestion contains `[street, city, state ZIP]`

#### Scenario: Existing-service customer
- **WHEN** `returning_customer_context.status` is `active_service` and there is no `offer_context`
- **THEN** the suggestions come from the `returning_active` stage
