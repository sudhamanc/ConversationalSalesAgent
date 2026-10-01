"""Loading and saving golden datasets (ADK EvalSet JSON) and their manifest.

Layout (all paths relative to ``evals/golden/``)::

    agents/<agent>/<agent>.evalset.json   + agents/<agent>/test_config.json
    router/router.evalset.json            + router/test_config.json
    journeys/<scenario>.evalset.json      + journeys/test_config.json
    MANIFEST.json                         review status per case, seed hashes
    tool_schemas.json                     snapshot of every agent's tool parameters

A set id is the evalset path without the suffix, e.g. ``agents/discovery_agent``.
A case key is ``<set id>/<eval_id>``. EvalSet models forbid extra fields, so
everything that is not ADK data (review status, scenario id, router alternatives,
journey expectations) lives in the manifest under that key.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator, Optional

from google.adk.evaluation.eval_config import EvalConfig
from google.adk.evaluation.eval_set import EvalSet

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
GOLDEN_DIR = EVALS_DIR / "golden"
MANIFEST_PATH = GOLDEN_DIR / "MANIFEST.json"
TOOL_SCHEMAS_PATH = GOLDEN_DIR / "tool_schemas.json"
SEED_DIR = REPO_ROOT / "db" / "seed"
EVALSET_SUFFIX = ".evalset.json"

#: Agent name -> importable package (the module AgentEvaluator loads root_agent from).
AGENT_PACKAGES: dict[str, str] = {
    "greeting_agent": "greeting_agent",
    "faq_agent": "faq_agent",
    "discovery_agent": "discovery_agent",
    "serviceability_agent": "serviceability_agent",
    "product_agent": "product_agent",
    "offer_management_agent": "offer_management",
    "order_agent": "order_agent",
    "payment_agent": "payment_agent",
    "service_fulfillment_agent": "service_fulfillment_agent",
    "customer_communication_agent": "customer_communication_agent",
}


# ---------------------------------------------------------------------------
# Eval sets
# ---------------------------------------------------------------------------


def set_id_for(path: Path) -> str:
    rel = path.resolve().relative_to(GOLDEN_DIR)
    return str(rel)[: -len(EVALSET_SUFFIX)] if str(rel).endswith(EVALSET_SUFFIX) else str(rel)


def path_for(set_id: str) -> Path:
    return GOLDEN_DIR / f"{set_id}{EVALSET_SUFFIX}"


def iter_set_paths(tier: Optional[str] = None) -> Iterator[Path]:
    """All evalset files, optionally limited to one tier (agents/router/journeys)."""
    root = GOLDEN_DIR / tier if tier else GOLDEN_DIR
    yield from sorted(root.rglob(f"*{EVALSET_SUFFIX}"))


def load_set(path: Path) -> EvalSet:
    return EvalSet.model_validate_json(path.read_text())


def save_set(eval_set: EvalSet, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = eval_set.model_dump(mode="json", by_alias=True, exclude_none=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_config(set_path: Path, judge_model: Optional[str] = None, judge_samples: Optional[int] = None) -> EvalConfig:
    """test_config.json next to the evalset (same convention as `adk eval`).

    ``judge_model`` / ``judge_samples`` (EVAL_JUDGE_MODEL / EVAL_JUDGE_SAMPLES) override
    every judge's ``judge_model`` / ``num_samples`` in the file.
    """
    raw = json.loads((set_path.parent / "test_config.json").read_text())
    for criterion in raw.get("criteria", {}).values():
        if isinstance(criterion, dict) and "judge_model_options" in criterion:
            if judge_model:
                criterion["judge_model_options"]["judge_model"] = judge_model
            if judge_samples:
                criterion["judge_model_options"]["num_samples"] = judge_samples
    return EvalConfig.model_validate(raw)


def judge_overrides() -> dict[str, Any]:
    """load_config keyword overrides from the environment."""
    import os

    samples = os.getenv("EVAL_JUDGE_SAMPLES")
    return {"judge_model": os.getenv("EVAL_JUDGE_MODEL"), "judge_samples": int(samples) if samples else None}


def agent_set_path(agent_name: str) -> Path:
    return GOLDEN_DIR / "agents" / agent_name / f"{agent_name}{EVALSET_SUFFIX}"


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"version": 1, "seed_hashes": {}, "cases": {}}
    return json.loads(MANIFEST_PATH.read_text())


def save_manifest(manifest: dict[str, Any]) -> None:
    manifest["cases"] = dict(sorted(manifest.get("cases", {}).items()))
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


def case_key(set_id: str, eval_id: str) -> str:
    return f"{set_id}/{eval_id}"


def case_meta(manifest: dict[str, Any], set_id: str, eval_id: str) -> dict[str, Any]:
    return manifest.get("cases", {}).get(case_key(set_id, eval_id), {})


def reviewed_only(eval_set: EvalSet, manifest: dict[str, Any]) -> tuple[EvalSet, list[str]]:
    """Return (set with reviewed cases only, eval ids pending review).

    ``EVAL_INCLUDE_DRAFTS=1`` also keeps unreviewed cases that have reference responses.
    That is only for debugging the suite itself: scores against drafts are not golden
    results, and scripts/eval.sh never sets it.
    """
    import os

    include_drafts = os.getenv("EVAL_INCLUDE_DRAFTS") == "1"
    keep, pending = [], []
    for case in eval_set.eval_cases:
        meta = case_meta(manifest, eval_set.eval_set_id, case.eval_id)
        recorded = all(
            "".join(p.text or "" for p in (inv.final_response.parts if inv.final_response else []) or []).strip()
            for inv in case.conversation or []
        )
        if meta.get("reviewed") or (include_drafts and recorded):
            keep.append(case)
        else:
            pending.append(case.eval_id)
    return eval_set.model_copy(update={"eval_cases": keep}), pending


# ---------------------------------------------------------------------------
# Seed data fingerprint
# ---------------------------------------------------------------------------


def seed_hashes() -> dict[str, str]:
    """SHA-256 of every seed file; goldens reference seed ids, so a change needs review."""
    return {
        str(p.relative_to(REPO_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(SEED_DIR.glob("*.sql"))
    }


def load_tool_schemas() -> dict[str, dict[str, dict[str, Any]]]:
    """{agent: {tool: {param: {"type": str, "required": bool}}}} snapshot."""
    return json.loads(TOOL_SCHEMAS_PATH.read_text())
