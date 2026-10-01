# Golden-dataset eval suite

Every other test suite in this repo replaces Gemini with a scripted model. This suite runs the **real model** against **golden datasets**: curated, human-reviewed conversations that record the expected **trajectory** (answering agents, tool calls with arguments) and a **reference response** for every turn. Each eval scores both.

Design and requirements: [openspec/changes/archive/2026-10-01-agent-eval-suite](../openspec/changes/archive/2026-10-01-agent-eval-suite/).

## Tiers

| Tier | Runner | What runs | Trajectory | Response |
|---|---|---|---|---|
| Agents | `test_agents.py` | each of the 10 agents in-process via ADK `AgentEvaluator` | `golden_trajectory_v1` | `final_response_match_v2`, `rubric_based_final_response_quality_v1`, `hallucinations_v1` (agents with tools) |
| Router | `test_router.py` | `route_intent` (`build_router`) on JSON routing inputs | chosen target = golden target (or `allowed_targets`) | valid `RouteDecision`, finish `STOP` (`MAX_TOKENS` fails) |
| Journeys | `test_journeys.py` | full stack over HTTP/SSE; tool trace read from the gateway session | answering agents per turn, `golden_trajectory_v1`, required events, no errors | same ADK response metrics per turn |

`golden_trajectory_v1` (`metrics.py`) requires the golden tool calls to appear in order (extra calls allowed) and every argument the golden lists to match (case/whitespace-insensitive strings, numeric numbers, lists as multisets). Goldens list only **stable** arguments: omit ids created during the run, dates and tokens.

## Layout

```
evals/golden/
  agents/<agent>/<agent>.evalset.json   ADK EvalSet (golden turns: user, tool_uses, final_response, rubrics)
  agents/<agent>/test_config.json       ADK EvalConfig: metrics, thresholds, judge model
  router/router.evalset.json            user = routing input JSON, final_response = {"target": ...}
  router/router_config.json             accuracy thresholds
  journeys/<scenario>.evalset.json      multi-turn journeys (+ journeys/test_config.json)
  MANIFEST.json                         per case: scenario_id, review status, router targets,
                                        journey turn_agents/turn_events; seed-file hashes
  tool_schemas.json                     snapshot of every agent's tool parameters
```

ADK eval models forbid extra fields, so everything that is not ADK data lives in `MANIFEST.json` under the case key `<set id>/<eval_id>` (e.g. `agents/discovery_agent/discovery_agent/existing-company-found`).

## Running

Prerequisites: PostgreSQL (`scripts/db.sh up`), the venv (`scripts/setup_local.sh`), and a Gemini key **with billing** (`GOOGLE_API_KEY`). The free tier (20 requests/day) cannot run the suite; a full run is roughly 1,000–1,500 requests including judge calls (estimate).

```bash
scripts/eval.sh                                   # agents + router + journeys
scripts/eval.sh --only discovery,serviceability   # selected agents
scripts/eval.sh --only router
scripts/eval.sh --only journeys                   # stop the dev stack first (scripts/stop_local.sh)
scripts/eval.sh --runs 3                          # 3 independent runs; a case must pass in all
```

`eval.sh` installs `evals/requirements.txt` (`google-adk[eval]`) when missing, creates `csa_eval` (`EVAL_DATABASE_URL`) and **resets it to `db/seed` before every run**. The dev database is never used. Results go to `evals/results/<timestamp>/` (gitignored): junit XML, per-agent CSV, `router.json`, journey JSON and `summary.txt`.

| Variable | Default | Purpose |
|---|---|---|
| `EVAL_DATABASE_URL` | `postgresql://csa:csa@localhost:5432/csa_eval` | isolated eval database |
| `EVAL_JUDGE_MODEL` | `gemini-3-flash-preview` (in `test_config.json`) | LLM judge for response metrics |
| `EVAL_JUDGE_SAMPLES` | `3` (in `test_config.json`) | judge samples per metric |
| `EVAL_GATEWAY_URL` | `http://127.0.0.1:8000` | journeys |

Offline checks (no key, no database) run with every `pytest`: `pytest evals -q` runs `test_golden_valid.py` and `test_metrics.py`; live tests are skipped unless `RUN_EVALS=1`.

## Golden lifecycle

Only **reviewed** cases run. New and re-recorded cases are drafts (`reviewed: false`).

1. **Author** the user turns, expected tool calls (stable arguments only) and rubrics from [Scenarios.md](../Scenarios.md). Tool names and parameters are checked against `tool_schemas.json`.
2. **Record** reference responses from the real model, against the eval database:
   ```bash
   EVAL_DATABASE_URL=postgresql://csa:csa@localhost:5432/csa_eval \
     venv/bin/python -m evals.record_golden --set agents/discovery_agent/discovery_agent
   venv/bin/python -m evals.record_golden --set router/router          # router references are authored labels
   scripts/eval.sh --only journeys --record                               # journeys
   ```
   `record_golden` prints the tool calls the model actually made; compare them with the golden trajectory.
3. **Review** and approve. Approval refuses cases without reference responses:
   ```bash
   venv/bin/python -m evals.review --list --pending
   venv/bin/python -m evals.review --show agents/discovery_agent/discovery_agent/existing-company-found
   venv/bin/python -m evals.review --approve <key> [<key> ...] --by "Your Name"
   ```
4. **Change on purpose:** `record_golden --refresh --case <id>` overwrites trajectory and response with current behavior and marks the case unreviewed; review the diff in the PR.

When `db/seed/*.sql` changes, `test_golden_valid.py` fails until goldens that reference seed data (customer ids, orders, appointments, ZIPs) are re-checked and `seed_hashes` updated (any `evals.review --approve` refreshes them). When an agent's tools change, run `python -m evals.record_golden --snapshot-tools` (needs catalog :8101 and serviceability :8102).

`EVAL_INCLUDE_DRAFTS=1` scores unreviewed-but-recorded cases. It exists only to debug the suite itself; those scores are not golden results and `eval.sh` never sets it.

## Baselines

Thresholds start lenient. Record the first full run here, then tighten `test_config.json` / `router_config.json`.

| Date | Model | Agents | Router | Journeys |
|---|---|---|---|---|
| 2026-09-30 | gemini-3-flash-preview (judge: same) | serviceability 6/6, all metrics 1.0 (other agents not yet scored) | 57/58 (98.3%), rule cases 100% | recorded and reviewed; scored run pending |

Review status: 106 of 115 goldens approved; 9 pending because of agent defects listed in `openspec/changes/archive/*agent-eval-suite/tasks.md` (Follow-ups). `python -m evals.review --list --pending` shows them.

## Troubleshooting

- `402 ... prepayment credits are depleted` / `429 RESOURCE_EXHAUSTED`: the Gemini project is out of credits or on the free tier.
- `404 ... no longer available to new users` for the judge: set `EVAL_JUDGE_MODEL` to a model your key can use.
- `golden_trajectory_v1` failures: compare the printed actual calls with the golden; if behavior changed on purpose, refresh and re-review.
