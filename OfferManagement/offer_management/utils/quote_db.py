"""
SQLite persistence for saved quotes.

Database file location controlled by QUOTE_DB_PATH env var
(defaults to ``data/quotes.db`` relative to the OfferManagement package root).
"""

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from .logger import get_logger

logger = get_logger(__name__)

_DEFAULT_DB_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data",
)
_DB_PATH = os.getenv(
    "QUOTE_DB_PATH",
    os.path.join(_DEFAULT_DB_DIR, "quotes.db"),
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
        CREATE TABLE IF NOT EXISTS quotes (
            quote_id       TEXT PRIMARY KEY,
            offer_id       TEXT NOT NULL,
            customer_name  TEXT,
            customer_email TEXT,
            customer_phone TEXT,
            items_json     TEXT NOT NULL,
            term_months    INTEGER NOT NULL DEFAULT 12,
            bant_score     REAL NOT NULL DEFAULT 0.0,
            subtotal       REAL NOT NULL,
            total_discount REAL NOT NULL DEFAULT 0.0,
            monthly_total  REAL NOT NULL,
            yearly_total   REAL NOT NULL,
            discount_breakdown_json TEXT,
            status         TEXT NOT NULL DEFAULT 'active',
            created_at     TEXT NOT NULL,
            expires_at     TEXT,
            converted_order_id TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_quote_email
            ON quotes(customer_email);
        CREATE INDEX IF NOT EXISTS idx_quote_status
            ON quotes(status);
    """)
    conn.commit()


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def insert_quote(
    quote_id: str,
    offer_id: str,
    customer_name: str,
    customer_email: Optional[str],
    customer_phone: Optional[str],
    items: List[Dict[str, Any]],
    term_months: int,
    bant_score: float,
    subtotal: float,
    total_discount: float,
    monthly_total: float,
    yearly_total: float,
    discount_breakdown: List[Dict[str, Any]],
    created_at: str,
    expires_at: str,
) -> None:
    """Persist a new quote row."""
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO quotes
            (quote_id, offer_id, customer_name, customer_email, customer_phone,
             items_json, term_months, bant_score, subtotal, total_discount,
             monthly_total, yearly_total, discount_breakdown_json,
             status, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """,
        (
            quote_id,
            offer_id,
            customer_name,
            customer_email,
            customer_phone,
            json.dumps(items),
            term_months,
            bant_score,
            subtotal,
            total_discount,
            monthly_total,
            yearly_total,
            json.dumps(discount_breakdown),
            created_at,
            expires_at,
        ),
    )
    conn.commit()


def get_quote(quote_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single quote by ID."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def list_quotes_by_email(email: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve quotes for a customer email."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM quotes WHERE customer_email = ? ORDER BY created_at DESC LIMIT ?",
        (email, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def mark_quote_converted(quote_id: str, order_id: str) -> bool:
    """Mark a quote as converted to an order."""
    conn = _get_conn()
    cur = conn.execute(
        "UPDATE quotes SET status = 'converted', converted_order_id = ? WHERE quote_id = ?",
        (order_id, quote_id),
    )
    conn.commit()
    return cur.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "quote_id": row["quote_id"],
        "offer_id": row["offer_id"],
        "customer_name": row["customer_name"],
        "customer_email": row["customer_email"],
        "customer_phone": row["customer_phone"],
        "items": json.loads(row["items_json"]) if row["items_json"] else [],
        "term_months": row["term_months"],
        "bant_score": row["bant_score"],
        "subtotal": row["subtotal"],
        "total_discount": row["total_discount"],
        "monthly_total": row["monthly_total"],
        "yearly_total": row["yearly_total"],
        "discount_breakdown": json.loads(row["discount_breakdown_json"]) if row["discount_breakdown_json"] else [],
        "status": row["status"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "converted_order_id": row["converted_order_id"],
    }


def clear_all() -> None:
    """Delete all rows – useful for testing."""
    conn = _get_conn()
    conn.execute("DELETE FROM quotes")
    conn.commit()
