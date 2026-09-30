"""Read-only order/fulfillment status for the fulfillment agent.

Order creation and order status changes belong to ``order_agent``. The former
simulated ``create_order`` / ``update_order_status`` stubs were removed; the
fulfillment agent only reads ``orders`` here (its single ``orders`` write is
``status = 'fulfilled'`` inside ``activate_service``).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import psycopg
from google.adk.tools.tool_context import ToolContext

from sales_common import db

from ._common import get_order, state_order_id

logger = logging.getLogger(__name__)

_STAGES = ("scheduled", "dispatched", "installed", "activated")


def get_fulfillment_status(
    order_id: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Returns the order status and installation/activation progress for an order.

    Args:
        order_id: Order identifier (defaults to the journey order_context)

    Returns:
        Order status plus the latest fulfillment record and lifecycle stages
    """
    order_id = (order_id or "").strip() or state_order_id(tool_context)
    if not order_id:
        return {"success": False, "error": "order_id is required"}
    try:
        with db.transaction() as conn:
            order = get_order(conn, order_id)
            if order is None:
                return {"success": False, "error": f"Order {order_id} not found"}
            fulfillment = conn.execute(
                "SELECT fulfillment_id, status, appointment_date, dispatch_id, activation_id, "
                "circuit_id, account_id, updated_at FROM fulfillments WHERE order_id = %s "
                "ORDER BY created_at DESC, fulfillment_id DESC LIMIT 1",
                (order_id,),
            ).fetchone()
    except psycopg.Error as exc:
        logger.error("Status lookup failed for %s: %s", order_id, exc)
        return {"success": False, "error": f"Order status error: {type(exc).__name__}"}

    current = fulfillment["status"] if fulfillment else "not_scheduled"
    reached = _STAGES.index(current) if current in _STAGES else -1
    stages = [{"stage": s, "completed": i <= reached} for i, s in enumerate(_STAGES)]
    return {
        "success": True,
        "order_id": order_id,
        "customer_id": order["customer_id"],
        "customer_name": order["customer_name"],
        "order_status": order["status"],
        "fulfillment_status": current,
        "appointment_id": fulfillment["fulfillment_id"] if fulfillment else None,
        "appointment_date": fulfillment["appointment_date"] if fulfillment else None,
        "dispatch_id": fulfillment["dispatch_id"] if fulfillment else None,
        "circuit_id": fulfillment["circuit_id"] if fulfillment else None,
        "account_id": fulfillment["account_id"] if fulfillment else None,
        "status_stages": stages,
        "last_updated": fulfillment["updated_at"] if fulfillment else None,
    }
