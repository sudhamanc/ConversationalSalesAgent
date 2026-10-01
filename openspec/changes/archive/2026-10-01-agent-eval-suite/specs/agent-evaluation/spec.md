# Spec Delta: agent-evaluation

## ADDED Requirements

### Requirement: Golden datasets

The repository SHALL contain golden datasets under `evals/golden/` in ADK `EvalSet` format covering all 10 agents, the router and the end-to-end journeys in `Scenarios.md`. Each golden turn SHALL define the expected trajectory and a reference response. Golden tool calls SHALL list only arguments that are stable across runs. `evals/golden/MANIFEST.json` SHALL record, per case, its scenario ID and review status (`reviewed`, `reviewed_by`, `reviewed_at`), plus hashes of the seed files the goldens were reviewed against.

#### Scenario: Unreviewed golden
- **WHEN** a case is marked `reviewed: false`
- **THEN** live evals skip it and report it as pending review

#### Scenario: Seed data changed
- **WHEN** a file in `db/seed/` no longer matches the manifest hash
- **THEN** `evals/test_golden_valid.py` fails, naming the changed file

#### Scenario: Golden references an unknown tool
- **WHEN** a golden tool call names a tool the agent does not expose
- **THEN** `evals/test_golden_valid.py` fails, naming the case and tool

### Requirement: Trajectory and response are both scored

Each eval tier SHALL score the trajectory and the response of every evaluated turn against the golden case:
- **Agents:** tool trajectory (`golden_trajectory_v1`) plus `final_response_match_v2`, `rubric_based_final_response_quality_v1` and, for agents with tools, `hallucinations_v1`.
- **Router:** the chosen target plus a schema-valid `RouteDecision` that did not stop at `MAX_TOKENS`.
- **Journeys:** the per-turn answering-agent sequence and tool trajectory plus the per-turn response metrics.

#### Scenario: Wrong tool arguments
- **WHEN** an agent calls the expected tool with a different stable argument than the golden (e.g. another ZIP code)
- **THEN** that case's trajectory score falls below threshold and the eval fails

#### Scenario: Router truncation
- **WHEN** the router's response ends with `MAX_TOKENS`
- **THEN** the router eval fails regardless of accuracy

### Requirement: Isolated, opt-in eval runs

`scripts/eval.sh [--only <tiers or agents>] [--runs N]` SHALL reset a dedicated `csa_eval` database to seed data before running and SHALL NOT write to the development database. Live eval tests SHALL be skipped unless `RUN_EVALS=1`. Results SHALL be written to `evals/results/<timestamp>/` with a summary of trajectory and response scores per case, and the script SHALL exit non-zero when any case fails.

#### Scenario: Normal test runs stay offline
- **WHEN** `pytest` runs without `RUN_EVALS=1`
- **THEN** no Gemini request is made and only golden validation runs

#### Scenario: Dev stack running during journeys
- **WHEN** `eval.sh --only journeys` runs while the gateway port is in use
- **THEN** it exits non-zero asking to stop the dev stack, and starts nothing
