"""Returning-customer summary (spec: agent-services "Returning customers are acknowledged and resumed")."""

import json
from datetime import datetime, timedelta

from sales_common.repositories.customer_state import returning_status, summarize_returning_customer

ACCOUNT = {"company_name": "Acme", "street": "123 Main Street", "city": "Philadelphia", "state": "PA", "zip_code": "19103"}
SVC = {"is_serviceable": True, "max_speed_mbps": 5000, "infrastructure_type": "FTTP", "service_address": "123 Main Street, Philadelphia, PA 19103"}


def _state(**overrides):
    base = {
        "customer_id": "CUST-1", "account": ACCOUNT, "active_quotes": [], "active_carts": [], "pending_orders": [],
        "payments": [], "fulfillments": [], "is_activated_customer": False, "active_services": None,
        "fulfilled_orders": [], "active_quote": None, "last_serviceability": None,
    }
    base.update(overrides)
    return base


def _check(days_ago=1, street="123 main street"):
    when = (datetime.utcnow() - timedelta(days=days_ago)).isoformat(timespec="seconds")
    return {"street": street, "city": "Philadelphia", "state": "PA", "zip_code": "19103",
            "is_serviceable": True, "result_json": json.dumps(SVC), "checked_at": when}


QUOTE = {"offer_id": "OFF-1", "items": [{"product_id": "FIB-5G"}], "term_months": 12, "total_price": 7188.0,
         "monthly_total": 599.0, "total_discount": 0.0, "created_at": "2026-11-16T18:00:00", "expires_at": "2026-12-16T18:00:00"}


def test_status_known_in_progress_active():
    assert returning_status(_state()) == "known"
    assert returning_status(_state(active_quotes=[{"offer_id": "OFF-1"}])) == "in_progress"
    assert returning_status(_state(fulfillments=[{"status": "scheduled"}])) == "in_progress"
    assert returning_status(_state(is_activated_customer=True, active_quotes=[{"offer_id": "OFF-1"}])) == "active_service"
    assert returning_status(_state(fulfilled_orders=[{"order_id": "ORD-1"}])) == "active_service"
    assert returning_status(_state(fulfillments=[{"status": "activated"}])) == "active_service"


def test_active_quote_restored_as_offer_context():
    out = summarize_returning_customer(_state(active_quotes=[{"offer_id": "OFF-1"}], active_quote=QUOTE))
    assert out["returning_customer_context"]["status"] == "in_progress"
    assert out["offer_context"]["offer_id"] == "OFF-1"
    assert out["offer_context"]["monthly_total"] == 599.0
    assert out["offer_context"]["restored"] is True
    assert out["offer_context"]["customer_id"] == "CUST-1"


def test_recent_check_for_same_address_is_reused():
    out = summarize_returning_customer(_state(last_serviceability=_check(days_ago=3)), reuse_days=30)
    svc = out["serviceability_context"]
    assert svc["reused"] is True and svc["max_speed_mbps"] == 5000
    assert out["returning_customer_context"]["last_serviceability"]["reused"] is True


def test_stale_or_other_address_check_is_not_reused():
    stale = summarize_returning_customer(_state(last_serviceability=_check(days_ago=45)), reuse_days=30)
    other = summarize_returning_customer(_state(last_serviceability=_check(street="9 Elm St")), reuse_days=30)
    assert stale["serviceability_context"] is None and other["serviceability_context"] is None
    assert stale["returning_customer_context"]["last_serviceability"]["reused"] is False


def test_known_customer_has_nothing_to_restore():
    out = summarize_returning_customer(_state())
    assert out["returning_customer_context"]["status"] == "known"
    assert out["offer_context"] is None and out["serviceability_context"] is None
    json.dumps(out)  # JSON-safe for session state
