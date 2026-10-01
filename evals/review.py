"""Review golden cases: list, inspect and approve.

  venv/bin/python -m evals.review --list [--pending] [--set agents/discovery_agent/discovery_agent]
  venv/bin/python -m evals.review --show agents/discovery_agent/discovery_agent/existing-company-found
  venv/bin/python -m evals.review --approve KEY [KEY ...] --by "Your Name"
  venv/bin/python -m evals.review --approve-set router/router --by "Your Name"

Approving sets ``reviewed: true``, ``reviewed_by`` and ``reviewed_at`` in
MANIFEST.json, and refuses cases whose turns have no reference response yet
(record them first with evals.record_golden or EVAL_RECORD=1 for journeys).
Approve only after checking the trajectory (tools, stable arguments, agents)
and the reference reply against the scenario.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.golden_io import case_key, iter_set_paths, load_manifest, load_set, save_manifest, seed_hashes  # noqa: E402


def _cases():
    for path in iter_set_paths():
        eval_set = load_set(path)
        for case in eval_set.eval_cases:
            yield case_key(eval_set.eval_set_id, case.eval_id), eval_set.eval_set_id, case


def _text(content) -> str:
    return "".join(p.text or "" for p in (content.parts or [])) if content else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--pending", action="store_true")
    parser.add_argument("--set", dest="set_id")
    parser.add_argument("--show")
    parser.add_argument("--approve", nargs="+", default=[])
    parser.add_argument("--approve-set")
    parser.add_argument("--by")
    args = parser.parse_args()
    manifest = load_manifest()
    cases = {key: (set_id, case) for key, set_id, case in _cases()}

    if args.list:
        for key, (set_id, _) in cases.items():
            meta = manifest["cases"].get(key, {})
            if args.set_id and set_id != args.set_id:
                continue
            if args.pending and meta.get("reviewed"):
                continue
            status = f"reviewed by {meta.get('reviewed_by')} {meta.get('reviewed_at')}" if meta.get("reviewed") else "PENDING"
            print(f"{key:<80} {meta.get('scenario_id') or '':<12} {status}")
        return 0

    if args.show:
        set_id, case = cases[args.show]
        print(json.dumps(manifest["cases"].get(args.show, {}), indent=2))
        if case.session_input and case.session_input.state:
            print("session state:", json.dumps(case.session_input.state)[:400])
        for i, inv in enumerate(case.conversation or []):
            print(f"\n--- turn {i + 1}\nuser: {_text(inv.user_content)}")
            for call in (inv.intermediate_data.tool_uses if inv.intermediate_data else []):
                print(f"tool: {call.name}({json.dumps(call.args, sort_keys=True)})")
            for rubric in inv.rubrics or []:
                print(f"rubric: {rubric.rubric_content.text_property}")
            print(f"reference reply: {_text(inv.final_response) or '(not recorded yet)'}")
        return 0

    keys = list(args.approve)
    if args.approve_set:
        keys += [k for k, (set_id, _) in cases.items() if set_id == args.approve_set]
    if keys:
        if not args.by:
            parser.error("--by is required when approving")
        today = dt.date.today().isoformat()
        for key in keys:
            if key not in cases:
                print(f"unknown case {key}", file=sys.stderr)
                return 2
            _, case = cases[key]
            missing = [i + 1 for i, inv in enumerate(case.conversation or []) if not _text(inv.final_response).strip()]
            if missing:
                print(f"{key}: no reference response for turn(s) {missing}; record first", file=sys.stderr)
                return 1
            manifest["cases"].setdefault(key, {}).update({"reviewed": True, "reviewed_by": args.by, "reviewed_at": today})
            print(f"approved {key}")
        manifest["seed_hashes"] = seed_hashes()
        save_manifest(manifest)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
