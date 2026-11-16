"""Cross-table customer pipeline lookup and the returning-customer summary.

``check_customer_state`` returns the raw pipeline rows; ``summarize_returning_customer``
turns them into ``returning_customer_context`` plus the journey keys to restore
(spec: agent-services "Returning customers are acknowledged and resumed").
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from ..config import env_int
from ..db import transaction

ACTIVE_FULFILLMENT = {"activated", "active"}
IN_PROGRESS_FULFILLMENT = {"scheduled", "installed", "rescheduled", "installation_complete"}


def check_customer_state(customer_id: str) -> dict[str, Any]:
    """Return the pipeline position of a customer across all sales tables.

    Keys: ``customer_id``, ``account``, ``active_quotes``, ``active_carts``,
    ``pending_orders``, ``payments``, ``fulfillments``, ``is_activated_customer``.
    """
    result: dict[str, Any] = {
        "customer_id": customer_id,
        "account": None,
        "active_quotes": [],
        "active_carts": [],
        "pending_orders": [],
        "payments": [],
        "fulfillments": [],
        "is_activated_customer": False,
        "active_services": None,
        "fulfilled_orders": [],
        "active_quote": None,
        "last_serviceability": None,
    }
    with transaction() as conn:
        row = conn.execute(
            'SELECT "Company Name", "Street", "City", "State", zip_code, "Existing Customer" '
            "FROM accounts WHERE customer_id = %s",
            (customer_id,),
        ).fetchone()
        if row:
            result["account"] = {
                "company_name": row["Company Name"],
                "street": row["Street"],
                "city": row["City"],
                "state": row["State"],
                "zip_code": row["zip_code"],
                "existing_customer": row["Existing Customer"],
            }
        result["active_quotes"] = list(
            conn.execute(
                "SELECT offer_id, company_name, total_price, status, created_at, expires_at "
                "FROM quotes WHERE customer_id = %s AND status = 'active'",
                (customer_id,),
            ).fetchall()
        )
        result["active_carts"] = list(
            conn.execute(
                "SELECT cart_id, total_amount, status, created_at "
                "FROM carts WHERE customer_id = %s AND status = 'active'",
                (customer_id,),
            ).fetchall()
        )
        result["pending_orders"] = list(
            conn.execute(
                "SELECT order_id, offer_id, status, total_amount, created_at FROM orders "
                "WHERE customer_id = %s AND status IN ('draft','pending_payment','paid')",
                (customer_id,),
            ).fetchall()
        )
        result["payments"] = list(
            conn.execute(
                "SELECT payment_id, order_id, status, amount, created_at FROM payments "
                "WHERE customer_id = %s ORDER BY created_at DESC LIMIT 5",
                (customer_id,),
            ).fetchall()
        )
        result["fulfillments"] = list(
            conn.execute(
                "SELECT fulfillment_id, order_id, status, appointment_date, circuit_id, activation_id "
                "FROM fulfillments WHERE customer_id = %s ORDER BY created_at DESC LIMIT 5",
                (customer_id,),
            ).fetchall()
        )
        master = conn.execute(
            "SELECT contracted_products FROM customer_master WHERE customer_id = %s", (customer_id,)
        ).fetchone()
        result["is_activated_customer"] = master is not None
        if master is not None:
            result["active_services"] = master.get("contracted_products")
        result["fulfilled_orders"] = list(
            conn.execute(
                "SELECT order_id, service_address, status, total_amount, created_at FROM orders "
                "WHERE customer_id = %s AND status = 'fulfilled' ORDER BY created_at DESC LIMIT 5",
                (customer_id,),
            ).fetchall()
        )
        quote = conn.execute(
            "SELECT offer_id, items_json, term_months, total_price, monthly_total, total_discount, "
            "created_at, expires_at FROM quotes WHERE customer_id = %s AND status = 'active' "
            "ORDER BY created_at DESC LIMIT 1",
            (customer_id,),
        ).fetchone()
        if quote:
            try:
                items = json.loads(quote.get("items_json") or "[]")
            except (TypeError, ValueError):
                items = []
            result["active_quote"] = {
                "offer_id": quote["offer_id"],
                "items": items,
                "term_months": quote["term_months"],
                "total_price": quote["total_price"],
                "monthly_total": quote["monthly_total"],
                "total_discount": quote["total_discount"],
                "created_at": quote["created_at"],
                "expires_at": quote["expires_at"],
            }
        check = conn.execute(
            "SELECT street, city, state, zip_code, is_serviceable, result_json, checked_at "
            "FROM serviceability_checks WHERE customer_id = %s ORDER BY checked_at DESC, id DESC LIMIT 1",
            (customer_id,),
        ).fetchone()
        if check:
            result["last_serviceability"] = dict(check)
    return result


def _fresh(checked_at: Optional[str], max_age_days: int) -> bool:
    try:
        checked = datetime.fromisoformat(str(checked_at))
    except (TypeError, ValueError):
        return False
    return datetime.utcnow() - checked <= timedelta(days=max_age_days)


def _same_address(check: dict[str, Any], account: Optional[dict[str, Any]]) -> bool:
    if not account:
        return False
    norm = lambda v: " ".join(str(v or "").lower().replace(".", "").split())  # noqa: E731
    return norm(check.get("zip_code")) == norm(account.get("zip_code")) and norm(check.get("street")) == norm(
        account.get("street")
    )


def returning_status(state: dict[str, Any]) -> str:
    """``active_service`` | ``in_progress`` | ``known`` from a ``check_customer_state`` result."""
    fulfillments = state.get("fulfillments") or []
    if (
        state.get("is_activated_customer")
        or state.get("fulfilled_orders")
        or any(str(f.get("status")).lower() in ACTIVE_FULFILLMENT for f in fulfillments)
    ):
        return "active_service"
    if (
        state.get("active_quotes")
        or state.get("pending_orders")
        or any(str(f.get("status")).lower() in IN_PROGRESS_FULFILLMENT for f in fulfillments)
    ):
        return "in_progress"
    return "known"


def summarize_returning_customer(
    state: dict[str, Any], company_name: Optional[str] = None, reuse_days: Optional[int] = None
) -> dict[str, Any]:
    """``returning_customer_context`` plus journey keys to restore.

    Returns ``{"returning_customer_context": {...}, "offer_context": {...}|None,
    "serviceability_context": {...}|None}``. The active quote becomes ``offer_context``;
    a stored check for the account address within ``SERVICEABILITY_REUSE_DAYS``
    (default 30) becomes ``serviceability_context`` with ``reused: true``.
    """
    reuse_days = reuse_days if reuse_days is not None else env_int("SERVICEABILITY_REUSE_DAYS", 30)
    account = state.get("account") or {}
    company = company_name or account.get("company_name")
    customer_id = state.get("customer_id")

    restored_svc = None
    last = state.get("last_serviceability")
    last_summary = None
    if last:
        try:
            stored = json.loads(last.get("result_json") or "{}")
        except (TypeError, ValueError):
            stored = {}
        reusable = _fresh(last.get("checked_at"), reuse_days) and _same_address(last, account)
        last_summary = {
            "checked_at": last.get("checked_at"),
            "is_serviceable": last.get("is_serviceable"),
            "max_speed_mbps": stored.get("max_speed_mbps"),
            "infrastructure_type": stored.get("infrastructure_type"),
            "service_address": stored.get("service_address"),
            "reused": bool(reusable and stored),
        }
        if reusable and stored:
            restored_svc = {**stored, "reused": True, "checked_at": last.get("checked_at")}

    quote = state.get("active_quote")
    restored_offer = None
    if quote:
        restored_offer = {
            "offer_id": quote["offer_id"],
            "customer_id": customer_id,
            "company_name": company,
            "items": quote.get("items") or [],
            "term_months": quote.get("term_months"),
            "total_price": quote.get("total_price"),
            "monthly_total": quote.get("monthly_total"),
            "total_discount": quote.get("total_discount"),
            "restored": True,
        }

    context = {
        "customer_id": customer_id,
        "company_name": company,
        "status": returning_status(state),
        "active_quote": quote,
        "pending_orders": state.get("pending_orders") or [],
        "fulfillments": state.get("fulfillments") or [],
        "fulfilled_orders": state.get("fulfilled_orders") or [],
        "active_services": state.get("active_services"),
        "last_serviceability": last_summary,
    }
    return {
        "returning_customer_context": json.loads(json.dumps(context, default=str)),
        "offer_context": json.loads(json.dumps(restored_offer, default=str)) if restored_offer else None,
        "serviceability_context": restored_svc,
    }
