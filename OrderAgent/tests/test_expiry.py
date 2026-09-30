"""Regression: carts/orders get an ``expires_at`` so maintenance can expire them."""

import uuid
from datetime import datetime, timedelta

from order_agent.tools.cart_tools import add_to_cart, create_cart, remove_from_cart
from order_agent.tools.order_tools import create_order


def _row(table: str, key: str, value: str) -> dict:
    from sales_common import db

    return db.fetch_one(f"SELECT * FROM {table} WHERE {key} = %s", (value,))


def test_cart_has_expires_at_and_refreshes_on_activity(pg):
    from sales_common import db

    cart_id = create_cart(f"CUST-EXP-{uuid.uuid4().hex[:6]}")["cart_id"]
    row = _row("carts", "cart_id", cart_id)
    assert row["expires_at"] is not None
    assert row["expires_at"] == db.compute_expires_at(row["created_at"], "cart")

    # Push expiry into the past, then activity must slide it 24h past updated_at.
    db.execute("UPDATE carts SET expires_at = '2000-01-01T00:00:00' WHERE cart_id = %s", (cart_id,))
    add_to_cart(cart_id, "Business Fiber 1 Gbps", 249.0)
    row = _row("carts", "cart_id", cart_id)
    assert row["expires_at"] == db.compute_expires_at(row["updated_at"], "cart")

    db.execute("UPDATE carts SET expires_at = '2000-01-01T00:00:00' WHERE cart_id = %s", (cart_id,))
    remove_from_cart(cart_id, "Business Fiber 1 Gbps")
    row = _row("carts", "cart_id", cart_id)
    assert datetime.fromisoformat(row["expires_at"]) > datetime.utcnow() + timedelta(hours=23)


def test_order_has_expires_at(pg):
    from sales_common import db

    result = create_order(
        customer_name=f"Expiry Co {uuid.uuid4().hex[:6]}",
        service_address="1 Main St, Boston MA 02108",
        service_type="Business Fiber 1 Gbps",
        customer_id="CUST-EXP-ORD",
        price=249.0,
    )
    assert result["success"]
    row = _row("orders", "order_id", result["order_id"])
    assert row["status"] == "pending_payment"
    assert row["expires_at"] == db.compute_expires_at(row["created_at"], "order")


def test_cleanup_expires_stale_cart_and_order(pg):
    from sales_common import db
    from sales_common.maintenance import cleanup_stale_records

    cart_id = create_cart(f"CUST-EXP-{uuid.uuid4().hex[:6]}")["cart_id"]
    fresh_cart = create_cart(f"CUST-EXP-{uuid.uuid4().hex[:6]}")["cart_id"]
    order_id = create_order(
        customer_name="Stale Order Co",
        service_address="1 Main St, Boston MA 02108",
        service_type="Business Fiber 1 Gbps",
        customer_id="CUST-EXP-STALE",
        price=99.0,
    )["order_id"]
    past = "2000-01-01T00:00:00"
    db.execute("UPDATE carts SET expires_at = %s WHERE cart_id = %s", (past, cart_id))
    db.execute("UPDATE orders SET expires_at = %s WHERE order_id = %s", (past, order_id))

    counts = cleanup_stale_records()

    assert counts["carts_expired"] >= 1 and counts["orders_cancelled"] >= 1
    assert _row("carts", "cart_id", cart_id)["status"] == "expired"
    assert _row("carts", "cart_id", fresh_cart)["status"] == "active"
    assert _row("orders", "order_id", order_id)["status"] == "cancelled"
