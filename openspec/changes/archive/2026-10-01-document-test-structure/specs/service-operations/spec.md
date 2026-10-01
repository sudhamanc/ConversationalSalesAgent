# Spec Delta: service-operations

## ADDED Requirements

### Requirement: Test layout documented

README.md SHALL describe where each kind of test lives:
- per-package unit tests in `<package>/tests/`
- gateway tests
- cross-service tests in the root `tests/`
- golden evals in `evals/`
- live E2E

It SHALL explain why unit tests live next to their package, and give the command to run each kind.

#### Scenario: Reader looks for library tests
- **WHEN** a reader wonders why `libs/sales_common/tests/` is not under the root `tests/`
- **THEN** the README test-structure section explains the per-package layout and what the root `tests/` holds
