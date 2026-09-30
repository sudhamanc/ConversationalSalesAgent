"""Transactional notification outbox.

Producer services (offer, order, payment, fulfillment, gateway maintenance)
insert a ``notifications`` row with ``status='pending'`` inside the same
transaction as the business change. The customer communication service's
dispatcher renders and delivers pending rows (SMTP or simulated) and marks them
``sent`` / ``simulated`` / ``failed``.

``metadata_json`` carries ``{"template": <notification_type>, "args": {...}}``
so the dispatcher can render the message with the communication service's own
templates.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Optional

from psycopg import Connection

from .db import now_iso, transaction

logger = logging.getLogger("sales_common.notifications")

NOTIFICATION_TYPES = {
    "quote_confirmation",
    "order_confirmation",
    "payment_confirmation",
    "installation_scheduled",
    "installation_reminder",
    "installation_complete",
    "service_activated",
    "abandoned_cart",
    "order_status_update",
    "quote_expired",
    "order_cancelled",
    "escalation",
    "install_dispatched",
}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def enqueue(
    notification_type: str,
    *,
    recipient_email: Optional[str] = None,
    recipient_phone: Optional[str] = None,
    args: Optional[dict[str, Any]] = None,
    customer_id: Optional[str] = None,
    order_id: Optional[str] = None,
    channels: Optional[list[str]] = None,
    conn: Optional[Connection] = None,
) -> Optional[str]:
    """Insert a pending notification. Returns its id, or ``None`` if no recipient.

    Pass ``conn`` to join the caller's transaction (recommended), otherwise a
    new transaction is used.
    """
    if notification_type not in NOTIFICATION_TYPES:
        raise ValueError(f"Unknown notification_type {notification_type!r}")
    email = (recipient_email or "").strip() or None
    if email and not _EMAIL_RE.match(email):
        logger.warning("Skipping notification %s: invalid email", notification_type)
        email = None
    if not email and not recipient_phone:
        logger.info("No recipient for %s notification; not enqueued", notification_type)
        return None
    notification_id = f"NTF-{uuid.uuid4().hex[:12].upper()}"
    now = now_iso()
    params = (
        notification_id,
        notification_type,
        email,
        recipient_phone,
        json.dumps({"template": notification_type, "args": args or {}}, default=str),
        customer_id,
        order_id,
        json.dumps(channels or ([c for c, v in (("email", email), ("sms", recipient_phone)) if v])),
        now,
        now,
    )
    sql = (
        "INSERT INTO notifications (notification_id, notification_type, recipient_email, "
        "recipient_phone, metadata_json, customer_id, order_id, status, channels_json, "
        "created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s,%s)"
    )
    if conn is not None:
        conn.execute(sql, params)
    else:
        with transaction() as own:
            own.execute(sql, params)
    logger.info("Enqueued %s notification %s", notification_type, notification_id)
    return notification_id
