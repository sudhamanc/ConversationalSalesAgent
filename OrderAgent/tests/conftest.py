import json
import os
import uuid
from pathlib import Path

os.environ.setdefault("GEMINI_MODEL", "gemini-test")  # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
os.environ.setdefault("DB_DIR", str(Path(__file__).resolve().parents[2] / "db"))
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def pg():
    """Migrated + seeded scratch database."""
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL not set")
    from sales_common import migrate

    migrate.run(seed=True)
    return os.environ["DATABASE_URL"]


@pytest.fixture
def quote(pg):
    """Insert an active quote row (as offer_management_agent would) and return its offer_id."""
    from sales_common import db

    offer_id = f"OFF-T{uuid.uuid4().hex[:9].upper()}"
    now = db.now_iso()
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO quotes (offer_id, customer_id, company_name, items_json, subtotal, "
            "total_price, monthly_total, yearly_total, full_quote_json, created_at, updated_at, expires_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (offer_id, "CUST-QT", "Quote Test Co", json.dumps([{"product_id": "FIB-1G"}]),
             249.0, 249.0, 249.0, 2988.0, json.dumps({"offer_id": offer_id}), now, now,
             db.compute_expires_at(now, "quote")),
        )
    return offer_id
