"""PostgreSQL queries for the ``coverage_zones`` table (migration 004)."""

from __future__ import annotations

from typing import Optional

from sales_common import db

_COLUMNS = (
    "zip_code, city, state, serviceable, service_zone, infrastructure_type, infrastructure, "
    "max_speed_mbps, estimated_install_days, available_products, available_product_categories, reason"
)


def get_coverage(zip_code: str) -> Optional[dict]:
    """Coverage row for a ZIP code (JSONB columns decoded), or ``None``."""
    return db.fetch_one(f"SELECT {_COLUMNS} FROM coverage_zones WHERE zip_code = %s", (zip_code,))


def list_service_zones() -> list[str]:
    """Distinct service zones of serviceable ZIPs, sorted."""
    rows = db.fetch_all(
        "SELECT DISTINCT service_zone FROM coverage_zones "
        "WHERE serviceable AND service_zone IS NOT NULL ORDER BY service_zone"
    )
    return [row["service_zone"] for row in rows]
