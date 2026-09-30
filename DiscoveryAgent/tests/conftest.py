import os
from pathlib import Path

os.environ.setdefault("GEMINI_MODEL", "gemini-test")      # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def seeded_db():
    """Migrate + seed the scratch database once per session (skipped without TEST_DATABASE_URL)."""
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not set")
    from sales_common import db, migrate

    migrate.run(seed=True, db_dir=REPO_ROOT / "db")
    yield db
    db.close_pool()
