"""Offline validation of the golden datasets (no LLM, no database, no API key).

Runs in every normal pytest invocation. Live evals assume what is checked here.
"""

from __future__ import annotations

import importlib
import json

import pytest

from evals.golden_io import (
    AGENT_PACKAGES,
    GOLDEN_DIR,
    case_key,
    iter_set_paths,
    load_config,
    load_manifest,
    load_set,
    load_tool_schemas,
    seed_hashes,
    set_id_for,
)

MANIFEST = load_manifest()
TOOLS = load_tool_schemas()
ALL_TOOLS = {tool: params for agent_tools in TOOLS.values() for tool, params in agent_tools.items()}
ROUTER_INPUT_KEYS = {"message", "last_agent", "last_reply", "journey", "company_name", "memories"}
SET_PATHS = list(iter_set_paths())


def _text(content) -> str:
    return "".join(p.text or "" for p in (content.parts or [])) if content else ""


def _check_calls(where: str, calls, schemas: dict) -> list[str]:
    problems = []
    for call in calls:
        if call.name not in schemas:
            problems.append(f"{where}: unknown tool {call.name!r}")
            continue
        for arg in (call.args or {}):
            if arg not in schemas[call.name]:
                problems.append(f"{where}: {call.name} has no parameter {arg!r}")
    return problems


def test_sets_exist_for_every_tier_and_agent():
    ids = {set_id_for(p) for p in SET_PATHS}
    for agent in AGENT_PACKAGES:
        assert f"agents/{agent}/{agent}" in ids, f"missing golden set for {agent}"
    assert "router/router" in ids
    assert any(i.startswith("journeys/") for i in ids)


def test_tool_snapshot_covers_every_agent():
    assert set(TOOLS) == set(AGENT_PACKAGES), "re-run: python -m evals.record_golden --snapshot-tools"


def test_seed_unchanged_since_review():
    current, recorded = seed_hashes(), MANIFEST.get("seed_hashes", {})
    changed = sorted(f for f in current.keys() | recorded.keys() if current.get(f) != recorded.get(f))
    assert not changed, (
        f"seed files changed since the goldens were reviewed: {changed}. Re-check goldens that "
        "reference seed data, then update seed_hashes in evals/golden/MANIFEST.json."
    )


def test_manifest_matches_cases():
    keys = set()
    for path in SET_PATHS:
        eval_set = load_set(path)
        assert eval_set.eval_set_id == set_id_for(path), f"{path}: eval_set_id must be {set_id_for(path)!r}"
        keys |= {case_key(eval_set.eval_set_id, c.eval_id) for c in eval_set.eval_cases}
    manifest_keys = set(MANIFEST.get("cases", {}))
    assert not keys - manifest_keys, f"cases missing from MANIFEST.json: {sorted(keys - manifest_keys)}"
    assert not manifest_keys - keys, f"MANIFEST.json entries without a case: {sorted(manifest_keys - keys)}"


@pytest.mark.parametrize("path", SET_PATHS, ids=lambda p: set_id_for(p))
def test_reviewed_cases_are_complete(path):
    eval_set = load_set(path)
    problems = []
    for case in eval_set.eval_cases:
        meta = MANIFEST["cases"].get(case_key(eval_set.eval_set_id, case.eval_id), {})
        if not meta.get("reviewed"):
            continue
        if not meta.get("reviewed_by") or not meta.get("reviewed_at"):
            problems.append(f"{case.eval_id}: reviewed cases need reviewed_by and reviewed_at")
        for i, inv in enumerate(case.conversation or []):
            if not _text(inv.final_response).strip():
                problems.append(f"{case.eval_id} turn {i + 1}: reviewed case has no reference response")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("agent", sorted(AGENT_PACKAGES))
def test_agent_goldens_use_real_tools(agent):
    path = GOLDEN_DIR / "agents" / agent / f"{agent}.evalset.json"
    eval_set = load_set(path)
    problems = []
    for case in eval_set.eval_cases:
        for i, inv in enumerate(case.conversation or []):
            calls = inv.intermediate_data.tool_uses if inv.intermediate_data else []
            problems += _check_calls(f"{case.eval_id} turn {i + 1}", calls, TOOLS[agent])
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("path", list(iter_set_paths("journeys")), ids=lambda p: set_id_for(p))
def test_journey_goldens(path):
    eval_set = load_set(path)
    problems = []
    for case in eval_set.eval_cases:
        meta = MANIFEST["cases"][case_key(eval_set.eval_set_id, case.eval_id)]
        turns = case.conversation or []
        if len(meta.get("turn_agents", [])) != len(turns):
            problems.append(f"{case.eval_id}: turn_agents must have one entry per turn")
        for agents in meta.get("turn_agents", []):
            problems += [f"{case.eval_id}: unknown agent {a!r}" for a in agents if a not in AGENT_PACKAGES]
        for events in meta.get("turn_events", []):
            for event in events:
                if event not in {"cart_update"} and not event.startswith("structured_card:"):
                    problems.append(f"{case.eval_id}: unknown expected event {event!r}")
        for i, inv in enumerate(turns):
            calls = inv.intermediate_data.tool_uses if inv.intermediate_data else []
            problems += _check_calls(f"{case.eval_id} turn {i + 1}", calls, ALL_TOOLS)
    assert not problems, "\n".join(problems)


def test_router_goldens():
    eval_set = load_set(GOLDEN_DIR / "router" / "router.evalset.json")
    problems = []
    for case in eval_set.eval_cases:
        meta = MANIFEST["cases"][case_key(eval_set.eval_set_id, case.eval_id)]
        (inv,) = case.conversation
        try:
            routing_input = json.loads(_text(inv.user_content))
        except ValueError:
            problems.append(f"{case.eval_id}: user content must be the JSON routing input")
            continue
        if set(routing_input) != ROUTER_INPUT_KEYS:
            problems.append(f"{case.eval_id}: routing input keys must be {sorted(ROUTER_INPUT_KEYS)}")
        golden = json.loads(_text(inv.final_response))
        if golden.get("target") != meta.get("target"):
            problems.append(f"{case.eval_id}: reference target differs from MANIFEST target")
        for target in [meta.get("target"), *meta.get("allowed_targets", [])]:
            if target not in AGENT_PACKAGES:
                problems.append(f"{case.eval_id}: unknown target {target!r}")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize(
    "path", [p for p in SET_PATHS if not p.parent.name == "router"], ids=lambda p: set_id_for(p)
)
def test_eval_configs_load(path):
    config = load_config(path)
    for name, custom in (config.custom_metrics or {}).items():
        module, _, function = custom.code_config.name.rpartition(".")
        assert callable(getattr(importlib.import_module(module), function)), f"{name}: bad code_config"


def test_skip_metrics_name_real_criteria():
    problems = []
    for path in SET_PATHS:
        if path.parent.name == "router":
            continue
        criteria = set(load_config(path).criteria)
        eval_set = load_set(path)
        for case in eval_set.eval_cases:
            meta = MANIFEST["cases"][case_key(eval_set.eval_set_id, case.eval_id)]
            for metric in meta.get("skip_metrics", []):
                if metric not in criteria or metric == "golden_trajectory_v1":
                    problems.append(f"{case.eval_id}: cannot skip {metric!r}")
            if meta.get("skip_metrics") and not meta.get("skip_reason"):
                problems.append(f"{case.eval_id}: skip_metrics needs a skip_reason")
    assert not problems, "\n".join(problems)
