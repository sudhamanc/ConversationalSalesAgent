"""Offer Management pricing tools (pure pricing + PostgreSQL persistence)."""

import json
import uuid
from types import SimpleNamespace

from offer_management.tools.pricing_tools import (
    find_best_bundle_offer,
    generate_offer_quote,
    get_existing_quotes,
    get_quote_details,
)


def _ctx(state=None):
    return SimpleNamespace(state=dict(state or {}))


def test_find_best_bundle_offer_success():
    result = find_best_bundle_offer(
        [
            {"product_id": "FIB-5G", "quantity": 1},
            {"product_id": "VOICE-STD", "quantity": 10},
        ],
        term_months=24,
    )
    assert result["found"] is True
    assert result["offer_id"].startswith("OFF-")
    assert result["bundle_discount_rate"] > 0
    assert result["term_discount_rate"] == 0.05


def test_generate_offer_quote_unknown_product():
    result = generate_offer_quote([{"product_id": "NOPE-1", "quantity": 1}])
    assert result["found"] is False
    assert result["error"] == "unknown_products"


def test_generate_offer_quote_persists_and_enqueues(pg):
    from sales_common import db

    cid = f"CUST-T-{uuid.uuid4().hex[:6]}"
    email = f"{cid.lower()}@example.com"
    ctx = _ctx()
    result = generate_offer_quote(
        json.dumps([{"product_id": "FIB-1G"}, {"product_id": "SDWAN-ESS", "quantity": 1}]),
        term_months=36,
        bant_score=80.0,
        customer_id=cid,
        company_name="Test Co",
        customer_email=email,
        tool_context=ctx,
    )
    assert result["offer_id"].startswith("OFF-")
    assert len(result["items"]) == 2
    for key in ("subtotal", "total_discount", "total_price", "monthly_total", "yearly_total",
                "discount_breakdown"):
        assert key in result
    assert {d["type"] for d in result["discount_breakdown"]} == {"bundle", "term", "bant"}

    offer_ctx = ctx.state["offer_context"]
    assert offer_ctx["offer_id"] == result["offer_id"]
    assert offer_ctx["customer_id"] == cid
    assert offer_ctx["total_price"] == result["total_price"]
    assert set(offer_ctx) == {"offer_id", "customer_id", "company_name", "items", "term_months",
                              "total_price", "monthly_total", "total_discount"}

    row = db.fetch_one("SELECT * FROM quotes WHERE offer_id = %s", (result["offer_id"],))
    assert row["customer_id"] == cid and row["status"] == "active"
    assert row["total_price"] == result["total_price"]

    sent = result["notification_sent"]
    assert sent["type"] == "QUOTE_CONFIRMATION" and sent["recipient"] == email
    notif = db.fetch_one("SELECT * FROM notifications WHERE notification_id = %s", (sent["notification_id"],))
    assert notif["status"] == "pending"
    assert notif["notification_type"] == "quote_confirmation"
    args = json.loads(notif["metadata_json"])["args"]
    assert args["offer_id"] == result["offer_id"]
    assert args["monthly_total"] == result["monthly_total"]
    assert len(args["items"]) == 2

    listed = get_existing_quotes(customer_id=cid)
    assert listed["success"] and listed["quotes"][0]["offer_id"] == result["offer_id"]
    details = get_quote_details(result["offer_id"])
    assert details["success"] and details["quote"]["total_price"] == result["total_price"]


def test_cache_hit_still_publishes_offer_context(pg):
    items = [{"product_id": "COAX-500M"}]
    first = generate_offer_quote(items, customer_id="CUST-A", company_name="A Co")
    ctx = _ctx()
    second = generate_offer_quote(items, customer_id="CUST-B", company_name="B Co", tool_context=ctx)
    assert second["offer_id"] != first["offer_id"]  # offer ids are per customer
    assert second["total_price"] == first["total_price"]  # pricing served from cache
    assert ctx.state["offer_context"]["offer_id"] == second["offer_id"]
    assert ctx.state["offer_context"]["customer_id"] == "CUST-B"


def test_no_email_no_notification(pg):
    result = generate_offer_quote([{"product_id": "MOB-UNL", "quantity": 3}], customer_id="CUST-NOEMAIL")
    assert "notification_sent" not in result


def test_quote_lookup_errors(pg):
    assert get_existing_quotes()["success"] is False
    assert get_quote_details("OFF-DOESNOTEXIST")["success"] is False


def test_same_bundle_for_two_customers_is_isolated(pg):
    """Regression: the quote cache ignored the customer, so a cache hit skipped
    persistence/notification and returned the previous caller's customer fields;
    offer ids were identical across customers so the upsert overwrote quotes."""
    from sales_common import db

    items = json.dumps([{"product_id": "FIB-1G", "quantity": 1}])
    a_id, b_id = f"CUST-A-{uuid.uuid4().hex[:6]}", f"CUST-B-{uuid.uuid4().hex[:6]}"
    ctx_a, ctx_b = _ctx(), _ctx()
    qa = generate_offer_quote(items, 12, 0.0, customer_id=a_id, company_name="A Co",
                              customer_email="a@example.com", tool_context=ctx_a)
    qb = generate_offer_quote(items, 12, 0.0, customer_id=b_id, company_name="B Co",
                              customer_email="b@example.com", tool_context=ctx_b)  # pricing cache hit

    assert qa["offer_id"] != qb["offer_id"]
    assert qb["customer_id"] == b_id and qb["company_name"] == "B Co"
    assert qa["total_price"] == qb["total_price"]
    assert qb["notification_sent"]["recipient"] == "b@example.com"
    assert ctx_b.state["offer_context"]["customer_id"] == b_id
    rows = {r["offer_id"]: r["customer_id"] for r in db.fetch_all(
        "SELECT offer_id, customer_id FROM quotes WHERE offer_id = ANY(%s)", ([qa["offer_id"], qb["offer_id"]],))}
    assert rows == {qa["offer_id"]: a_id, qb["offer_id"]: b_id}
    # Re-quoting the same customer is idempotent (same offer id, row updated in place).
    again = generate_offer_quote(items, 12, 0.0, customer_id=a_id, company_name="A Co", tool_context=_ctx())
    assert again["offer_id"] == qa["offer_id"]
