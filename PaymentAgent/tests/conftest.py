import os

os.environ.setdefault("GEMINI_MODEL", "gemini-test")  # construction only; never called
os.environ.setdefault("PUBLIC_URL", "http://localhost:0")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

import uuid

import pytest


@pytest.fixture(scope="session")
def migrated_db():
    from pathlib import Path

    from sales_common import migrate

    migrate.run(seed=True, db_dir=Path(__file__).resolve().parents[2] / "db")
    yield
    from sales_common import db

    db.close_pool()


@pytest.fixture
def make_order(migrated_db):
    """Create a fresh pending_payment order (unique customer, so rate limits never collide)."""
    from sales_common import db

    def _make(total: float = 249.0, email: str = "buyer@example.com") -> dict:
        suffix = uuid.uuid4().hex[:8].upper()
        order = {
            "order_id": f"ORD-TEST-{suffix}",
            "customer_id": f"CUST-TEST-{suffix}",
            "customer_name": "Test Corp",
            "service_address": "1 Test St, Denver, CO",
            "contact_phone": "555-0100",
            "contact_email": email,
            "status": "pending_payment",
            "total_amount": total,
        }
        now = db.now_iso()
        db.execute(
            "INSERT INTO orders (order_id, customer_name, customer_id, service_address, contact_phone, "
            "contact_email, status, total_amount, created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (order["order_id"], order["customer_name"], order["customer_id"], order["service_address"],
             order["contact_phone"], order["contact_email"], order["status"], total, now, now),
        )
        return order

    return _make
