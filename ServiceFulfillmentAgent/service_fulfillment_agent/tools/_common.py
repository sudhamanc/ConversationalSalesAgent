"""Shared helpers for fulfillment tools: order/fulfillment lookups and journey state.

All persistence goes through ``sales_common.db`` (PostgreSQL). There is no
in-memory fallback: when ``DATABASE_URL`` is unset, ``sales_common.db`` raises.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

from psycopg import Connection

logger = logging.getLogger("service_fulfillment_agent.tools")

#: Fulfillment statuses that still represent a live (not yet activated) appointment.
OPEN_FULFILLMENT_STATUSES = ("scheduled", "dispatched", "installed")


def stable_number(value: str, modulo: int) -> int:
    """Process-independent hash (Python's ``hash()`` is salted per process)."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def state_dict(tool_context, key: str) -> dict[str, Any]:
    """Return ``tool_context.state[key]`` as a dict (empty when absent)."""
    if tool_context is None:
        return {}
    value = tool_context.state.get(key)
    return dict(value) if isinstance(value, dict) else {}


def state_order_id(tool_context) -> Optional[str]:
    """Order id forwarded by the gateway in ``order_context`` / ``payment_context``."""
    order_ctx = state_dict(tool_context, "order_context")
    payment_ctx = state_dict(tool_context, "payment_context")
    for candidate in (order_ctx.get("order_id"), payment_ctx.get("order_id")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def update_order_context(tool_context, order_id: str, **fields: Any) -> None:
    """Merge ``fields`` into ``order_context`` when it belongs to ``order_id``.

    ``order_context`` is owned by the order agent; fulfillment only adds
    installation/activation fields (and ``status`` on activation). The write is
    exported to the gateway by ``export_context_delta``.
    """
    if tool_context is None:
        return
    current = state_dict(tool_context, "order_context")
    if current.get("order_id") not in (None, "", order_id):
        return
    current["order_id"] = order_id
    current.update(fields)
    tool_context.state["order_context"] = current


def get_order(conn: Connection, order_id: str) -> Optional[dict]:
    return conn.execute(
        "SELECT order_id, customer_id, customer_name, service_address, contact_phone, "
        "contact_email, status, total_amount FROM orders WHERE order_id = %s",
        (order_id,),
    ).fetchone()


def find_fulfillment(
    conn: Connection,
    appointment_id: Optional[str] = None,
    order_id: Optional[str] = None,
    *,
    for_update: bool = False,
) -> Optional[dict]:
    """Find a fulfillment by appointment id, else the latest one for ``order_id``."""
    lock = " FOR UPDATE" if for_update else ""
    if appointment_id:
        row = conn.execute(
            f"SELECT * FROM fulfillments WHERE fulfillment_id = %s{lock}", (appointment_id,)
        ).fetchone()
        if row:
            return row
    if order_id:
        return conn.execute(
            "SELECT * FROM fulfillments WHERE order_id = %s "
            f"ORDER BY created_at DESC, fulfillment_id DESC LIMIT 1{lock}",
            (order_id,),
        ).fetchone()
    return None
