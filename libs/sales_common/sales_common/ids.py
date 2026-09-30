"""Identifier helpers.

Python's built-in ``hash()`` is salted per process, so IDs derived from it are
neither stable across restarts/replicas nor collision-safe. Use these instead.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone


def new_id(prefix: str, *, timestamp_format: str = "%Y%m%d", random_hex: int = 8) -> str:
    """Unique, human-readable id: ``<PREFIX>-<UTC timestamp>-<random hex>``.

    >>> new_id("ORD")  # doctest: +SKIP
    'ORD-20260930-9F2C41AB'
    """
    stamp = datetime.now(timezone.utc).strftime(timestamp_format)
    return f"{prefix}-{stamp}-{secrets.token_hex(random_hex // 2 or 1).upper()}"


def stable_number(value: str, modulo: int) -> int:
    """Deterministic, process-independent number in ``[0, modulo)`` for ``value``."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo
