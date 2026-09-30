"""PostgreSQL queries for the ``notifications`` table (via ``sales_common.db``).

Writes happen through the outbox: ``sales_common.notifications.enqueue`` inserts
pending rows and :mod:`customer_communication_agent.dispatcher` delivers them
(and maintains ``dedup_cache``). This module only reads.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from sales_common import db


def _loads(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except ValueError:
        return default


def row_to_dict(row: dict) -> dict[str, Any]:
    """JSON-friendly notification record."""
    meta = _loads(row.get("metadata_json"), {})
    return {
        "notification_id": row["notification_id"],
        "notification_type": row["notification_type"],
        "recipient_email": row.get("recipient_email"),
        "recipient_phone": row.get("recipient_phone"),
        "subject": row.get("subject"),
        "message": row.get("message"),
        "metadata": meta.get("args", meta) if isinstance(meta, dict) else {},
        "customer_id": row.get("customer_id"),
        "order_id": row.get("order_id"),
        "status": row["status"],
        "channels": _loads(row.get("channels_json"), []),
        "attempts": row.get("attempts") or 0,
        "created_at": row.get("created_at"),
        "sent_at": row.get("sent_at"),
        "error": row.get("error"),
    }


def get_notification(notification_id: str) -> Optional[dict[str, Any]]:
    row = db.fetch_one("SELECT * FROM notifications WHERE notification_id = %s", (notification_id,))
    return row_to_dict(row) if row else None


def get_history(
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    notification_type: Optional[str] = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Notifications filtered by email (case-insensitive) / phone / type, newest first."""
    clauses: list[str] = []
    params: list[Any] = []
    if customer_email:
        clauses.append("lower(recipient_email) = lower(%s)")
        params.append(customer_email.strip())
    if customer_phone:
        clauses.append("recipient_phone = %s")
        params.append(customer_phone.strip())
    if notification_type:
        clauses.append("notification_type = %s")
        params.append(notification_type)
    where = " AND ".join(clauses) if clauses else "TRUE"
    params.append(limit)
    rows = db.fetch_all(
        f"SELECT * FROM notifications WHERE {where} "
        "ORDER BY created_at DESC, notification_id DESC LIMIT %s",
        params,
    )
    return [row_to_dict(r) for r in rows]
