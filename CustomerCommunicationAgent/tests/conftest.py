import os
from pathlib import Path

import pytest

os.environ.setdefault("GEMINI_MODEL", "gemini-test")  # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
# Never send real email from tests.
os.environ.pop("SMTP_ENABLED", None)

REPO_ROOT = Path(__file__).resolve().parents[2]


def pytest_configure(config):
    config.addinivalue_line("markers", "pg: requires a PostgreSQL TEST_DATABASE_URL")


def pytest_collection_modifyitems(config, items):
    if os.getenv("TEST_DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set (PostgreSQL integration tests)")
    for item in items:
        if "pg" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def migrated():
    from sales_common import migrate

    migrate.run(seed=True, db_dir=REPO_ROOT / "db")
    return True


@pytest.fixture
def clean_db(migrated, monkeypatch):
    """Empty notification tables before each test; SMTP disabled."""
    from sales_common import db

    monkeypatch.delenv("SMTP_ENABLED", raising=False)
    db.execute("DELETE FROM notifications")
    db.execute("DELETE FROM dedup_cache")
    yield db
    db.execute("DELETE FROM notifications")
    db.execute("DELETE FROM dedup_cache")
