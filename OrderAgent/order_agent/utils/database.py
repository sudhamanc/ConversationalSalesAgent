"""
SQLite persistence layer for carts and orders.

Replaces the former in-memory _CARTS / _ORDERS dictionaries so that state
survives process restarts and returning customers can resume their carts and
review previous orders.

Tables
------
carts        – one row per cart (header)
cart_items   – one row per line-item in a cart
orders       – one row per order (header)
order_items  – one row per line-item in an order
"""

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import get_logger

logger = get_logger(__name__)

# Default DB location: OrderAgent/data/orders.db  (sibling of order_agent/ package)
_DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
_DEFAULT_DB_PATH = os.path.join(_DEFAULT_DB_DIR, "orders.db")

# Module-level lock for thread safety
_lock = threading.Lock()


def _get_db_path() -> str:
    db_path = os.getenv("ORDERS_DB_PATH", _DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist.  Safe to call multiple times."""
    with _lock:
        conn = _get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS carts (
                    cart_id       TEXT PRIMARY KEY,
                    customer_id   TEXT NOT NULL,
                    total_amount  REAL NOT NULL DEFAULT 0.0,
                    created_at    TEXT NOT NULL,
                    updated_at    TEXT NOT NULL,
                    expires_at    TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_carts_customer
                    ON carts(customer_id);

                CREATE TABLE IF NOT EXISTS cart_items (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    cart_id       TEXT NOT NULL REFERENCES carts(cart_id) ON DELETE CASCADE,
                    service_type  TEXT NOT NULL,
                    price         REAL NOT NULL,
                    quantity      INTEGER NOT NULL DEFAULT 1,
                    subtotal      REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_cart_items_cart
                    ON cart_items(cart_id);

                CREATE TABLE IF NOT EXISTS orders (
                    order_id       TEXT PRIMARY KEY,
                    customer_name  TEXT NOT NULL,
                    customer_id    TEXT NOT NULL,
                    service_address TEXT NOT NULL,
                    contact_phone  TEXT NOT NULL,
                    contact_email  TEXT,
                    offer_id       TEXT,
                    status         TEXT NOT NULL DEFAULT 'draft',
                    total_amount   REAL NOT NULL DEFAULT 0.0,
                    created_at     TEXT NOT NULL,
                    updated_at     TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_orders_customer
                    ON orders(customer_id);

                CREATE INDEX IF NOT EXISTS idx_orders_offer
                    ON orders(offer_id);

                CREATE TABLE IF NOT EXISTS order_items (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id      TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
                    service_type  TEXT NOT NULL,
                    price         REAL NOT NULL,
                    quantity      INTEGER NOT NULL DEFAULT 1,
                    subtotal      REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_order_items_order
                    ON order_items(order_id);
            """)
            conn.commit()
            logger.info(f"Order/cart database initialised at {_get_db_path()}")
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Cart persistence helpers
# ---------------------------------------------------------------------------

def save_cart(cart: Dict[str, Any]) -> None:
    """Insert or replace a cart (header + items)."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO carts
                   (cart_id, customer_id, total_amount, created_at, updated_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    cart["cart_id"],
                    cart["customer_id"],
                    cart["total_amount"],
                    cart["created_at"],
                    cart["updated_at"],
                    cart.get("expires_at"),
                ),
            )
            # Replace items: delete old, insert current
            conn.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart["cart_id"],))
            for item in cart.get("items", []):
                conn.execute(
                    """INSERT INTO cart_items (cart_id, service_type, price, quantity, subtotal)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        cart["cart_id"],
                        item["service_type"],
                        item["price"],
                        item["quantity"],
                        item["subtotal"],
                    ),
                )
            conn.commit()
        finally:
            conn.close()


