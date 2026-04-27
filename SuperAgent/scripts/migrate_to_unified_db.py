#!/usr/bin/env python3
"""
One-time migration: copy Discovery data from ``discover_prospecting_clean.db``
into the unified ``sales_agent.db``, generating ``customer_id`` for every
existing account row.

Usage
-----
    python3 SuperAgent/scripts/migrate_to_unified_db.py [--source PATH] [--target PATH]

Defaults:
    --source  DiscoveryAgent/data/discover_prospecting_clean.db
    --target  SuperAgent/data/sales_agent.db

The script is **idempotent**: it skips accounts that already have a
``customer_id`` in the target database.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone

# Ensure SuperAgent package is importable
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SUPER_AGENT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _SUPER_AGENT_ROOT)


def _resolve_default_source() -> str:
    """Return the default Discovery DB path relative to the repo root."""
    repo_root = os.path.dirname(_SUPER_AGENT_ROOT)
    return os.path.join(repo_root, "DiscoveryAgent", "data", "discover_prospecting_clean.db")


def _resolve_default_target() -> str:
    """Return the default unified DB path."""
    return os.path.join(_SUPER_AGENT_ROOT, "data", "sales_agent.db")


def _generate_customer_id(index: int) -> str:
    """Generate a customer_id in the format ``CUST-YYYYMMDD-XXX``."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"CUST-{today}-{index:03d}"


# Tables to migrate (skip accounts_backup and any other non-standard tables)
_DISCOVERY_TABLES = ["accounts", "contacts", "spend", "opportunities", "insights", "actions"]


def migrate(source_path: str, target_path: str, *, dry_run: bool = False) -> dict:
    """Migrate Discovery data from *source_path* into *target_path*.

    Parameters
    ----------
    source_path : str
        Path to ``discover_prospecting_clean.db``.
    target_path : str
        Path to ``sales_agent.db`` (will be created via ``init_db()`` if missing).
    dry_run : bool
        If True, print what would happen but don't write.

    Returns
    -------
    dict
        Counts of rows migrated per table, plus customer_ids generated.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source database not found: {source_path}")

    # Ensure target schema exists
    os.environ["SALES_AGENT_DB_PATH"] = target_path

    # Import after setting env var so database.py picks up the path
    import importlib.util
    db_spec = importlib.util.spec_from_file_location(
        "database",
        os.path.join(_SUPER_AGENT_ROOT, "super_agent", "utils", "database.py"),
    )
    db_mod = importlib.util.module_from_spec(db_spec)
    db_spec.loader.exec_module(db_mod)
    db_mod.init_db()

    src = sqlite3.connect(source_path)
    src.row_factory = sqlite3.Row
    tgt = db_mod.get_connection()

    counts = {table: 0 for table in _DISCOVERY_TABLES}
    counts["customer_ids_generated"] = 0

    now = datetime.now(timezone.utc).isoformat()

    try:
        # --- 1. Migrate accounts (with customer_id generation) ---
        existing_companies = {
            row[0]
            for row in tgt.execute('SELECT "Company Name" FROM accounts').fetchall()
        }

        src_accounts = src.execute("SELECT * FROM accounts").fetchall()
        col_names = [desc[0] for desc in src.execute("SELECT * FROM accounts LIMIT 0").description]

        # Find the next customer_id index (in case of partial migration)
        max_idx_row = tgt.execute(
            "SELECT customer_id FROM accounts WHERE customer_id IS NOT NULL "
            "ORDER BY customer_id DESC LIMIT 1"
        ).fetchone()
        next_idx = 1
        if max_idx_row and max_idx_row[0]:
            try:
                next_idx = int(max_idx_row[0].split("-")[-1]) + 1
            except (ValueError, IndexError):
                next_idx = len(existing_companies) + 1

        for row in src_accounts:
            company = row["Company Name"]
            if company in existing_companies:
                continue  # Already migrated

            cust_id = _generate_customer_id(next_idx)
            next_idx += 1

            # Build INSERT with all original columns + new columns
            values = {col: row[col] for col in col_names}
            values["customer_id"] = cust_id
            values["created_at"] = now
            values["updated_at"] = now

            placeholders = ", ".join(["?"] * len(values))
            cols = ", ".join([f'"{k}"' for k in values.keys()])

            if not dry_run:
                tgt.execute(
                    f"INSERT INTO accounts ({cols}) VALUES ({placeholders})",
                    tuple(values.values()),
                )

            counts["accounts"] += 1
            counts["customer_ids_generated"] += 1

        # --- 2. Migrate contacts ---
        existing_contacts = set()
        for r in tgt.execute('SELECT "Company Name", "Name" FROM contacts').fetchall():
            existing_contacts.add((r[0], r[1]))

        src_contacts = src.execute("SELECT * FROM contacts").fetchall()
        contact_cols = [desc[0] for desc in src.execute("SELECT * FROM contacts LIMIT 0").description]

        for row in src_contacts:
            key = (row["Company Name"], row["Name"])
            if key in existing_contacts:
                continue

            values = {col: row[col] for col in contact_cols}
            values["created_at"] = now

            placeholders = ", ".join(["?"] * len(values))
            cols = ", ".join([f'"{k}"' for k in values.keys()])

            if not dry_run:
                tgt.execute(
                    f"INSERT INTO contacts ({cols}) VALUES ({placeholders})",
                    tuple(values.values()),
                )
            counts["contacts"] += 1

        # --- 3-6. Migrate spend, opportunities, insights, actions ---
        for table in ["spend", "opportunities", "insights", "actions"]:
            src_rows = src.execute(f"SELECT * FROM {table}").fetchall()
            src_cols = [
                desc[0] for desc in src.execute(f"SELECT * FROM {table} LIMIT 0").description
            ]

            # Check existing rows by Company Name
            existing_keys = {
                r[0] for r in tgt.execute(f'SELECT "Company Name" FROM {table}').fetchall()
            }

            for row in src_rows:
                company = row["Company Name"]
                if company in existing_keys:
                    continue

                values = {col: row[col] for col in src_cols}

                # Add date columns for tables that have them in unified schema
                if table == "opportunities":
                    values["created_at"] = now
                    values["updated_at"] = now

                placeholders = ", ".join(["?"] * len(values))
                cols = ", ".join([f'"{k}"' for k in values.keys()])

                if not dry_run:
                    tgt.execute(
                        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                        tuple(values.values()),
                    )
                counts[table] += 1

            # For tables with multiple rows per company (opportunities),
            # mark those already migrated so we don't double-count
            existing_keys.update(
                row["Company Name"] for row in src_rows
            )

        if not dry_run:
            tgt.commit()

    finally:
        src.close()
        tgt.close()

    return counts


def main():
    parser = argparse.ArgumentParser(description="Migrate Discovery data to unified sales_agent.db")
    parser.add_argument("--source", default=_resolve_default_source(),
                        help="Path to discover_prospecting_clean.db")
    parser.add_argument("--target", default=_resolve_default_target(),
                        help="Path to sales_agent.db")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without writing")
    args = parser.parse_args()

    print(f"Source: {args.source}")
    print(f"Target: {args.target}")
    if args.dry_run:
        print("DRY RUN — no writes will be performed")
    print()

    counts = migrate(args.source, args.target, dry_run=args.dry_run)

    print("Migration results:")
    for table, count in counts.items():
        print(f"  {table:30s} {count:>5d} rows")
    print()
    print("Done." if not args.dry_run else "Dry run complete (no changes made).")


if __name__ == "__main__":
    main()
