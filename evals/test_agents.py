"""Tier 1: each agent against its golden set, in-process, with ADK's AgentEvaluator.

Trajectory: ``golden_trajectory_v1`` (evals/metrics.py). Response:
``final_response_match_v2``, ``rubric_based_final_response_quality_v1`` and, for
agents with tools, ``hallucinations_v1``. Criteria per agent live in
``evals/golden/agents/<agent>/test_config.json``. Only reviewed cases run.

Run through scripts/eval.sh (resets the eval database first), or directly:
``RUN_EVALS=1 venv/bin/python -m pytest evals/test_agents.py -k discovery``.
"""

from __future__ import annotations

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

from evals.golden_io import AGENT_PACKAGES, agent_set_path, judge_overrides, load_config, load_manifest, load_set, reviewed_only

pytestmark = [pytest.mark.eval, pytest.mark.asyncio]


@pytest.mark.parametrize("agent", sorted(AGENT_PACKAGES))
async def test_agent_golden_set(agent, results_dir):
    path = agent_set_path(agent)
    eval_set, pending = reviewed_only(load_set(path), load_manifest())
    if pending:
        print(f"\n{agent}: {len(pending)} case(s) pending review, not run: {', '.join(pending)}")
    if not eval_set.eval_cases:
        pytest.skip(f"{agent}: no reviewed golden cases ({len(pending)} pending review)")

    await AgentEvaluator.evaluate_eval_set(
        agent_module=AGENT_PACKAGES[agent],
        eval_set=eval_set,
        eval_config=load_config(path, **judge_overrides()),
        num_runs=1,  # repetitions are separate eval.sh runs, each on a freshly reset database
        print_detailed_results=True,
        output_file=str(results_dir / f"agent-{agent}.csv"),
    )
