"""Serviceability service tests.

Database-backed tests need ``TEST_DATABASE_URL`` (a scratch PostgreSQL
database); they run ``sales_common.migrate.run(seed=True)`` once per session
and are skipped when the variable is unset.
"""

import os
import sys
from pathlib import Path

import pytest

SERVICE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_DIR.parents[1]
sys.path.insert(0, str(SERVICE_DIR))

TEST_DB = os.getenv("TEST_DATABASE_URL", "")
if TEST_DB:
    os.environ["DATABASE_URL"] = TEST_DB
os.environ.setdefault("USE_MOCK_DATA", "true")


def pytest_configure(config):
    config.addinivalue_line("markers", "pg: requires a PostgreSQL TEST_DATABASE_URL")


def pytest_collection_modifyitems(config, items):
    if TEST_DB:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set (PostgreSQL integration tests)")
    for item in items:
        if "pg" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def migrated_db():
    """Apply migrations + seeds to the scratch database once per session."""
    from sales_common import db, migrate

    migrate.run(seed=True, db_dir=REPO_ROOT / "db")
    yield TEST_DB
    db.close_pool()
