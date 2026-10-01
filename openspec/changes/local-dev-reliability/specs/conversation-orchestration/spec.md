# Spec Delta: conversation-orchestration

## ADDED Requirements

### Requirement: Router output budget

The `route_intent` router SHALL complete its `RouteDecision` JSON within its output budget. On `gemini-3*` models it SHALL request `thinking_level=MINIMAL`, and its `max_output_tokens` SHALL be at least 1024.

#### Scenario: Gemini 3 routing
- **WHEN** `GEMINI_MODEL=gemini-3-flash-preview` and a message needs LLM routing
- **THEN** the router response finishes with `STOP` and parses as a `RouteDecision`
