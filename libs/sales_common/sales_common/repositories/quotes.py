"""Quote status helpers (replaces Order -> Offer ``sys.modules`` call)."""

from __future__ import annotations

from typing import Optional

from psycopg import Connection

from ..db import now_iso, transaction


def mark_ordered(offer_id: str, conn: Optional[Connection] = None) -> bool:
    """Mark a quote as ordered. Returns True when a row was updated."""
    sql = "UPDATE quotes SET status = 'ordered', updated_at = %s WHERE offer_id = %s"
    params = (now_iso(), offer_id)
    if conn is not None:
        return conn.execute(sql, params).rowcount > 0
    with transaction() as own:
        return own.execute(sql, params).rowcount > 0
