"""
PostgreSQL persistence for carts and orders (``sales_common.db``).

Tables (schema in ``db/migrations/001_sales_schema.sql``; never created here)
------
carts        - one row per cart (header)
cart_items   - one row per line-item in a cart
orders       - one row per order (header)
order_items  - one row per line-item in an order

Every function accepts an optional ``conn`` so callers can join an existing
``sales_common.db.transaction()``; otherwise each call runs in its own
transaction.
"""

from __future__ import annotations

from contextlib import contextmanager
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional

from psycopg import Connection

from sales_common import db

from .logger import get_logger

logger = get_logger(__name__)


@contextmanager
def _tx(conn: Optional[Connection]) -> Iterator[Connection]:
    if conn is not None:
        yield conn
    else:
        with db.transaction() as own:
            yield own


def _plain(value: Any) -> Any:
    """Enum members (e.g. ``OrderStatus``) are stored by value."""
    return value.value if isinstance(value, Enum) else value


def _item(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "service_type": row["service_type"],
        "price": row["price"],
        "quantity": row["quantity"],
        "subtotal": row["subtotal"],
    }


# ---------------------------------------------------------------------------
# Cart persistence helpers
# ---------------------------------------------------------------------------

def save_cart(cart: Dict[str, Any], conn: Optional[Connection] = None) -> None:
    """Upsert a cart header and replace its items."""
    with _tx(conn) as c:
        c.execute(
            """INSERT INTO carts
                   (cart_id, customer_id, total_amount, status, created_at, updated_at, expires_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (cart_id) DO UPDATE SET
                   customer_id  = EXCLUDED.customer_id,
                   total_amount = EXCLUDED.total_amount,
                   status       = EXCLUDED.status,
                   created_at   = EXCLUDED.created_at,
                   updated_at   = EXCLUDED.updated_at,
                   expires_at   = EXCLUDED.expires_at""",
            (
                cart["cart_id"],
                cart["customer_id"],
                cart["total_amount"],
                cart.get("status", "active"),
                cart["created_at"],
                cart["updated_at"],
                cart.get("expires_at"),
            ),
        )
        c.execute("DELETE FROM cart_items WHERE cart_id = %s", (cart["cart_id"],))
        for item in cart.get("items", []):
            c.execute(
                """INSERT INTO cart_items (cart_id, service_type, price, quantity, subtotal)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (cart["cart_id"], item["service_type"], item["price"], item["quantity"], item["subtotal"]),
            )


def load_cart(cart_id: str, conn: Optional[Connection] = None) -> Optional[Dict[str, Any]]:
    """Return a cart dict (with ``items``) or None."""
    with _tx(conn) as c:
        row = c.execute("SELECT * FROM carts WHERE cart_id = %s", (cart_id,)).fetchone()
        if not row:
            return None
        items = c.execute(
            "SELECT service_type, price, quantity, subtotal FROM cart_items WHERE cart_id = %s ORDER BY id",
            (cart_id,),
        ).fetchall()
    return {
        "cart_id": row["cart_id"],
        "customer_id": row["customer_id"],
        "total_amount": row["total_amount"],
        "status": row["status"] or "active",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "expires_at": row["expires_at"],
        "items": [_item(r) for r in items],
    }


def load_carts_for_customer(customer_id: str) -> List[Dict[str, Any]]:
    """Return all carts for a given customer (for returning-customer lookup)."""
    with db.transaction() as c:
        rows = c.execute(
            "SELECT cart_id FROM carts WHERE customer_id = %s ORDER BY updated_at DESC",
            (customer_id,),
        ).fetchall()
        return [cart for r in rows if (cart := load_cart(r["cart_id"], conn=c)) is not None]


def delete_cart(cart_id: str, conn: Optional[Connection] = None) -> None:
    """Remove a cart and its items (e.g. after order submission)."""
    with _tx(conn) as c:
        c.execute("DELETE FROM cart_items WHERE cart_id = %s", (cart_id,))
        c.execute("DELETE FROM carts WHERE cart_id = %s", (cart_id,))


# ---------------------------------------------------------------------------
# Order persistence helpers
# ---------------------------------------------------------------------------

def save_order(order_dict: Dict[str, Any], conn: Optional[Connection] = None) -> None:
    """Upsert an order header and replace its items."""
    with _tx(conn) as c:
        c.execute(
            """INSERT INTO orders
                   (order_id, customer_name, customer_id, service_address,
                    contact_phone, contact_email, offer_id, status,
                    total_amount, created_at, updated_at, expires_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (order_id) DO UPDATE SET
                   customer_name   = EXCLUDED.customer_name,
                   customer_id     = EXCLUDED.customer_id,
                   service_address = EXCLUDED.service_address,
                   contact_phone   = EXCLUDED.contact_phone,
                   contact_email   = EXCLUDED.contact_email,
                   offer_id        = EXCLUDED.offer_id,
                   status          = EXCLUDED.status,
                   total_amount    = EXCLUDED.total_amount,
                   created_at      = EXCLUDED.created_at,
                   updated_at      = EXCLUDED.updated_at,
                   expires_at      = EXCLUDED.expires_at""",
            (
                order_dict["order_id"],
                order_dict["customer_name"],
                order_dict["customer_id"],
                order_dict["service_address"],
                order_dict["contact_phone"],
                order_dict.get("contact_email"),
                order_dict.get("offer_id"),
                _plain(order_dict["status"]),
                order_dict["total_amount"],
                order_dict["created_at"],
                order_dict["updated_at"],
                order_dict.get("expires_at"),
            ),
        )
        c.execute("DELETE FROM order_items WHERE order_id = %s", (order_dict["order_id"],))
        for item in order_dict.get("items", []):
            c.execute(
                """INSERT INTO order_items (order_id, service_type, price, quantity, subtotal)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (order_dict["order_id"], item["service_type"], item["price"], item["quantity"], item["subtotal"]),
            )


def load_order(order_id: str, conn: Optional[Connection] = None) -> Optional[Dict[str, Any]]:
    """Return an order dict (with ``items``) or None."""
    with _tx(conn) as c:
        row = c.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,)).fetchone()
        if not row:
            return None
        items = c.execute(
            "SELECT service_type, price, quantity, subtotal FROM order_items WHERE order_id = %s ORDER BY id",
            (order_id,),
        ).fetchall()
    order = dict(row)
    order["items"] = [_item(r) for r in items]
    return order


