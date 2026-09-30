"""PostgreSQL access for the ``products`` table (migration 002)."""

from __future__ import annotations

from typing import Optional

from sales_common import db

from .models import ProductRecord

_COLUMNS = (
    "product_id, product_name, category, technology, speeds, description, features, "
    "available, unit_price::float8 AS unit_price, family, sort_order"
)


# JSONB does not keep key order; restore the catalog's natural order for display.
_SPEED_KEY_ORDER = ("download", "upload", "throughput", "sites", "lines", "codec", "data", "network")


def _ordered_speeds(speeds: dict) -> dict:
    rank = {k: i for i, k in enumerate(_SPEED_KEY_ORDER)}
    return dict(sorted((speeds or {}).items(), key=lambda kv: (rank.get(kv[0], len(rank)), kv[0])))


def _record(row: dict) -> ProductRecord:
    return ProductRecord.model_validate({**row, "speeds": _ordered_speeds(row.get("speeds"))})


def list_products(*, available_only: bool = True) -> list[ProductRecord]:
    sql = f"SELECT {_COLUMNS} FROM products"
    if available_only:
        sql += " WHERE available"
    sql += " ORDER BY sort_order, product_id"
    return [_record(r) for r in db.fetch_all(sql)]


def get_product(product_id: str) -> Optional[ProductRecord]:
    """Case-insensitive lookup by id (ids are stored upper-case)."""
    row = db.fetch_one(
        f"SELECT {_COLUMNS} FROM products WHERE product_id = upper(%s)",
        (product_id.strip(),),
    )
    return _record(row) if row else None


def get_products(product_ids: list[str]) -> dict[str, ProductRecord]:
    ids = [p.strip().upper() for p in product_ids]
    rows = db.fetch_all(f"SELECT {_COLUMNS} FROM products WHERE product_id = ANY(%s)", (ids,))
    return {r["product_id"]: _record(r) for r in rows}


def list_categories() -> list[str]:
    rows = db.fetch_all("SELECT DISTINCT category FROM products ORDER BY category")
    return [r["category"] for r in rows]
