"""
SQLite persistence for notifications.

Stores notifications and deduplication state so they survive process restarts.
Database file location controlled by NOTIFICATION_DB_PATH env var
(defaults to ``data/notifications.db`` relative to the repo root).
"""

import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .logger import get_logger

logger = get_logger(__name__)

_DEFAULT_DB_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data",
)
_DB_PATH = os.getenv(
    "NOTIFICATION_DB_PATH",
    os.path.join(_DEFAULT_DB_DIR, "notifications.db"),
)

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Return a thread-local SQLite connection (created on first access)."""
    conn: Optional[sqlite3.Connection] = getattr(_local, "conn", None)
    if conn is None:
        db_dir = os.path.dirname(_DB_PATH)
        if db_dir and _DB_PATH != ":memory:":
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        if _DB_PATH != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
        _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id   TEXT PRIMARY KEY,
            notification_type TEXT NOT NULL,
            recipient_email   TEXT,
            recipient_phone   TEXT,
            subject           TEXT,
            message           TEXT,
            metadata_json     TEXT,
            status            TEXT NOT NULL DEFAULT 'pending',
            channels_json     TEXT NOT NULL DEFAULT '[]',
            created_at        TEXT NOT NULL,
            sent_at           TEXT,
            error             TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_notif_email
            ON notifications(recipient_email);
        CREATE INDEX IF NOT EXISTS idx_notif_phone
            ON notifications(recipient_phone);
        CREATE INDEX IF NOT EXISTS idx_notif_type
            ON notifications(notification_type);

        CREATE TABLE IF NOT EXISTS dedup_cache (
            dedup_key  TEXT PRIMARY KEY,
            sent_at    TEXT NOT NULL
        );
    """)
    conn.commit()


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def store_notification(
    notification_id: str,
    notification_type: str,
    recipient_email: Optional[str],
    recipient_phone: Optional[str],
    subject: str,
    message: str,
    metadata: Optional[Dict[str, Any]],
    status: str,
    channels: List[str],
    created_at: str,
    sent_at: Optional[str],
    error: Optional[str],
) -> None:
    """Persist a notification record (insert or replace)."""
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO notifications
            (notification_id, notification_type, recipient_email, recipient_phone,
             subject, message, metadata_json, status, channels_json,
             created_at, sent_at, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            notification_id,
            notification_type,
            recipient_email,
            recipient_phone,
            subject,
            message,
            json.dumps(metadata) if metadata else "{}",
            status,
            json.dumps(channels),
            created_at,
            sent_at,
            error,
        ),
    )
    conn.commit()


def check_duplicate(notification_type: str, recipient: str, window_minutes: int = 5) -> bool:
    """Return True if a notification of this type was sent to recipient within *window_minutes*."""
    conn = _get_conn()
    dedup_key = f"{notification_type}:{recipient}"
    row = conn.execute(
        "SELECT sent_at FROM dedup_cache WHERE dedup_key = ?", (dedup_key,)
    ).fetchone()
    if row:
        last_sent = datetime.fromisoformat(row["sent_at"])
        if datetime.now() - last_sent < timedelta(minutes=window_minutes):
            logger.warning(f"Duplicate notification blocked: {dedup_key}")
            return True
    # Upsert
    conn.execute(
        "INSERT OR REPLACE INTO dedup_cache (dedup_key, sent_at) VALUES (?, ?)",
        (dedup_key, datetime.now().isoformat()),
    )
    conn.commit()
    return False


def get_history(
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    notification_type: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Retrieve notification history filtered by email/phone/type."""
    conn = _get_conn()
    clauses: List[str] = []
    params: List[Any] = []

    if customer_email:
        clauses.append("recipient_email = ?")
        params.append(customer_email)
    if customer_phone:
        clauses.append("recipient_phone = ?")
        params.append(customer_phone)
    if notification_type:
        clauses.append("notification_type = ?")
        params.append(notification_type)

    where = " AND ".join(clauses) if clauses else "1=1"
    params.append(limit)

    rows = conn.execute(
        f"SELECT * FROM notifications WHERE {where} ORDER BY created_at DESC LIMIT ?",
        params,
    ).fetchall()

    results = []
    for row in rows:
        results.append({
            "notification_id": row["notification_id"],
            "notification_type": row["notification_type"],
            "recipient_email": row["recipient_email"],
            "recipient_phone": row["recipient_phone"],
            "subject": row["subject"],
            "message": row["message"],
            "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            "status": row["status"],
            "channels": json.loads(row["channels_json"]) if row["channels_json"] else [],
            "created_at": row["created_at"],
            "sent_at": row["sent_at"],
            "error": row["error"],
        })
    return results


def clear_all() -> None:
    """Delete all rows – useful for testing."""
    conn = _get_conn()
    conn.execute("DELETE FROM notifications")
    conn.execute("DELETE FROM dedup_cache")
    conn.commit()
