import os

import pytest

TEST_DB = os.getenv("TEST_DATABASE_URL", "")


def pytest_collection_modifyitems(config, items):
    if TEST_DB:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set (PostgreSQL integration tests)")
    for item in items:
        if "pg" in item.keywords:
            item.add_marker(skip)


def pytest_configure(config):
    config.addinivalue_line("markers", "pg: requires a PostgreSQL TEST_DATABASE_URL")


@pytest.fixture
def pg_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DB)
    from sales_common import db

    db.close_pool()
    yield TEST_DB
    db.close_pool()
