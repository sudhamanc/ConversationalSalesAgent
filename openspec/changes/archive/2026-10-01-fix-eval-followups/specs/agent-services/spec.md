# Spec Delta: agent-services

## ADDED Requirements

### Requirement: Empty model responses are retried

Agents SHALL use a model wrapper that repeats a non-streaming model call once when the response contains neither text nor a function call.

#### Scenario: Empty response
- **WHEN** Gemini returns a response with no text and no function call
- **THEN** the call is repeated once and the retry's response is used

### Requirement: Credit check reports the score

The payment agent SHALL include the credit score returned by `check_business_credit` together with the decision.

#### Scenario: Conditional approval
- **WHEN** the credit check returns a score of 55 and a conditional decision
- **THEN** the reply states both the score and the conditional approval
