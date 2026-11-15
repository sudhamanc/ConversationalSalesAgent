"""Push an eval run's ``cases.jsonl`` to Langfuse: datasets, experiment runs and scores.

    python -m evals.langfuse_sync <results dir> [--run-name NAME]

``<results dir>`` is ``evals/results/<timestamp>`` (every ``run-*/cases.jsonl``
becomes its own run, named ``<timestamp>-run-<n>``) or a single run directory.

Per dataset group (``csa-golden-agents-<agent>``, ``csa-golden-router``,
``csa-golden-journeys``):

1. upsert the dataset and one item per case (item id = stable hash of the
   MANIFEST case key; input and expected output from the golden case)
2. ``Langfuse.run_experiment`` over those items. The task **replays** the
   recorded actual output (no model is called); journey cases join their
   gateway session (``propagate_attributes(session_id=...)``) so the result sits
   next to that session's ``chat_turn`` traces. The evaluator returns each
   recorded metric as a NUMERIC score and ``passed`` as a BOOLEAN score.

The SDK links each trace to the dataset run through ``langfuse.experiment.*``
span attributes; experiment traces use Langfuse's environment ``sdk-experiment``.

This module needs only the standard library and ``langfuse`` 5.x. It runs in an
isolated environment (``scripts/eval.sh --langfuse`` uses ``uv run --no-project
--with-requirements evals/requirements-langfuse.txt``) because langfuse 5.x and
google-adk 2.10 need incompatible OpenTelemetry versions.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Iterable

from evals.cases import CASES_FILE, read_cases

DEFAULT_HOST = "https://us.cloud.langfuse.com"


def dataset_name(case: dict) -> str:
    if case["tier"] == "agents":
        return f"csa-golden-agents-{case['set']}"
    return f"csa-golden-{case['tier']}"


def item_id(case_key: str) -> str:
    """Stable, project-unique dataset item id for a MANIFEST case key."""
    return "csa-" + hashlib.sha256(case_key.encode()).hexdigest()[:40]


def discover_runs(path: Path) -> list[tuple[Path, str]]:
    """``(cases.jsonl path, run name)`` pairs under a results or run directory."""
    path = Path(path)
    if (path / CASES_FILE).exists():
        name = f"{path.parent.name}-{path.name}" if path.name.startswith("run-") else path.name
        return [(path / CASES_FILE, name)]
    return [(p, f"{path.name}-{p.parent.name}") for p in sorted(path.glob(f"run-*/{CASES_FILE}"))]


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def evaluations(case: dict, sdk: Any) -> list:
    """Recorded metrics as Langfuse evaluations, plus a boolean ``passed``."""
    out = []
    for m in case.get("metrics") or []:
        if m.get("score") is None:
            continue
        threshold = m.get("threshold")
        out.append(
            sdk.Evaluation(
                name=m["name"],
                value=float(m["score"]),
                comment=None if threshold is None else f"threshold {threshold}",
            )
        )
    out.append(sdk.Evaluation(name="passed", value=1.0 if case.get("passed") else 0.0, data_type="BOOLEAN"))
    return out


def _ensure_dataset(client: Any, name: str, tier: str) -> None:
    try:
        client.get_dataset(name)
    except Exception:  # not found (the SDK raises its NotFoundError)
        client.create_dataset(
            name=name,
            description=f"Golden eval cases ({tier}) from evals/golden; items keyed by MANIFEST case key",
            metadata={"source": "evals/golden", "tier": tier},
        )


def sync_cases(cases: Iterable[dict], run_name: str, *, client: Any, sdk: Any, metadata: dict[str, str]) -> dict[str, int]:
    """Upsert datasets/items for ``cases`` and record them as one experiment run per dataset."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        groups[dataset_name(case)].append(case)

    summary: dict[str, int] = {}
    for name, group in sorted(groups.items()):
        _ensure_dataset(client, name, group[0]["tier"])
        by_item: dict[str, dict] = {}
        for case in group:
            iid = item_id(case["key"])
            client.create_dataset_item(
                dataset_name=name,
                id=iid,
                input=case["input"],
                expected_output=case["expected"],
                metadata={"case_key": case["key"], "tier": case["tier"], "set": case["set"]},
            )
            by_item[iid] = case
        by_key = {case["key"]: case for case in group}
        items = [item for item in client.get_dataset(name).items if item.id in by_item]

        def task(*, item, **_kwargs):
            case = by_item[item.id]
            session_id = case.get("session_id")
            scope = sdk.propagate_attributes(session_id=session_id) if session_id else nullcontext()
            with scope:
                return case["actual"]

        def evaluator(*, input=None, output=None, expected_output=None, metadata=None, **_kwargs):
            return evaluations(by_key[(metadata or {})["case_key"]], sdk)

        client.run_experiment(
            name=name,
            run_name=run_name,
            description=f"Golden eval run {run_name} (recorded results replayed by evals.langfuse_sync)",
            data=items,
            task=task,
            evaluators=[evaluator],
            metadata=metadata,
            max_concurrency=8,
        )
        summary[name] = len(items)
    client.flush()
    return summary


def _sdk():
    """The langfuse SDK pieces the sync uses (imported lazily: not installed in ./venv)."""
    from types import SimpleNamespace

    from langfuse import Evaluation, Langfuse, propagate_attributes

    return SimpleNamespace(Langfuse=Langfuse, Evaluation=Evaluation, propagate_attributes=propagate_attributes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.langfuse_sync", description=__doc__.split("\n\n")[0])
    parser.add_argument("results_dir", type=Path, help="evals/results/<timestamp> or one run-* directory")
    parser.add_argument("--run-name", help="override the run name (single run only)")
    args = parser.parse_args(argv)

    public_key, secret_key = os.getenv("LANGFUSE_PUBLIC_KEY", ""), os.getenv("LANGFUSE_SECRET_KEY", "")
    if not (public_key and secret_key):
        print("langfuse_sync: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set", file=sys.stderr)
        return 2
    runs = discover_runs(args.results_dir)
    if not runs:
        print(f"langfuse_sync: no {CASES_FILE} under {args.results_dir}", file=sys.stderr)
        return 1
    if args.run_name and len(runs) > 1:
        print("langfuse_sync: --run-name needs a single run directory", file=sys.stderr)
        return 2

    sdk = _sdk()
    host = (os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST") or DEFAULT_HOST).rstrip("/")
    client = sdk.Langfuse(public_key=public_key, secret_key=secret_key, base_url=host)
    metadata = {
        "git_commit": git_commit(),
        "gemini_model": os.getenv("GEMINI_MODEL", ""),
        "results_dir": str(args.results_dir),
    }
    for path, run_name in runs:
        summary = sync_cases(read_cases(path), args.run_name or run_name, client=client, sdk=sdk, metadata=metadata)
        for name, count in summary.items():
            print(f"langfuse_sync: {name}: {count} case(s) in run {args.run_name or run_name}")
    client.shutdown()
    print(f"langfuse_sync: done ({host}, Datasets view)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
