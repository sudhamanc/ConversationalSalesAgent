"""Eval suite configuration.

Live evals (marked ``eval``) call Gemini and are skipped unless ``RUN_EVALS=1``.
``test_golden_valid.py`` is not marked and always runs (offline, no API key).

For live runs the repo-root ``.env`` is loaded (without overriding the shell),
then ``DATABASE_URL`` is replaced by ``EVAL_DATABASE_URL`` so agents never write
to the development database. ``scripts/eval.sh`` sets these and resets the
eval database first.
"""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))  # `evals.*` imports and the custom metric path

RUN_EVALS = os.getenv("RUN_EVALS") == "1"
DEFAULT_EVAL_DATABASE_URL = "postgresql://csa:csa@localhost:5432/csa_eval"

if RUN_EVALS:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env", override=False)
    os.environ["DATABASE_URL"] = os.getenv("EVAL_DATABASE_URL", DEFAULT_EVAL_DATABASE_URL)
    os.environ.setdefault("CATALOG_MCP_URL", "http://127.0.0.1:8101/mcp/")
    os.environ.setdefault("SERVICEABILITY_MCP_URL", "http://127.0.0.1:8102/mcp/")
    os.environ.setdefault("PUBLIC_URL", "http://localhost:0")


def pytest_configure(config):
    config.addinivalue_line("markers", "eval: live eval against Gemini (needs RUN_EVALS=1)")


def pytest_collection_modifyitems(config, items):
    if RUN_EVALS:
        return
    skip = pytest.mark.skip(reason="live eval: set RUN_EVALS=1 (or use scripts/eval.sh)")
    for item in items:
        if "eval" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def results_dir() -> Path:
    """Per-run output directory (EVAL_RESULTS_DIR from eval.sh, else evals/results/adhoc)."""
    path = Path(os.getenv("EVAL_RESULTS_DIR", REPO_ROOT / "evals" / "results" / "adhoc"))
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def num_runs() -> int:
    return int(os.getenv("EVAL_RUNS", "2"))
