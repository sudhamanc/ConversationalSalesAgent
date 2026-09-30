import os

import pytest

os.environ.setdefault("GEMINI_MODEL", "gemini-test")
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("SUGGESTIONS_ENABLED", "false")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


def pytest_configure(config):
    config.addinivalue_line("markers", "pg: requires TEST_DATABASE_URL (PostgreSQL)")


def pytest_collection_modifyitems(config, items):
    if os.getenv("TEST_DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set")
    for item in items:
        if "pg" in item.keywords:
            item.add_marker(skip)
