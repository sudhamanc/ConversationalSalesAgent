# Spec Delta: agent-evaluation

## ADDED Requirements

### Requirement: Unscored judge results are retried

When an agent group's only failures are metrics the judge did not evaluate, the eval SHALL retry that group once before reporting failure.

#### Scenario: Judge returns no score
- **WHEN** `hallucinations_v1` is "not evaluated" for a case and nothing else failed
- **THEN** the group is evaluated again and the second result is reported
