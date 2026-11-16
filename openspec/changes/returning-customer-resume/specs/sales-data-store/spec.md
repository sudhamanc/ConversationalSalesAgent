## ADDED Requirements

### Requirement: Serviceability checks are stored

Migration `006_serviceability_checks.sql` SHALL create `serviceability_checks`. `serviceability_agent` SHALL insert one row per successful `check_service_availability`: the customer (when known), the address, `is_serviceable`, the recorded `serviceability_context` JSON and `checked_at`. An insert failure SHALL be logged and SHALL NOT fail the check. `sales_common.repositories.customer_state` SHALL return the latest check for the customer.

#### Scenario: Check recorded
- **WHEN** `check_service_availability` succeeds for a known customer
- **THEN** a `serviceability_checks` row exists with that customer id and ZIP
