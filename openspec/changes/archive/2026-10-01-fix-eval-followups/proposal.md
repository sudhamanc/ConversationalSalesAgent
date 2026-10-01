# Proposal: Fix Eval Follow-ups

## Why

The scored baseline left four open items:
- The credit-check reply omits the credit score (Scenarios 8.1).
- Agents intermittently return a completely empty model response (seen in faq, payment and product).
- The hallucination judge sometimes produces no score ("not evaluated"), which ADK counts as a failure.
- Journey reply metrics never had a full scored run.

## What Changes

- **Payment prompt:** credit-check replies state the credit score with the decision.
- **`sales_common.models.agent_model()`:** a Gemini model that retries once when a non-streaming response has no text and no function call. All 10 agents use it.
- **`evals/test_agents.py`:** a group whose only failures are "not evaluated" judge results is retried once.
- **Scored targeted run:** payment, product, order, service_fulfillment and journeys.
- **README:** a consolidated baseline results table (no run dates).

BASELINE.md sections affected: 5 (config line: model wrapper).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-services`: adds credit score in replies and the empty-response retry.
- `agent-evaluation`: adds the retry for unscored judge results.

## Non-goals

- Changing judge models or thresholds.

## Impact

- **Code:** `sales_common` (new `models.py`), the 10 agents' `build_agent` model default, payment prompt, `evals/test_agents.py`.
- **Docs:** README, evals/README, BASELINE.md.
