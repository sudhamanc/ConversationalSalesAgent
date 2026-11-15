## ADDED Requirements

### Requirement: Eval results exported to Langfuse

Every eval run SHALL write `evals/results/<timestamp>/run-<n>/cases.jsonl`, one JSON object per scored case, with these fields:
- `key`: the MANIFEST case key
- `tier`: `agents`, `router` or `journeys`
- `set`: the dataset group (agent name, `router` or `journeys`)
- `input`: the user turns
- `expected`: the reference responses and expected trajectory or target
- `actual`: the produced responses and trajectory or target
- `metrics`: a list of `{name, score, threshold, passed}`
- `passed`
- `session_id` when known
- `trace_ids`: for journeys, the per-turn trace ids from the `done` events

`scripts/eval.sh --langfuse` SHALL run the evals with `LANGFUSE_TRACING_ENVIRONMENT=eval` and then `python -m evals.langfuse_sync <results dir>`. The sync SHALL do the following:
- upsert one Langfuse dataset per group (`csa-golden-agents-<agent>`, `csa-golden-router`, `csa-golden-journeys`), with one item per case keyed by a stable id derived from the case key
- record every case as an experiment item in a dataset run named after the results directory, with the git commit and `GEMINI_MODEL` in the run metadata; this uses the Langfuse Python SDK experiment runner, replaying the recorded output without re-running any model
- give each case's experiment trace its input, expected output and actual output, and the case's session id when known
- record one score per metric and a boolean `passed` score on that trace

The sync SHALL run in an environment separate from the services' virtualenv, because langfuse 5.x and google-adk 2.10 require incompatible OpenTelemetry versions. Without `--langfuse`, an eval run SHALL send nothing to Langfuse, even when the keys are in `.env`. The sync SHALL refuse to run without Langfuse keys.

#### Scenario: Router run exported
- **WHEN** `scripts/eval.sh --only router --langfuse` completes
- **THEN** the `csa-golden-router` dataset has a run named after the results directory, with one item per router case and `target_match` and `passed` scores

#### Scenario: Journey linked to its execution traces
- **WHEN** a journey case is exported
- **THEN** its experiment trace belongs to the journey's gateway session, so Langfuse shows it next to that session's `chat_turn` traces

#### Scenario: Default run stays local
- **WHEN** `scripts/eval.sh --only router` runs without `--langfuse`
- **THEN** results are written locally and no request is made to Langfuse
