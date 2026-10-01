# Spec Delta: agent-evaluation

## ADDED Requirements

### Requirement: Goldens are independent of run order and date

Golden cases SHALL NOT depend on data written by other cases in the same run. Cases that write data use their own seeded customer, and the eval database is reset before the journey tier. Cases whose correct reply contains dates relative to today SHALL list `final_response_match_v2` in `skip_metrics` (with a `skip_reason`) in MANIFEST.json; their trajectory and rubrics are still scored.

#### Scenario: Read-after-write between cases
- **WHEN** one case lists quotes and another case creates quotes for a customer
- **THEN** the two cases use different customers, so their results do not depend on execution order

#### Scenario: Date-relative reply
- **WHEN** a case books "the earliest available slot"
- **THEN** its exact reply is not compared with the recorded reference, but its tool calls and rubrics are

### Requirement: Judges see tool results

Journey invocations SHALL keep function-call ids so ADK's judges can pair every tool call with its response. Rubrics SHALL only state properties a judge can verify from the user prompt and the reply; grounding in tool data is scored by `hallucinations_v1`.

#### Scenario: Journey grounding
- **WHEN** a journey turn states data returned by a remote agent's tool
- **THEN** `hallucinations_v1` sees the paired tool response and does not mark the claim unsupported
