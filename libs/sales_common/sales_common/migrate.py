"""Versioned SQL migrations and seed loader.

Usage::

    python -m sales_common.migrate            # migrate only
    python -m sales_common.migrate --seed     # migrate, then load seed files once

Files are applied in lexical order from ``<DB_DIR>/migrations/*.sql`` and
``<DB_DIR>/seed/*.sql``. Applied versions are recorded in ``schema_migrations``
and ``seed_versions`` so re-runs are no-ops. Without ``DB_DIR`` the first
``db/`` directory found walking up from the current working directory is used,
then walking up from the installed package (editable install in the repo),
then ``/app/db`` (see ``find_db_dir``).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import psycopg

from .db import database_url
from .logging import mask_url, setup_logging

logger = logging.getLogger("sales_common.migrate")

_LOCK_ID = 7_402_113  # arbitrary advisory-lock key shared by all runners


def _walk_up_for_db(start: Path) -> Optional[Path]:
    for candidate in [start, *start.parents]:
        if (candidate / "db" / "migrations").is_dir():
            return candidate / "db"
    return None


def find_db_dir() -> Path:
    """Locate the ``db/`` directory (``migrations/`` + ``seed/``).

    Order: ``DB_DIR`` env override, walk up from the current working directory,
    walk up from this package's location (editable installs live inside the
    repo), then ``/app/db`` (container images).
    """
    explicit = os.getenv("DB_DIR", "").strip()
    if explicit:
        path = Path(explicit)
        if not (path / "migrations").is_dir():
            raise FileNotFoundError(f"DB_DIR={explicit} has no migrations/ directory")
        return path
    for start in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        found = _walk_up_for_db(start)
        if found is not None:
            return found
    container = Path("/app/db")
    if (container / "migrations").is_dir():
        return container
    raise FileNotFoundError("Could not locate db/migrations; set DB_DIR")


def _apply(conn: psycopg.Connection, table: str, files: list[Path]) -> list[str]:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {table} ("
        " version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    done = {row[0] for row in conn.execute(f"SELECT version FROM {table}").fetchall()}
    applied = []
    for path in files:
        if path.name in done:
            continue
        logger.info("Applying %s/%s", path.parent.name, path.name)
        with conn.transaction():
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute(f"INSERT INTO {table} (version) VALUES (%s)", (path.name,))
        applied.append(path.name)
    return applied


def run(seed: bool = False, db_dir: Path | None = None) -> dict[str, list[str]]:
    """Apply pending migrations (and seeds when ``seed``). Returns applied file names."""
    db_dir = db_dir or find_db_dir()
    url = database_url()
    logger.info("Migrating %s using %s", mask_url(url), db_dir)
    result = {"migrations": [], "seeds": []}
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_ID,))
        try:
            result["migrations"] = _apply(
                conn, "schema_migrations", sorted((db_dir / "migrations").glob("*.sql"))
            )
            if seed and (db_dir / "seed").is_dir():
                result["seeds"] = _apply(conn, "seed_versions", sorted((db_dir / "seed").glob("*.sql")))
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply sales DB migrations")
    parser.add_argument("--seed", action="store_true", help="also load seed files")
    args = parser.parse_args(argv)
    setup_logging("db-migrate")
    result = run(seed=args.seed)
    logger.info(
        "Applied %d migration(s), %d seed file(s)", len(result["migrations"]), len(result["seeds"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
