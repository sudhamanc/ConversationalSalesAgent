"""Tier 3: end-to-end journeys through the running gateway (HTTP/SSE, A2A, MCP, PostgreSQL).

For each golden journey:

1. Create a session (``POST /api/session``) and send every golden user turn
   (``POST /api/chat``), keeping the streamed text, answering agents and events.
2. Read ``{session_id, user_id}`` from ``GET /api/debug/session`` (the eval stack
   runs with ``DEBUG=true``) and load the gateway session from the eval database
   with ADK's ``DatabaseSessionService``. Remote agents' tool calls are in it.
3. Build one actual ``Invocation`` per turn: tool calls from the session events,
   the streamed text as the final response.
4. Score per turn against the golden:
   * trajectory: answering agents == golden ``turn_agents``; tool calls with
     ``golden_trajectory_v1``; required ``turn_events`` present; no ``error`` event;
   * response: the ADK metrics in ``evals/golden/journeys/test_config.json``.

``EVAL_RECORD=1`` writes the streamed replies into the goldens as drafts
(``reviewed: false``) instead of scoring. Needs the stack started by
``scripts/eval.sh --only journeys`` (or ``EVAL_GATEWAY_URL``).
"""

from __future__ import annotations

import inspect
import json
import os
import sys
import uuid

import pytest
from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_config import get_eval_metrics_from_config
from google.adk.evaluation.eval_metrics import EvalStatus
from google.genai import types

from evals.golden_io import (
    AGENT_PACKAGES,
    REPO_ROOT,
    case_key,
    iter_set_paths,
    judge_overrides,
    load_config,
    load_manifest,
    load_set,
    reviewed_only,
    save_manifest,
    save_set,
    set_id_for,
)
from evals.trace import events_to_turns

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from e2e_client import post_json, run_turn  # noqa: E402

pytestmark = [pytest.mark.eval, pytest.mark.asyncio]

GATEWAY_URL = os.getenv("EVAL_GATEWAY_URL", "http://127.0.0.1:8000").rstrip("/")
TURN_TIMEOUT = float(os.getenv("EVAL_TURN_TIMEOUT", "180"))
RECORD = os.getenv("EVAL_RECORD") == "1"
JOURNEY_PATHS = list(iter_set_paths("journeys"))


def _get_json(url: str, token: str) -> dict:
    import urllib.request

    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


async def _session_tool_calls(token: str, messages: list[str]) -> list[IntermediateData]:
    """Tool calls/responses per user turn, from the gateway session in the eval database."""
    from google.adk.sessions import DatabaseSessionService
    from sales_common.db import session_db_url
    from super_agent.config import settings

    ids = _get_json(f"{GATEWAY_URL}/api/debug/session", token)
    service = DatabaseSessionService(db_url=session_db_url())
    session = await service.get_session(
        app_name=settings.agent.app_name, user_id=ids["user_id"], session_id=ids["session_id"]
    )
    turns = events_to_turns(
        session.events if session else [], allowed_authors=set(AGENT_PACKAGES), user_messages=messages
    )
    data = [t.invocation.intermediate_data for t in turns]
    return (data + [IntermediateData()] * len(messages))[: len(messages)]


def _event_names(sse_turn) -> set[str]:
    names = set()
    for event in sse_turn.events:
        if event.get("type") == "structured_card":
            names.add(f"structured_card:{event.get('card_type')}")
        elif event.get("type") == "cart_update":
            names.add("cart_update")
    return names


async def _score_response_metrics(config, actual: list[Invocation], expected: list[Invocation]) -> dict:
    from google.adk.evaluation.metric_evaluator_registry import (
        DEFAULT_METRIC_EVALUATOR_REGISTRY,
        register_custom_metrics_from_config,
    )

    registry = register_custom_metrics_from_config(config, DEFAULT_METRIC_EVALUATOR_REGISTRY.fork())
    for act, exp in zip(actual, expected):  # case rubrics travel with the actual invocation
        act.rubrics = exp.rubrics
    results = {}
    for metric in get_eval_metrics_from_config(config):
        evaluator = registry.get_evaluator(metric)
        result = evaluator.evaluate_invocations(actual, expected)
        if inspect.isawaitable(result):
            result = await result
        results[metric.metric_name] = result
    return results


