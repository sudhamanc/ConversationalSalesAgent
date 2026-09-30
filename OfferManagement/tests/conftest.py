import os
from pathlib import Path

os.environ.setdefault("GEMINI_MODEL", "gemini-test")  # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
os.environ.setdefault("DB_DIR", str(Path(__file__).resolve().parents[2] / "db"))
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

import pytest  # noqa: E402

requires_pg = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")


@pytest.fixture(scope="session")
def pg():
    """Migrated + seeded scratch database."""
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL not set")
    from sales_common import migrate

    migrate.run(seed=True)
    return os.environ["DATABASE_URL"]


@pytest.fixture(autouse=True)
def _fresh_cache():
    from offer_management.utils.cache import clear_cache

    clear_cache()
    yield
    clear_cache()
