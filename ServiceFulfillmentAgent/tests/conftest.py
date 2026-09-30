import os
import uuid
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("GEMINI_MODEL", "gemini-test")  # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
    os.environ.setdefault("DB_DIR", str(Path(__file__).resolve().parents[2] / "db"))

requires_db = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")


@pytest.fixture(scope="session")
def migrated_db():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL not set")
    from sales_common import db, migrate

    migrate.run(seed=True)
    yield
    db.close_pool()


@pytest.fixture
def next_weekday() -> str:
    day = date.today() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day.isoformat()


@pytest.fixture
def order(migrated_db):
    """A fresh prospect account + pending_payment order with one item."""
    from sales_common import db

    suffix = uuid.uuid4().hex[:8].upper()
    customer_id = f"CUST-TEST-{suffix}"
    order_id = f"ORD-TEST-{suffix}"
    company = f"Fulfillment Test Co {suffix}"
    now = db.now_iso()
    with db.transaction() as conn:
        conn.execute(
            'INSERT INTO accounts ("Company Name", "Industry", "Street", "City", "State", zip_code, '
            '"Existing Customer", "Current Products", customer_id, created_at, updated_at) '
            "VALUES (%s, 'Retail', '8265 Broadway', 'Portland', 'OR', '97201', 'N', 'Voice', %s, %s, %s)",
            (company, customer_id, now, now),
        )
        conn.execute(
            "INSERT INTO orders (order_id, customer_name, customer_id, service_address, contact_phone, "
            "contact_email, status, total_amount, created_at, updated_at) "
            "VALUES (%s, %s, %s, '8265 Broadway, Portland, OR 97201', '555-0100', 'buyer@example.com', "
            "'pending_payment', 249.99, %s, %s)",
            (order_id, company, customer_id, now, now),
        )
        conn.execute(
            "INSERT INTO order_items (order_id, service_type, price, quantity, subtotal) "
            "VALUES (%s, 'Business Fiber 1 Gbps', 249.99, 1, 249.99)",
            (order_id,),
        )
    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "customer_name": company,
        "contact_email": "buyer@example.com",
        "service_address": "8265 Broadway, Portland, OR 97201",
        "service_type": "Business Fiber 1 Gbps",
        "total_amount": 249.99,
        "status": "pending_payment",
    }


@pytest.fixture
def tool_context(order):
    """Minimal stand-in for ADK ToolContext: tools only use ``.state``."""
    return SimpleNamespace(state={"order_context": dict(order)})
