"""Notification outbox dispatcher.

Producers insert ``notifications`` rows with ``status='pending'`` through
``sales_common.notifications.enqueue`` (in their business transaction). This
module delivers them:

1. ``SELECT ... WHERE status='pending' <backoff due> ORDER BY seq (insertion order, migration 005)
   FOR UPDATE SKIP LOCKED`` (several service instances can dispatch concurrently without
   double-sending). ``created_at`` has second resolution and ``notifications`` has no
   sequence column, so ``notification_id`` is only a deterministic tiebreak: rows created
   in the same second are processed in id order, not strictly in insertion order.
2. Render subject/message from ``metadata_json = {"template": ..., "args": {...}}``
   with :mod:`.templates` (unknown templates use ``generic``).
3. De-duplicate through ``dedup_cache`` (same template + recipient + reference within
   ``DEDUP_WINDOW_MINUTES``) -> ``status='deduped'``.
4. Email via SMTP when ``SMTP_ENABLED=true`` (``status='sent'``), otherwise simulated
   (``status='simulated'``). SMS is always simulated.
5. On a delivery error the row stays ``pending`` with ``error`` set; after
   ``MAX_ATTEMPTS`` attempts it is marked ``failed``. Retries back off linearly: a row
   with ``attempts > 0`` is picked again only once ``updated_at`` is at least
   ``NOTIFY_RETRY_SECONDS`` (default 60) * ``attempts`` seconds in the past.

:func:`dispatcher_lifespan` runs :func:`dispatch_pending` every ``NOTIFY_POLL_SECONDS``
(default 10) in a worker thread for the lifetime of the A2A server.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from psycopg import Connection

from sales_common import db
from sales_common.config import ConfigError, env_float

from .delivery import SmtpSettings, send_email
from .templates import render

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
DEDUP_WINDOW_MINUTES = 5
DEFAULT_BATCH = 50
#: Marketing notifications are email-only (no SMS without explicit opt-in).
EMAIL_ONLY_TEMPLATES = {"abandoned_cart"}
_REFERENCE_KEYS = ("quote_id", "cart_id", "order_id")


def _metadata(row: dict) -> tuple[str, dict[str, Any]]:
    """Return ``(template, args)`` from ``metadata_json`` (falls back to the row type)."""
    meta: Any = {}
    raw = row.get("metadata_json")
    if raw:
        try:
            meta = json.loads(raw)
        except ValueError:
            meta = {}
    if not isinstance(meta, dict):
        meta = {}
    args = meta.get("args")
    if not isinstance(args, dict):
        # Legacy rows stored the args at the top level.
        args = {k: v for k, v in meta.items() if k != "template"}
    template = meta.get("template") or row["notification_type"]
    return str(template), args


def _channels(row: dict) -> list[str]:
    try:
        channels = json.loads(row.get("channels_json") or "[]")
    except ValueError:
        channels = []
    if not isinstance(channels, list) or not channels:
        channels = (["email"] if row.get("recipient_email") else []) + (
            ["sms"] if row.get("recipient_phone") else []
        )
    return [str(c) for c in channels]


def dedup_key(row: dict, template: str, args: dict[str, Any]) -> str:
    """``<template>:<recipient>[:<reference>]`` used in ``dedup_cache``."""
    recipient = (row.get("recipient_email") or row.get("recipient_phone") or "").lower()
    parts = [template, recipient]
    ref = next((args.get(k) for k in _REFERENCE_KEYS if args.get(k)), None) or row.get("order_id")
    if ref:
        parts.append(str(ref))
    if template == "order_status_update" and args.get("new_status"):
        parts.append(str(args["new_status"]))
    if template == "payment_confirmation" and args.get("payment_status"):
        parts.append(str(args["payment_status"]).lower())
    return ":".join(parts)


def _is_duplicate(conn: Connection, key: str) -> bool:
    # Serialize dispatchers on this key for the rest of the transaction; a missing
    # dedup_cache row cannot be locked with FOR UPDATE.
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (key,))
    row = conn.execute("SELECT sent_at FROM dedup_cache WHERE dedup_key = %s", (key,)).fetchone()
    if not row:
        return False
    try:
        last = datetime.fromisoformat(row["sent_at"])
    except (TypeError, ValueError):
        return False
    if last.tzinfo is not None:
        last = last.astimezone(timezone.utc).replace(tzinfo=None)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now - last < timedelta(minutes=DEDUP_WINDOW_MINUTES)


def _record_sent(conn: Connection, key: str, now: str) -> None:
    conn.execute(
        "INSERT INTO dedup_cache (dedup_key, sent_at) VALUES (%s, %s) "
        "ON CONFLICT (dedup_key) DO UPDATE SET sent_at = EXCLUDED.sent_at",
        (key, now),
    )


def _deliver(conn: Connection, row: dict, settings: SmtpSettings) -> str:
    """Process one locked pending row. Returns the outcome counter name."""
    nid = row["notification_id"]
    attempts = int(row.get("attempts") or 0) + 1
    now = db.now_iso()
    template, args = _metadata(row)
    try:
        subject, message = render(template, args, order_id=row.get("order_id"))
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        conn.execute(
            "UPDATE notifications SET status='failed', attempts=%s, updated_at=%s, error=%s "
            "WHERE notification_id=%s",
            (attempts, now, f"Render error: {type(exc).__name__}: {exc}", nid),
        )
        logger.error("Notification %s failed to render (%s)", nid, template)
        return "failed"

    key = dedup_key(row, template, args)
    if _is_duplicate(conn, key):
        conn.execute(
            "UPDATE notifications SET status='deduped', subject=%s, message=%s, attempts=%s, "
            "updated_at=%s, error=%s WHERE notification_id=%s",
            (subject, message, attempts, now,
             f"Duplicate: already sent within {DEDUP_WINDOW_MINUTES} minutes", nid),
        )
        logger.info("Notification %s deduplicated (%s)", nid, template)
        return "deduped"

    channels = _channels(row)
    delivered: list[str] = []
    real_email = False
    error: Optional[str] = None

    email = row.get("recipient_email")
    if "email" in channels and email:
        if settings.enabled:
            result = send_email(settings, email, subject, message)
            if result.get("sent"):
                delivered.append("email")
                real_email = True
            else:
                error = str(result.get("detail") or "email delivery failed")
        else:
            logger.info("[SIMULATED] email for notification %s: %s", nid, subject)
            delivered.append("email")

    phone = row.get("recipient_phone")
    if "sms" in channels and phone and template not in EMAIL_ONLY_TEMPLATES and error is None:
        logger.info("[SIMULATED] SMS for notification %s", nid)
        delivered.append("sms")

    if error is not None or not delivered:
        # No deliverable channel (e.g. SMS-only marketing message) cannot succeed on retry.
        permanent = error is None
        error = error or "No deliverable channel for this notification"
        status = "failed" if permanent or attempts >= MAX_ATTEMPTS else "pending"
        conn.execute(
            "UPDATE notifications SET status=%s, subject=%s, message=%s, attempts=%s, "
            "updated_at=%s, error=%s WHERE notification_id=%s",
            (status, subject, message, attempts, now, error, nid),
        )
        logger.warning("Notification %s attempt %d failed (%s)", nid, attempts, status)
        return "failed" if status == "failed" else "retrying"

    status = "sent" if real_email else "simulated"
    conn.execute(
        "UPDATE notifications SET status=%s, subject=%s, message=%s, attempts=%s, "
        "channels_json=%s, sent_at=%s, updated_at=%s, error=NULL WHERE notification_id=%s",
        (status, subject, message, attempts, json.dumps(delivered), now, now, nid),
    )
    _record_sent(conn, key, now)
    logger.info("Notification %s %s via %s", nid, status, ",".join(delivered))
    return status


def retry_seconds() -> float:
    """Base retry backoff (``NOTIFY_RETRY_SECONDS``, default 60, >= 0)."""
    value = env_float("NOTIFY_RETRY_SECONDS", 60.0)
    if value < 0:
        raise ConfigError(f"NOTIFY_RETRY_SECONDS must be >= 0, got {value}")
    return value


def dispatch_pending(limit: int = DEFAULT_BATCH, *, notification_id: Optional[str] = None) -> dict[str, int]:
    """Deliver up to ``limit`` pending notifications in one transaction.

    ``notification_id`` restricts the batch to one row (used by the agent's own
    ``send_*`` tools). Rows locked by another dispatcher are skipped, and rows whose
    retry backoff (``NOTIFY_RETRY_SECONDS * attempts`` since ``updated_at``) has not
    elapsed are left for a later poll.

    Returns counts: ``processed``, ``sent``, ``simulated``, ``deduped``,
    ``retrying`` (failed attempt, will retry) and ``failed`` (gave up).
    """
    counts = {"processed": 0, "sent": 0, "simulated": 0, "deduped": 0, "retrying": 0, "failed": 0}
    limit = max(1, int(limit))
    settings = SmtpSettings.from_env()
    # Timestamps are naive-UTC ISO text (sales_common.db.now_iso).
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    where = (
        "status = 'pending' AND (attempts = 0 OR updated_at IS NULL "
        "OR updated_at::timestamp <= %s::timestamp - make_interval(secs => %s * attempts))"
    )
    params: list[Any] = [now.isoformat(timespec="seconds"), retry_seconds()]
    if notification_id:
        where += " AND notification_id = %s"
        params.append(notification_id)
    params.append(limit)
    with db.transaction() as conn:
        rows = conn.execute(
            f"SELECT * FROM notifications WHERE {where} "
            # Best-effort chronological order; notification_id breaks same-second ties.
            "ORDER BY seq FOR UPDATE SKIP LOCKED LIMIT %s",
            params,
        ).fetchall()
        for row in rows:
            outcome = _deliver(conn, row, settings)
            counts[outcome] += 1
            counts["processed"] += 1
    if counts["processed"]:
        logger.info("dispatch_pending: %s", counts)
    return counts


# ---------------------------------------------------------------------------
# Background loop (started by server.py via create_a2a_app(extra_lifespan=...))
# ---------------------------------------------------------------------------

def poll_seconds() -> float:
    value = env_float("NOTIFY_POLL_SECONDS", 10.0)
    if value <= 0:
        raise ConfigError(f"NOTIFY_POLL_SECONDS must be > 0, got {value}")
    return value


async def run_dispatch_loop(interval: float, stop: asyncio.Event) -> None:
    """Call :func:`dispatch_pending` every ``interval`` seconds until ``stop`` is set."""
    logger.info("Notification dispatcher started (every %.1fs)", interval)
    while not stop.is_set():
        try:
            await asyncio.to_thread(dispatch_pending)
        except Exception:  # keep the loop alive (DB restarts, etc.); retried next poll
            logger.exception("Notification dispatch failed")
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval)
    logger.info("Notification dispatcher stopped")


@contextlib.asynccontextmanager
async def dispatcher_lifespan(_app):
    """Starlette lifespan: run the dispatcher loop while the server is up."""
    SmtpSettings.from_env().validate()
    retry_seconds()  # fail fast on a bad NOTIFY_RETRY_SECONDS
    interval = poll_seconds()
    stop = asyncio.Event()
    task = asyncio.create_task(run_dispatch_loop(interval, stop), name="notification-dispatcher")
    try:
        yield
    finally:
        stop.set()
        try:
            # Let an in-flight batch (running in a thread) finish and commit.
            await asyncio.wait_for(task, timeout=30)
        except asyncio.TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
