"""Cart -> order flow against PostgreSQL."""

import json
import uuid
from types import SimpleNamespace

from order_agent.tools.cart_tools import add_to_cart, clear_cart, create_cart, get_cart, remove_from_cart
from order_agent.tools.order_tools import (
    cancel_order,
    create_order,
    generate_contract,
    get_order,
    modify_order,
    update_order_status,
)

ORDER_CONTEXT_KEYS = {
    "order_id", "customer_id", "customer_name", "contact_email", "contact_phone",
    "service_address", "service_type", "price", "offer_id", "total_amount", "status",
}


def test_cart_flow(pg):
    cid = f"CUST-CART-{uuid.uuid4().hex[:6]}"
    created = create_cart(cid)
    assert created["success"] and created["cart_id"].startswith("CART-")
    cart_id = created["cart_id"]

    r = add_to_cart(cart_id, "Business Fiber 1 Gbps", 249.0)
    assert r["success"] and r["cart"]["total_amount"] == 249.0
    r = add_to_cart(cart_id, "Business Voice Standard", 24.0, quantity=2)
    r = add_to_cart(cart_id, "Business Voice Standard", 24.0, quantity=1)
    assert r["cart"]["total_amount"] == 249.0 + 72.0
    assert [i["quantity"] for i in r["cart"]["items"]] == [1, 3]

    r = remove_from_cart(cart_id, "Business Voice Standard")
    assert r["cart"]["total_amount"] == 249.0
    fetched = get_cart(cart_id)
    assert fetched["success"] and fetched["cart"]["customer_id"] == cid
    assert len(fetched["cart"]["items"]) == 1

    assert clear_cart(cart_id)["success"]
    assert get_cart(cart_id)["cart"]["items"] == []
    assert get_cart("CART-NOPE")["success"] is False
    assert add_to_cart("CART-NOPE", "x", 1.0)["success"] is False


def test_create_order_links_quote_and_enqueues(pg, quote):
    from sales_common import db

    name = f"Order Test {uuid.uuid4().hex[:6]}"
    ctx = SimpleNamespace(state={"offer_context": {"offer_id": quote, "total_price": 249.0}})
    result = create_order(
        customer_name=name,
        service_address="1 Main St, Boston MA 02108",
        service_type="Business Fiber 1 Gbps",
        customer_id="CUST-ORD-1",
        contact_email="buyer@example.com",
        tool_context=ctx,
    )
    assert result["success"], result
    order_id = result["order_id"]
    assert result["offer_id"] == quote
    assert result["status"] == "pending_payment"
    assert result["total_amount"] == 249.0
    assert result["email_confirmation_sent"] is True

    oc = ctx.state["order_context"]
    assert set(oc) == ORDER_CONTEXT_KEYS
    assert oc["order_id"] == order_id and oc["offer_id"] == quote and oc["price"] == 249.0

    assert db.fetch_one("SELECT status FROM quotes WHERE offer_id=%s", (quote,))["status"] == "ordered"
    row = db.fetch_one("SELECT * FROM orders WHERE order_id=%s", (order_id,))
    assert row["status"] == "pending_payment" and row["offer_id"] == quote
    notif = db.fetch_one("SELECT * FROM notifications WHERE notification_id=%s",
                         (result["email_notification_id"],))
    assert notif["status"] == "pending" and notif["notification_type"] == "order_confirmation"
    assert notif["order_id"] == order_id
    args = json.loads(notif["metadata_json"])["args"]
    assert args["order_id"] == order_id and args["total_amount"] == 249.0

    got = get_order(order_id)
    assert got["success"] and got["order"]["items"][0]["service_type"] == "Business Fiber 1 Gbps"

    mod = modify_order(order_id, service_type="Business Fiber 5 Gbps", price=599.0)
    assert mod["success"] and mod["order"]["total_amount"] == 599.0
    contract = generate_contract(order_id)
    assert contract["contract"]["contract_id"] == f"CONT-{order_id}"

    upd = update_order_status(order_id, "confirmed")
    assert upd["old_status"] == "pending_payment" and upd["new_status"] == "confirmed"
    assert modify_order(order_id, price=1.0)["success"] is False
    assert update_order_status(order_id, "bogus")["success"] is False

    cancelled = cancel_order(order_id, reason="test")
    assert cancelled["status"] == "cancelled"
    assert db.fetch_one("SELECT status FROM orders WHERE order_id=%s", (order_id,))["status"] == "cancelled"


def test_create_order_unknown_offer_is_dropped(pg):
    result = create_order(
        customer_name=f"No Quote {uuid.uuid4().hex[:6]}",
        service_address="2 Main St",
        service_type="Business Internet 200 Mbps",
        price=79.0,
        offer_id="OFF-DOESNOTEXIST",
    )
    assert result["success"], result
    assert result["offer_id"] is None and "warning" in result
    assert result["customer_id"].startswith("CUST-")
    assert result["email_confirmation_sent"] is False  # no email, "Not provided" phone


def test_missing_order(pg):
    assert get_order("ORD-NOPE")["success"] is False
    assert cancel_order("ORD-NOPE")["success"] is False
    assert generate_contract("ORD-NOPE")["success"] is False


def test_same_day_orders_for_same_company_do_not_collide(pg):
    """Regression: IDs were ``hash(customer_name) % 1000`` so repeat orders overwrote each other."""
    from sales_common import db

    name = f"Repeat Buyer {uuid.uuid4().hex[:6]}"
    ids = []
    for _ in range(2):
        result = create_order(
            customer_name=name,
            service_address="1 Main St, Boston MA 02108",
            service_type="Business Fiber 1 Gbps",
            customer_id="CUST-REPEAT-1",
            price=100.0,
        )
        assert result["success"], result
        ids.append(result["order_id"])
    assert ids[0] != ids[1]
    assert db.fetch_one("SELECT count(*) AS n FROM orders WHERE order_id = ANY(%s)", (ids,))["n"] == 2
    carts = {create_cart("CUST-REPEAT-1")["cart_id"] for _ in range(3)}
    assert len(carts) == 3