def load_cart(cart_id: str) -> Optional[Dict[str, Any]]:
    """Return a cart dict or None."""
    with _lock:
        conn = _get_connection()
        try:
            row = conn.execute("SELECT * FROM carts WHERE cart_id = ?", (cart_id,)).fetchone()
            if not row:
                return None
            cart = {
                "cart_id": row["cart_id"],
                "customer_id": row["customer_id"],
                "total_amount": row["total_amount"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "expires_at": row["expires_at"],
                "items": [],
            }
            items = conn.execute(
                "SELECT service_type, price, quantity, subtotal FROM cart_items WHERE cart_id = ?",
                (cart_id,),
            ).fetchall()
            cart["items"] = [
                {"service_type": r["service_type"], "price": r["price"], "quantity": r["quantity"], "subtotal": r["subtotal"]}
                for r in items
            ]
            return cart
        finally:
            conn.close()


def load_carts_for_customer(customer_id: str) -> List[Dict[str, Any]]:
    """Return all carts for a given customer (for returning-customer lookup)."""
    with _lock:
        conn = _get_connection()
        try:
            rows = conn.execute(
                "SELECT cart_id FROM carts WHERE customer_id = ? ORDER BY updated_at DESC",
                (customer_id,),
            ).fetchall()
            cart_ids = [r["cart_id"] for r in rows]
        finally:
            conn.close()
    # load_cart acquires its own lock, so release first
    return [c for cid in cart_ids if (c := load_cart(cid)) is not None]


def delete_cart(cart_id: str) -> None:
    """Remove a cart and its items (e.g. after order submission)."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart_id,))
            conn.execute("DELETE FROM carts WHERE cart_id = ?", (cart_id,))
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Order persistence helpers
# ---------------------------------------------------------------------------

def save_order(order_dict: Dict[str, Any]) -> None:
    """Insert or replace an order (header + items)."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO orders
                   (order_id, customer_name, customer_id, service_address,
                    contact_phone, contact_email, offer_id, status,
                    total_amount, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    order_dict["order_id"],
                    order_dict["customer_name"],
                    order_dict["customer_id"],
                    order_dict["service_address"],
                    order_dict["contact_phone"],
                    order_dict.get("contact_email"),
                    order_dict.get("offer_id"),
                    order_dict["status"],
                    order_dict["total_amount"],
                    order_dict["created_at"],
                    order_dict["updated_at"],
                ),
            )
            conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_dict["order_id"],))
            for item in order_dict.get("items", []):
                conn.execute(
                    """INSERT INTO order_items (order_id, service_type, price, quantity, subtotal)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        order_dict["order_id"],
                        item["service_type"],
                        item["price"],
                        item["quantity"],
                        item["subtotal"],
                    ),
                )
            conn.commit()
        finally:
            conn.close()


def load_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Return an order dict or None."""
    with _lock:
        conn = _get_connection()
        try:
            row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            if not row:
                return None
            order = {k: row[k] for k in row.keys()}
            items = conn.execute(
                "SELECT service_type, price, quantity, subtotal FROM order_items WHERE order_id = ?",
                (order_id,),
            ).fetchall()
            order["items"] = [
                {"service_type": r["service_type"], "price": r["price"], "quantity": r["quantity"], "subtotal": r["subtotal"]}
                for r in items
            ]
            return order
        finally:
            conn.close()


def load_orders_for_customer(customer_id: str) -> List[Dict[str, Any]]:
    """Return all orders for a customer, newest first."""
    with _lock:
        conn = _get_connection()
        try:
            rows = conn.execute(
                "SELECT order_id FROM orders WHERE customer_id = ? ORDER BY created_at DESC",
                (customer_id,),
            ).fetchall()
            order_ids = [r["order_id"] for r in rows]
        finally:
            conn.close()
    return [o for oid in order_ids if (o := load_order(oid)) is not None]


def update_order_field(order_id: str, **fields) -> bool:
    """Update one or more columns on the orders table.  Returns True if row existed."""
    if not fields:
        return False
    allowed = {
        "customer_name", "customer_id", "service_address", "contact_phone",
        "contact_email", "offer_id", "status", "total_amount", "updated_at",
    }
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"Cannot update fields: {bad}")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [order_id]
    with _lock:
        conn = _get_connection()
        try:
            cur = conn.execute(f"UPDATE orders SET {set_clause} WHERE order_id = ?", values)
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# Auto-initialise on import so callers don't need to remember
init_db()