@pytest.mark.parametrize("path", JOURNEY_PATHS, ids=lambda p: set_id_for(p))
async def test_journey(path, results_dir):
    manifest = load_manifest()
    full_set = load_set(path)
    eval_set, pending = (full_set, []) if RECORD else reviewed_only(full_set, manifest)
    if not eval_set.eval_cases:
        pytest.skip(f"{set_id_for(path)}: no reviewed golden cases ({len(pending)} pending review)")
    config = load_config(path, **judge_overrides())
    report = []
    failures = []

    for case in eval_set.eval_cases:
        meta = manifest["cases"][case_key(eval_set.eval_set_id, case.eval_id)]
        golden_turns = case.conversation or []
        session = post_json(f"{GATEWAY_URL}/api/session", {"client_id": f"eval-{uuid.uuid4()}"}, {}, 30.0)
        token = session["token"]

        messages = ["".join(p.text or "" for p in golden.user_content.parts) for golden in golden_turns]
        sse_turns = [run_turn(GATEWAY_URL, token, message, TURN_TIMEOUT) for message in messages]
        tool_data = await _session_tool_calls(token, messages)

        actual = [
            Invocation(
                invocation_id=golden.invocation_id,
                user_content=golden.user_content,
                final_response=types.Content(role="model", parts=[types.Part(text=sse.text)]),
                intermediate_data=data,
            )
            for golden, sse, data in zip(golden_turns, sse_turns, tool_data)
        ]

        if RECORD:
            for golden, act in zip(golden_turns, actual):
                golden.final_response = act.final_response
            meta.update({"reviewed": False, "reviewed_by": None, "reviewed_at": None})
            for i, (sse, data) in enumerate(zip(sse_turns, tool_data)):
                calls = [f"{c.name}({json.dumps(c.args, sort_keys=True)})" for c in data.tool_uses]
                print(f"\n{case.eval_id} turn {i + 1}: agents={sse.authors} events={sorted(_event_names(sse))}"
                      f"\n  tools={calls}\n  reply={sse.text[:200]!r}")
            continue

        # Trajectory: agents, tool calls, events, errors (per turn)
        from evals.metrics import trajectory_score

        for i, (golden, sse, data) in enumerate(zip(golden_turns, sse_turns, tool_data)):
            expected_calls = [(c.name, dict(c.args or {})) for c in golden.intermediate_data.tool_uses]
            actual_calls = [(c.name, dict(c.args or {})) for c in data.tool_uses]
            row = {
                "case": case.eval_id,
                "turn": i + 1,
                "agents_expected": meta["turn_agents"][i],
                "agents_actual": sse.authors,
                "tool_score": trajectory_score(expected_calls, actual_calls),
                "events_missing": sorted(set(meta["turn_events"][i]) - _event_names(sse)),
                "errors": sse.errors,
            }
            report.append(row)
            where = f"{case.eval_id} turn {i + 1}"
            if row["agents_actual"] != row["agents_expected"]:
                failures.append(f"{where}: agents {row['agents_actual']} != golden {row['agents_expected']}")
            threshold = config.criteria["golden_trajectory_v1"]
            threshold = threshold if isinstance(threshold, (int, float)) else threshold.threshold
            if row["tool_score"] < threshold:
                failures.append(f"{where}: tool trajectory {row['tool_score']:.2f} < {threshold} (actual {actual_calls})")
            if row["events_missing"]:
                failures.append(f"{where}: missing events {row['events_missing']}")
            if row["errors"]:
                failures.append(f"{where}: error events {row['errors']}")

        # Response: ADK metrics per turn against the golden reply
        skip = {"golden_trajectory_v1", *meta.get("skip_metrics", [])}
        results = await _score_response_metrics(
            config.model_copy(update={"criteria": {k: v for k, v in config.criteria.items() if k not in skip}}),
            actual,
            golden_turns,
        )
        for name, result in results.items():
            report.append({"case": case.eval_id, "metric": name, "score": result.overall_score,
                           "status": result.overall_eval_status.name})
            if result.overall_eval_status == EvalStatus.FAILED:
                failures.append(f"{case.eval_id}: {name} score {result.overall_score} below threshold")

    if RECORD:
        save_set(full_set, path)
        save_manifest(manifest)
        pytest.skip(f"recorded drafts into {path.name}; review them before running scored evals")

    (results_dir / f"journey-{path.name.replace('.evalset.json', '')}.json").write_text(
        json.dumps(report, indent=2, default=str)
    )
    assert not failures, "\n".join(failures)
