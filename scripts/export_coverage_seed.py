#!/usr/bin/env python3
"""Export the legacy serviceability mock coverage data to PostgreSQL seed SQL.

One-time migration helper. Reads ``MOCK_COVERAGE_DATA`` and the per-technology
infrastructure defaults (``infrastructure_catalog`` inside
``get_infrastructure_by_technology``) from the legacy module
``ServiceabilityAgent/serviceability_agent/tools/gis_tools.py`` and writes
``db/seed/003_coverage.sql`` matching ``db/migrations/004_coverage.sql``.

The legacy module is read with ``ast`` (literal evaluation only), so nothing is
imported or executed: no ADK agent is constructed and ``GEMINI_MODEL`` is not
needed. The module now lives only in git history (it was moved into
``services/serviceability``), so by default it is read with ``git show``.

Transformations:

* Legacy ``products`` lists (plans with prices) are dropped; the per-ZIP
  ``available_products`` SKU lists are kept unchanged.
* Serviceable ZIPs without an ``infrastructure`` object get one built from the
  technology defaults. ``max_speed_mbps`` is capped at the fastest internet SKU
  sold in that ZIP so speeds agree with ``available_products``.
* ``available_product_categories`` is computed as the legacy lookup did.

The seed is idempotent (``INSERT ... ON CONFLICT (zip_code) DO UPDATE``).

Usage::

    python scripts/export_coverage_seed.py [--source PATH] [--git-rev REV] [--out PATH]
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEGACY_PATH = "ServiceabilityAgent/serviceability_agent/tools/gis_tools.py"
DEFAULT_OUT = ROOT / "db" / "seed" / "003_coverage.sql"

# City/state per ZIP, taken from the comments next to each legacy entry.
# ``None`` where the legacy comment names no city (synthetic ZIPs).
ZIP_LOCATIONS: dict[str, tuple[str | None, str | None]] = {
    "19107": ("Philadelphia", "PA"), "19103": ("Philadelphia", "PA"), "18000": (None, "PA"),
    "10001": ("New York", "NY"), "90001": ("Los Angeles", "CA"), "60601": ("Chicago", "IL"),
    "94102": ("San Francisco", "CA"), "02101": ("Boston", "MA"), "98101": ("Seattle", "WA"),
    "30301": ("Atlanta", "GA"), "33101": ("Miami", "FL"), "75201": ("Dallas", "TX"),
    "85001": ("Phoenix", "AZ"), "80201": ("Denver", "CO"), "20001": ("Washington", "DC"),
    "55401": ("Minneapolis", "MN"), "63101": ("St. Louis", "MO"), "97201": ("Portland", "OR"),
    "89101": ("Las Vegas", "NV"), "28201": ("Charlotte", "NC"), "92101": ("San Diego", "CA"),
    "78701": ("Austin", "TX"), "37201": ("Nashville", "TN"), "27601": ("Raleigh", "NC"),
    "43201": ("Columbus", "OH"), "46201": ("Indianapolis", "IN"), "64101": ("Kansas City", "MO"),
    "53201": ("Milwaukee", "WI"), "48201": ("Detroit", "MI"), "21201": ("Baltimore", "MD"),
    "95101": ("San Jose", "CA"), "73301": ("Austin", "TX"), "07101": ("Newark", "NJ"),
    "06103": ("Hartford", "CT"), "08053": ("Marlton", "NJ"), "99501": ("Anchorage", "AK"),
    "96801": ("Honolulu", "HI"), "88901": (None, "NV"),
}

# Infrastructure ``type`` label used by the legacy records per technology.
INFRASTRUCTURE_TYPE_LABELS = {"FTTP": "Fiber", "HFC": "Coax/HFC", "DOCSIS 3.1": "Coax/DOCSIS 3.1"}

# Download speed (Mbps) of each internet SKU, used to cap derived max speeds.
INTERNET_SKU_MBPS = {
    "FIB-1G": 1000, "FIB-5G": 5000, "FIB-10G": 10000,
    "COAX-200M": 200, "COAX-500M": 500, "COAX-1G": 1000,
}

INTERNET_TECHNOLOGIES = {"FTTP", "HFC", "DOCSIS 3.1"}


def read_legacy_source(source: str | None, git_rev: str) -> str:
    """Return the legacy module source from a file, the working tree or git history."""
    if source:
        return Path(source).read_text(encoding="utf-8")
    working = ROOT / LEGACY_PATH
    if working.is_file():
        return working.read_text(encoding="utf-8")

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout

    try:
        return git("show", f"{git_rev}:{LEGACY_PATH}")
    except subprocess.CalledProcessError:
        # Removed at git_rev: read it from the parent of the commit that removed it.
        last = git("rev-list", "-n", "1", git_rev, "--", LEGACY_PATH).strip()
        if not last:
            raise SystemExit(f"{LEGACY_PATH} not found in git history; pass --source")
        return git("show", f"{last}^:{LEGACY_PATH}")


def extract_literals(source: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (MOCK_COVERAGE_DATA, infrastructure_catalog) via ``ast.literal_eval``."""
    tree = ast.parse(source)
    coverage = defaults = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "MOCK_COVERAGE_DATA":
                coverage = ast.literal_eval(node.value)
            elif isinstance(target, ast.Name) and target.id == "infrastructure_catalog":
                defaults = ast.literal_eval(node.value)
    if coverage is None or defaults is None:
        raise SystemExit("Legacy source lacks MOCK_COVERAGE_DATA or infrastructure_catalog")
    return coverage, defaults


