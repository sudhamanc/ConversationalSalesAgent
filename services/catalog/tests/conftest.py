import os
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("GEMINI_MODEL", "gemini-test")  # construction only; never called
os.environ.setdefault("RAG_BUILD_ON_START", "false")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session")
def seeded_db():
    """Scratch PostgreSQL database with migrations + seeds applied."""
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not set")
    from sales_common import migrate

    migrate.run(seed=True, db_dir=REPO_ROOT / "db")
    return os.environ["DATABASE_URL"]


@pytest.fixture
def no_rag():
    """Force the knowledge index into the 'unavailable' state for one test."""
    from catalog_service import rag

    rag.set_index(None, "disabled for test")
    yield
    rag.set_index(None, None)
