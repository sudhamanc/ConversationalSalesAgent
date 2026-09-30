"""Periodic TTL enforcement (run hourly by the gateway)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from . import notifications
from .db import ESCALATION_DAYS, now_iso, transaction

logger = logging.getLogger("sales_common.maintenance")


def cleanup_stale_records() -> dict[str, int]:
    """Expire quotes/carts, cancel timed-out orders, escalate stuck paid orders.

    Abandoned-cart and order-cancelled notifications are enqueued in the same
    transaction (outbox) and delivered by the communication service.
    """
    now = now_iso()
    cutoff = (
        datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=ESCALATION_DAYS)
    ).isoformat(timespec="seconds")
    counts = {
        "quotes_expired": 0,
        "carts_expired": 0,
        "orders_cancelled": 0,
        "orders_escalated": 0,
        "notifications_enqueued": 0,
    }
    with transaction() as conn:
        counts["quotes_expired"] = conn.execute(
            "UPDATE quotes SET status='expired', updated_at=%s "
            "WHERE status='active' AND expires_at < %s",
            (now, now),
        ).rowcount

        carts = conn.execute(
            'SELECT c.cart_id, c.customer_id, a."Company Name" AS company_name, '
            '(SELECT ct."Email" FROM contacts ct WHERE ct."Company Name" = a."Company Name" LIMIT 1) AS email '
            "FROM carts c LEFT JOIN accounts a ON c.customer_id = a.customer_id "
            "WHERE c.status='active' AND c.expires_at < %s FOR UPDATE OF c",
            (now,),
        ).fetchall()
        if carts:
            conn.execute(
                "UPDATE carts SET status='expired', updated_at=%s WHERE cart_id = ANY(%s)",
                (now, [c["cart_id"] for c in carts]),
            )
        counts["carts_expired"] = len(carts)

        orders = conn.execute(
            "SELECT order_id, customer_id, contact_email FROM orders "
            "WHERE status='pending_payment' AND expires_at < %s FOR UPDATE",
            (now,),
        ).fetchall()
        if orders:
            conn.execute(
                "UPDATE orders SET status='cancelled', updated_at=%s WHERE order_id = ANY(%s)",
                (now, [o["order_id"] for o in orders]),
            )
        counts["orders_cancelled"] = len(orders)

        counts["orders_escalated"] = conn.execute(
            "UPDATE orders SET status='escalated', updated_at=%s WHERE status='paid' AND updated_at < %s",
            (now, cutoff),
        ).rowcount

        for cart in carts:
            if notifications.enqueue(
                "abandoned_cart",
                recipient_email=cart["email"],
                customer_id=cart["customer_id"],
                args={"cart_id": cart["cart_id"], "company_name": cart["company_name"] or ""},
                conn=conn,
            ):
                counts["notifications_enqueued"] += 1
        for order in orders:
            if notifications.enqueue(
                "order_cancelled",
                recipient_email=order["contact_email"],
                customer_id=order["customer_id"],
                order_id=order["order_id"],
                args={"order_id": order["order_id"], "reason": "Pending payment timed out"},
                conn=conn,
            ):
                counts["notifications_enqueued"] += 1
    logger.info("cleanup_stale_records: %s", counts)
    return counts
