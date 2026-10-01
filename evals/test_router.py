"""Tier 2: the gateway router (``route_intent``) against its golden set.

Each golden case is the JSON routing input ``prepare_turn`` builds plus the
golden ``RouteDecision``. Scored per case:

* trajectory: the chosen ``target`` equals the golden target (or is in the
  manifest's ``allowed_targets``);
* response: the output parses as ``RouteDecision`` and the model finished with
  ``STOP`` (a ``MAX_TOKENS`` finish fails the run; that was the Gemini 3
  thinking-budget bug).

Thresholds: ``evals/golden/router/router_config.json`` (overall accuracy, and
accuracy on cases tagged with an explicit ROUTER_INSTRUCTION rule).
"""

from __future__ import annotations

import json
from collections import Counter

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from evals.golden_io import GOLDEN_DIR, case_key, load_manifest, load_set, reviewed_only

pytestmark = [pytest.mark.eval, pytest.mark.asyncio]

ROUTER_SET = GOLDEN_DIR / "router" / "router.evalset.json"
CONFIG = json.loads((GOLDEN_DIR / "router" / "router_config.json").read_text())


def standalone_router(router):
    """The workflow runs route_intent with mode="single_turn", which ADK rejects as a root
    agent. Eval it as an identical copy (same model, instruction, output schema,
    generate config, include_contents) with mode="chat" and a single user message."""
    return router.model_copy(update={"mode": "chat"})


async def _route(router, routing_input_text: str) -> tuple[str, str]:
    """Return (raw output text, finish reason) for one routing input."""
    service = InMemorySessionService()
    runner = Runner(agent=router, app_name="csa_eval_router", session_service=service)
    session = await service.create_session(app_name="csa_eval_router", user_id="eval_user")
    text, finish = "", ""
    message = types.Content(role="user", parts=[types.Part(text=routing_input_text)])
    async for event in runner.run_async(user_id="eval_user", session_id=session.id, new_message=message):
        if event.finish_reason:
            finish = str(getattr(event.finish_reason, "name", event.finish_reason))
        for part in (event.content.parts if event.content else []) or []:
            if part.text and not part.thought:
                text += part.text
    return text, finish


async def test_router_golden_set(results_dir):
    from sales_common.config import model_name
    from super_agent.workflow import RouteDecision, build_router

    manifest = load_manifest()
    eval_set, pending = reviewed_only(load_set(ROUTER_SET), manifest)
    if pending:
        print(f"\nrouter: {len(pending)} case(s) pending review, not run")
    if not eval_set.eval_cases:
        pytest.skip(f"router: no reviewed golden cases ({len(pending)} pending review)")

    router = standalone_router(build_router(model_name()))
    rows, confusion = [], Counter()
    for case in eval_set.eval_cases:
        meta = manifest["cases"][case_key(eval_set.eval_set_id, case.eval_id)]
        (invocation,) = case.conversation
        routing_input = "".join(p.text or "" for p in invocation.user_content.parts)
        raw, finish = await _route(router, routing_input)
        try:
            chosen = RouteDecision.model_validate_json(raw).target
            schema_ok = True
        except ValueError:
            chosen, schema_ok = None, False
        accepted = {meta["target"], *meta.get("allowed_targets", [])}
        rows.append({
            "eval_id": case.eval_id,
            "rule": meta.get("rule"),
            "expected": meta["target"],
            "allowed": sorted(accepted),
            "chosen": chosen,
            "trajectory_ok": chosen in accepted,
            "response_ok": schema_ok and finish == "STOP",
            "finish_reason": finish,
            "raw": raw[:300],
        })
        confusion[(meta["target"], chosen)] += 1

    (results_dir / "router.json").write_text(json.dumps(rows, indent=2))
    total = len(rows)
    accuracy = sum(r["trajectory_ok"] for r in rows) / total
    rule_rows = [r for r in rows if r["rule"]]
    rule_accuracy = sum(r["trajectory_ok"] for r in rule_rows) / len(rule_rows) if rule_rows else 1.0
    truncated = [r["eval_id"] for r in rows if r["finish_reason"] == "MAX_TOKENS"]
    bad_schema = [r["eval_id"] for r in rows if not r["response_ok"]]

    print(f"\nrouter: accuracy {accuracy:.1%} ({total} cases), rule cases {rule_accuracy:.1%}")
    for r in rows:
        if not (r["trajectory_ok"] and r["response_ok"]):
            print(f"  FAIL {r['eval_id']}: expected {r['allowed']} got {r['chosen']} finish={r['finish_reason']}")
    print("  confusion (expected -> chosen: count):")
    for (expected, chosen), count in sorted(confusion.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        if expected != chosen:
            print(f"    {expected} -> {chosen}: {count}")

    assert not truncated, f"router output hit MAX_TOKENS (truncated JSON): {truncated}"
    assert not bad_schema, f"router output not a valid RouteDecision with finish STOP: {bad_schema}"
    assert accuracy >= CONFIG["accuracy_threshold"], f"router accuracy {accuracy:.1%} < {CONFIG['accuracy_threshold']:.0%}"
    assert rule_accuracy >= CONFIG["rule_accuracy_threshold"], (
        f"router accuracy on explicit-rule cases {rule_accuracy:.1%} < {CONFIG['rule_accuracy_threshold']:.0%}"
    )
