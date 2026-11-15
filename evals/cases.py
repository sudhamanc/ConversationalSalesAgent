"""Uniform per-case results: ``<run dir>/cases.jsonl`` (one JSON object per scored case).

Every tier appends here (agents from the ADK eval CSV, router and journeys
directly). ``python -m evals.langfuse_sync`` reads it, so this module uses the
standard library only (the sync runs in an isolated environment without ADK).

Record fields: ``key`` (MANIFEST case key), ``tier`` (agents | router |
journeys), ``set`` (agent name, ``router`` or ``journeys``), ``input``,
``expected``, ``actual``, ``metrics`` (list of ``{name, score, threshold,
passed}``), ``passed``, ``session_id`` (when known) and ``trace_ids``
(journeys: per-turn ``done.trace_id``).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Optional

CASES_FILE = "cases.jsonl"


def metric(name: str, score: Optional[float], threshold: Optional[float] = None, passed: Optional[bool] = None) -> dict:
    return {"name": name, "score": score, "threshold": threshold, "passed": passed}


def case_record(
    *,
    key: str,
    tier: str,
    set_name: str,
    input: Any,
    expected: Any,
    actual: Any,
    metrics: list[dict],
    passed: bool,
    session_id: Optional[str] = None,
    trace_ids: Optional[list[str]] = None,
) -> dict:
    return {
        "key": key,
        "tier": tier,
        "set": set_name,
        "input": input,
        "expected": expected,
        "actual": actual,
        "metrics": metrics,
        "passed": bool(passed),
        "session_id": session_id,
        "trace_ids": [t for t in (trace_ids or []) if t],
    }


def append_cases(results_dir: Path, records: Iterable[dict]) -> int:
    """Append records to ``results_dir/cases.jsonl``; returns how many were written."""
    path = Path(results_dir) / CASES_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_cases(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _float(value: Any) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def cases_from_agent_csv(csv_path: Path, agent: str) -> list[dict]:
    """Group the ADK ``AgentEvaluator`` output CSV (one row per case and metric) into case records.

    Columns: eval_set_id, eval_id, metric_name, threshold, score, eval_status,
    prompt, expected_response, actual_response, expected_tool_calls, actual_tool_calls.
    """
    by_case: dict[str, dict] = {}
    with Path(csv_path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = f"{row['eval_set_id']}/{row['eval_id']}"
            record = by_case.setdefault(
                key,
                case_record(
                    key=key,
                    tier="agents",
                    set_name=agent,
                    input=row.get("prompt", ""),
                    expected={"response": row.get("expected_response", ""), "tool_calls": row.get("expected_tool_calls", "")},
                    actual={"response": row.get("actual_response", ""), "tool_calls": row.get("actual_tool_calls", "")},
                    metrics=[],
                    passed=True,
                ),
            )
            status = (row.get("eval_status") or "").upper()
            record["metrics"].append(
                metric(row["metric_name"], _float(row.get("score")), _float(row.get("threshold")), status == "PASSED")
            )
            if status != "PASSED":
                record["passed"] = False
    return list(by_case.values())
