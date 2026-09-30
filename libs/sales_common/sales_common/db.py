"""PostgreSQL access for deterministic agent tools (psycopg 3, sync).

ADK runs synchronous tools in worker threads, so a thread-safe connection pool
is used. ``DATABASE_URL`` is a libpq URL (``postgresql://user:pw@host:5432/db``);
on Cloud Run use ``postgresql://user:pw@/db?host=/cloudsql/PROJECT:REGION:INSTANCE``.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator, Optional, Sequence

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import env_int, require_env
from .logging import mask_url

logger = logging.getLogger("sales_common.db")

_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def database_url() -> str:
    """libpq URL for business data. Accepts SQLAlchemy-style ``postgresql+driver://``."""
    url = require_env("DATABASE_URL")
    if url.startswith("postgresql+"):
        url = "postgresql://" + url.split("://", 1)[1]
    return url


def session_db_url() -> str:
    """SQLAlchemy async URL for ADK sessions / A2A tasks.

    Uses ``SESSION_DB_URL`` when set, else derives ``postgresql+asyncpg://`` from
    ``DATABASE_URL``. A ``?host=/cloudsql/...`` socket parameter is preserved.
    """
    import os

    explicit = os.getenv("SESSION_DB_URL", "").strip()
    if explicit:
        return explicit
    url = database_url()
    return "postgresql+asyncpg://" + url.split("://", 1)[1]


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                url = database_url()
                _pool = ConnectionPool(
                    conninfo=url,
                    min_size=1,
                    max_size=env_int("DB_POOL_MAX", 5),
                    kwargs={"row_factory": dict_row, "autocommit": False},
                    open=True,
                    name="sales_common",
                )
                logger.info("PostgreSQL pool opened for %s", mask_url(url))
    return _pool


def close_pool() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


@contextmanager
def transaction() -> Iterator[Connection]:
    """Yield a pooled connection inside a transaction (commit on success, rollback on error)."""
    with get_pool().connection() as conn:
        with conn.transaction():
            yield conn


def fetch_one(sql: str, params: Sequence[Any] | dict | None = None) -> Optional[dict]:
    with transaction() as conn:
        return conn.execute(sql, params).fetchone()


def fetch_all(sql: str, params: Sequence[Any] | dict | None = None) -> list[dict]:
    with transaction() as conn:
        return list(conn.execute(sql, params).fetchall())


def execute(sql: str, params: Sequence[Any] | dict | None = None) -> int:
    """Execute a statement; return affected row count."""
    with transaction() as conn:
        return conn.execute(sql, params).rowcount


def ping() -> bool:
    """Return True when the database answers ``SELECT 1``."""
    try:
        return fetch_one("SELECT 1 AS ok") is not None
    except Exception as exc:  # health checks must not raise
        logger.warning("Database ping failed: %s", type(exc).__name__)
        return False


# ---------------------------------------------------------------------------
# Time helpers (timestamps are stored as ISO-8601 TEXT, UTC, second precision)
# ---------------------------------------------------------------------------

QUOTE_EXPIRY_DAYS = 30
CART_EXPIRY_HOURS = 24
ORDER_EXPIRY_HOURS = 48
PAYMENT_EXPIRY_MINUTES = 15
ESCALATION_DAYS = 7


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def compute_expires_at(created_at: str, entity: str) -> str:
    """ISO-8601 ``expires_at`` for ``quote`` | ``cart`` | ``order`` | ``payment``."""
    dt = datetime.fromisoformat(created_at)
    deltas = {
        "quote": timedelta(days=QUOTE_EXPIRY_DAYS),
        "cart": timedelta(hours=CART_EXPIRY_HOURS),
        "order": timedelta(hours=ORDER_EXPIRY_HOURS),
        "payment": timedelta(minutes=PAYMENT_EXPIRY_MINUTES),
    }
    if entity not in deltas:
        raise ValueError(f"Unknown entity type: {entity!r}")
    return (dt + deltas[entity]).isoformat(timespec="seconds")
