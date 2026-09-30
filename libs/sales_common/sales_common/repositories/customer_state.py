"""Cross-table customer pipeline lookup (replaces Discovery -> SuperAgent call)."""

from __future__ import annotations

from typing import Any

from ..db import transaction


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
        result["is_activated_customer"] = (
            conn.execute(
                "SELECT 1 FROM customer_master WHERE customer_id = %s", (customer_id,)
            ).fetchone()
            is not None
        )
    return result