def default_infrastructure(technology: str, defaults: dict[str, Any], skus: list[str]) -> dict:
    """Infrastructure object derived from the technology defaults."""
    spec = defaults[technology]
    max_speed = spec["max_speed_mbps"]
    sku_speeds = [INTERNET_SKU_MBPS[s] for s in skus if s in INTERNET_SKU_MBPS]
    if sku_speeds:
        max_speed = min(max_speed, max(sku_speeds))
    return {
        "type": INFRASTRUCTURE_TYPE_LABELS[technology],
        "network_element": {
            "typical_equipment": list(spec["typical_equipment"]),
            "details_source": "technology_defaults",
        },
        "speed_capability": {
            "min_speed_mbps": min(spec["min_speed_mbps"], max_speed),
            "max_speed_mbps": max_speed,
            "symmetrical": spec["symmetrical"],
        },
        "service_class": spec["service_classes"][0],
        "redundancy_available": spec["redundancy_capable"],
    }


def build_rows(coverage: dict[str, Any], defaults: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for zip_code, data in coverage.items():
        city, state = ZIP_LOCATIONS.get(zip_code, (None, None))
        row: dict[str, Any] = {
            "zip_code": zip_code,
            "city": city,
            "state": state,
            "serviceable": bool(data.get("serviceable")),
            "service_zone": None,
            "infrastructure_type": None,
            "infrastructure": None,
            "max_speed_mbps": None,
            "estimated_install_days": None,
            "available_products": [],
            "available_product_categories": [],
            "reason": data.get("reason"),
        }
        if row["serviceable"]:
            technology = data["technology"]
            skus = list(data.get("available_products", []))
            infrastructure = data.get("infrastructure") or default_infrastructure(
                technology, defaults, skus
            )
            categories = ["Internet"] if technology in INTERNET_TECHNOLOGIES else []
            categories += ["Voice", "SD-WAN", "Mobile"]
            row.update(
                service_zone=data["zone"],
                infrastructure_type=technology,
                infrastructure=infrastructure,
                max_speed_mbps=infrastructure["speed_capability"]["max_speed_mbps"],
                estimated_install_days=data["install_days"],
                available_products=skus,
                available_product_categories=categories,
                reason=None,
            )
        rows.append(row)
    return rows


def literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (dict, list)):
        text = json.dumps(value, separators=(", ", ": "))
        return "'" + text.replace("'", "''") + "'::jsonb"
    return "'" + str(value).replace("'", "''") + "'"


COLUMNS = [
    "zip_code", "city", "state", "serviceable", "service_zone", "infrastructure_type",
    "infrastructure", "max_speed_mbps", "estimated_install_days", "available_products",
    "available_product_categories", "reason",
]


def render_sql(rows: list[dict[str, Any]]) -> str:
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNS if c != "zip_code")
    lines = [
        "-- Coverage seed exported from the legacy serviceability MOCK_COVERAGE_DATA.",
        "-- Generated by scripts/export_coverage_seed.py. Do not edit by hand.",
        "-- Idempotent: re-applying updates existing rows.",
        "SET client_min_messages = warning;",
        "",
        f"-- coverage_zones: {len(rows)} rows "
        f"({sum(r['serviceable'] for r in rows)} serviceable)",
    ]
    for row in rows:
        values = ", ".join(literal(row[c]) for c in COLUMNS)
        lines.append(
            f"INSERT INTO coverage_zones ({', '.join(COLUMNS)}) VALUES ({values}) "
            f"ON CONFLICT (zip_code) DO UPDATE SET {updates};"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--source", help="path to the legacy gis_tools.py (default: git history)")
    parser.add_argument("--git-rev", default="HEAD", help="git revision to read the legacy module from")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output SQL path")
    args = parser.parse_args(argv)

    coverage, defaults = extract_literals(read_legacy_source(args.source, args.git_rev))
    rows = build_rows(coverage, defaults)
    missing = [r["zip_code"] for r in rows if r["serviceable"] and not r["infrastructure"]]
    if missing:
        raise SystemExit(f"Serviceable ZIPs without infrastructure: {missing}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_sql(rows), encoding="utf-8")
    print(f"Wrote {len(rows)} coverage rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