def load_orders_for_customer(customer_id: str) -> List[Dict[str, Any]]:
    """Return all orders for a customer, newest first."""
    with db.transaction() as c:
        rows = c.execute(
            "SELECT order_id FROM orders WHERE customer_id = %s ORDER BY created_at DESC",
            (customer_id,),
        ).fetchall()
        return [o for r in rows if (o := load_order(r["order_id"], conn=c)) is not None]


_UPDATABLE = {
    "customer_name", "customer_id", "service_address", "contact_phone",
    "contact_email", "offer_id", "status", "total_amount", "updated_at",
    "expires_at",
}


def update_order_field(order_id: str, conn: Optional[Connection] = None, **fields) -> bool:
    """Update one or more columns on the orders table. Returns True if the row existed."""
    if not fields:
        return False
    bad = set(fields) - _UPDATABLE
    if bad:
        raise ValueError(f"Cannot update fields: {bad}")
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = [_plain(v) for v in fields.values()] + [order_id]
    with _tx(conn) as c:
        return c.execute(f"UPDATE orders SET {set_clause} WHERE order_id = %s", values).rowcount > 0


def quote_exists(offer_id: str, conn: Optional[Connection] = None) -> bool:
    """True when ``offer_id`` exists in ``quotes`` (``orders.offer_id`` is a foreign key)."""
    with _tx(conn) as c:
        return c.execute("SELECT 1 FROM quotes WHERE offer_id = %s", (offer_id,)).fetchone() is not None
