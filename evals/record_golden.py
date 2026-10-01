"""Record draft goldens from the real model, and snapshot tool schemas.

Goldens are reviewed data: this script only writes *drafts* and marks every case
it touches ``reviewed: false`` in MANIFEST.json. A reviewer then checks the
trajectory and reference response, edits them if needed, and sets
``reviewed: true`` / ``reviewed_by`` / ``reviewed_at``.

Usage (from the repo root, with the venv and a billed GOOGLE_API_KEY):

  venv/bin/python -m evals.record_golden --snapshot-tools
      Rewrite evals/golden/tool_schemas.json from the agents' current tools
      (needs catalog :8101 and serviceability :8102 for the MCP-backed agents).

  venv/bin/python -m evals.record_golden --set agents/discovery_agent [--case ID ...]
      Fill in reference responses (``final_response``) for cases that have none.
      Hand-authored trajectories are kept.

  venv/bin/python -m evals.record_golden --set agents/discovery_agent --refresh --case ID
      Overwrite both trajectory and response with what the model does now
      (intentional behavior change; review the diff before committing).

  --dry-run lists what would be recorded. Journeys are recorded by
  ``evals/test_journeys.py --record`` because they need the running stack.

Recording runs against DATABASE_URL; use the eval database
(``EVAL_DATABASE_URL``, reset by scripts/eval.sh), never the dev database.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from evals.golden_io import (  # noqa: E402
    AGENT_PACKAGES,
    TOOL_SCHEMAS_PATH,
    case_key,
    load_manifest,
    load_set,
    path_for,
    save_manifest,
    save_set,
    seed_hashes,
)


def _env() -> None:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env", override=False)
    if os.getenv("EVAL_DATABASE_URL"):
        os.environ["DATABASE_URL"] = os.environ["EVAL_DATABASE_URL"]
    os.environ.setdefault("CATALOG_MCP_URL", "http://127.0.0.1:8101/mcp/")
    os.environ.setdefault("SERVICEABILITY_MCP_URL", "http://127.0.0.1:8102/mcp/")
    os.environ.setdefault("PUBLIC_URL", "http://localhost:0")


# ---------------------------------------------------------------------------
# Tool schema snapshot
# ---------------------------------------------------------------------------


async def snapshot_tools() -> dict[str, Any]:
    import importlib

    from google.adk.tools import FunctionTool

    out: dict[str, Any] = {}
    for agent_name, package in AGENT_PACKAGES.items():
        agent = importlib.import_module(package).root_agent
        tools = []
        for tool in agent.tools:
            if hasattr(tool, "get_tools"):  # McpToolset
                tools.extend(await tool.get_tools())
            elif callable(tool) and not hasattr(tool, "name"):
                tools.append(FunctionTool(tool))
            else:
                tools.append(tool)
        schemas: dict[str, Any] = {}
        for tool in tools:
            declaration = tool._get_declaration()
            schema = {}
            if declaration is not None:
                schema = declaration.parameters_json_schema or (
                    declaration.parameters.model_dump(mode="json", exclude_none=True) if declaration.parameters else {}
                )
            required = set((schema or {}).get("required", []))
            schemas[tool.name] = {
                name: {"required": name in required} for name in (schema or {}).get("properties", {})
            }
        out[agent_name] = dict(sorted(schemas.items()))
    return out


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


def _tier_and_agent(set_id: str) -> tuple[str, str]:
    tier, _, rest = set_id.partition("/")
    return tier, rest.split("/")[0]


async def record(set_id: str, case_ids: list[str], refresh: bool, dry_run: bool) -> int:
    from google.adk.evaluation.eval_case import IntermediateData

    from evals.agent_runner import run_agent_case, run_router_case

    tier, agent_name = _tier_and_agent(set_id)
    if tier not in {"agents", "router"}:
        print(f"{set_id}: only agents/* and router sets are recorded here", file=sys.stderr)
        return 2
    path = path_for(set_id)
    eval_set = load_set(path)
    manifest = load_manifest()
    selected = [c for c in eval_set.eval_cases if not case_ids or c.eval_id in case_ids]
    todo = [
        c for c in selected
        if refresh or any(not "".join(p.text or "" for p in (inv.final_response.parts if inv.final_response else []) or []).strip()
                          for inv in c.conversation or [])
    ]
    for case in todo:
        print(f"{'would record' if dry_run else 'recording'} {case_key(set_id, case.eval_id)}")
    if dry_run:
        return 0

    updated = []
    for case in todo:
        try:
            if tier == "router":
                turns = await run_router_case(case)
            else:
                turns = await run_agent_case(agent_name, case)
        except Exception as exc:  # quota, billing, network: keep what was recorded so far
            print(f"  stopped at {case.eval_id}: {type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)
            break
        for golden, turn in zip(case.conversation or [], turns):
            golden.final_response = turn.invocation.final_response
            if refresh:
                golden.intermediate_data = IntermediateData(
                    tool_uses=turn.invocation.intermediate_data.tool_uses
                )
            calls = [f"{c.name}({json.dumps(c.args, sort_keys=True)})" for c in turn.invocation.intermediate_data.tool_uses]
            print(f"  turn: tools={calls}")
            print(f"        reply={(golden.final_response.parts[0].text or '')[:160]!r}")
        meta = manifest.setdefault("cases", {}).setdefault(case_key(set_id, case.eval_id), {})
        meta.update({"reviewed": False, "reviewed_by": None, "reviewed_at": None})
        updated.append(case.eval_id)
        save_set(eval_set, path)  # after every case, so an interrupted run keeps its progress
        manifest["seed_hashes"] = seed_hashes()
        save_manifest(manifest)
    print(f"\nRecorded {len(updated)} of {len(todo)} draft case(s) in {path.relative_to(REPO_ROOT)}; all marked reviewed=false.")
    print("Review each trajectory (drop arguments that change per run, e.g. new ids/dates)")
    print("and reference reply, then approve: python -m evals.review --approve <key> --by <name>.")
    return 0 if len(updated) == len(todo) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--snapshot-tools", action="store_true")
    parser.add_argument("--set", dest="set_id")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _env()
    if args.snapshot_tools:
        schemas = asyncio.run(snapshot_tools())
        TOOL_SCHEMAS_PATH.write_text(json.dumps(schemas, indent=2) + "\n")
        print(f"Wrote {TOOL_SCHEMAS_PATH.relative_to(REPO_ROOT)} ({sum(map(len, schemas.values()))} tools)")
        return 0
    if not args.set_id:
        parser.error("--set or --snapshot-tools is required")
    return asyncio.run(record(args.set_id, args.case, args.refresh, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
