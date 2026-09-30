"""Catalog business logic shared by the REST API and the MCP tools.

Functions take plain arguments and return pydantic models. Invalid input
raises :class:`InvalidInputError` (REST 422), unknown products raise
:class:`ProductNotFoundError` (REST 404). No function returns price fields.

Defects fixed relative to the legacy ProductAgent tools (design D3):

* product ids are matched case-insensitively;
* speeds are compared numerically in Mbps (``"1 Gbps"`` > ``"500 Mbps"``);
* the ignored ``max_price`` / ``max_budget`` parameters are gone;
  ``get_best_value_product`` ranks by Mbps, optionally within a category.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from . import rag, repository
from .models import (
    Alternative,
    AlternativesResult,
    BestValueResult,
    CategoryList,
    CompareResult,
    Comparison,
    ComparisonTable,
    KnowledgeResult,
    ProductDetail,
    ProductList,
    ProductRecord,
    ProductRef,
    ProductSummary,
    SearchCriteria,
    SearchItem,
    SearchResult,
)

MIN_COMPARE = 2
MAX_COMPARE = 5
MAX_ALTERNATIVES = 5
CRITERIA = ("faster", "similar", "different_tech")
DEFAULT_TOP_K = 4
MAX_TOP_K = 10


class CatalogError(Exception):
    """Base class for catalog errors."""


class InvalidInputError(CatalogError):
    """Input failed validation (REST 422)."""


class ProductNotFoundError(CatalogError):
    """Product id is not in the catalog (REST 404)."""

    def __init__(self, product_id: str):
        super().__init__(f"Product '{product_id}' not found in catalog")
        self.product_id = product_id


# ---------------------------------------------------------------------------
# Speed parsing
# ---------------------------------------------------------------------------

_UNIT_MBPS = {"k": 0.001, "m": 1.0, "g": 1000.0, "t": 1_000_000.0}
_SPEED_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*([kmgt])?(?:bps|b/s|bit/s|b)?\b", re.IGNORECASE)

_OPERATORS: list[tuple[str, str]] = [
    (">=", ">="), ("=>", ">="), ("<=", "<="), ("=<", "<="), (">", ">"), ("<", "<"), ("=", "="),
    ("at least", ">="), ("minimum", ">="), ("min", ">="), ("or more", ">="), ("or faster", ">="),
    ("more than", ">"), ("faster than", ">"), ("greater than", ">"), ("over", ">"), ("above", ">"),
    ("at most", "<="), ("up to", "<="), ("maximum", "<="), ("max", "<="),
    ("less than", "<"), ("slower than", "<"), ("under", "<"), ("below", "<"),
]


def parse_speed_mbps(text: Optional[str]) -> Optional[float]:
    """Parse ``"1 Gbps"`` / ``"Up to 250 Mbps"`` / ``"500"`` to Mbps; ``None`` if absent."""
    if not text:
        return None
    match = _SPEED_RE.search(str(text))
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    unit = (match.group(2) or "m").lower()
    return value * _UNIT_MBPS[unit]


def parse_speed_query(speed: str) -> tuple[str, float]:
    """Parse a speed filter such as ``"1 Gbps"``, ``">= 500 Mbps"`` or ``"under 1 Gbps"``.

    Returns ``(operator, mbps)``; a bare value means an exact match.
    """
    text = speed.strip().lower()
    op = "="
    for token, symbol in _OPERATORS:
        if text.startswith(token) or (token in {"or more", "or faster"} and text.endswith(token)):
            op = symbol
            text = text[len(token):] if text.startswith(token) else text[: -len(token)]
            break
    mbps = parse_speed_mbps(text)
    if mbps is None:
        raise InvalidInputError(
            f"Unrecognised speed {speed!r}; use e.g. '1 Gbps', '500 Mbps', '>= 1 Gbps', 'under 500 Mbps'"
        )
    return op, mbps


def _matches(value: float, op: str, target: float) -> bool:
    return {
        "=": abs(value - target) < 1e-6,
        ">=": value >= target,
        "<=": value <= target,
        ">": value > target,
        "<": value < target,
    }[op]


def download_mbps(product: ProductRecord) -> Optional[float]:
    return parse_speed_mbps(product.speeds.get("download"))


def throughput_mbps(product: ProductRecord) -> Optional[float]:
    """Download speed, falling back to SD-WAN ``throughput``."""
    value = download_mbps(product)
    return value if value is not None else parse_speed_mbps(product.speeds.get("throughput"))


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

_CATEGORY_ALIASES = {
    "voice": "Voice",
    "business voice": "Voice",
    "mobile": "Business Mobile",
    "business mobile": "Business Mobile",
    "wireless": "Business Mobile",
    "sd-wan": "SD-WAN",
    "sdwan": "SD-WAN",
    "wan": "SD-WAN",
    "fiber": "Fiber Internet",
    "fibre": "Fiber Internet",
    "fiber internet": "Fiber Internet",
    "coax": "Coax Internet",
    "cable": "Coax Internet",
    "coax internet": "Coax Internet",
    "internet": "Fiber Internet",
}


def normalize_category(category: str) -> str:
    """Map aliases (``fiber``, ``sdwan``...) to canonical category names."""
    cleaned = category.strip()
    return _CATEGORY_ALIASES.get(cleaned.lower(), cleaned)


def _summary(p: ProductRecord) -> ProductSummary:
    return ProductSummary(
        product_id=p.product_id,
        product_name=p.product_name,
        category=p.category,
        technology=p.technology,
        speeds=p.speeds,
    )


def _dedupe(ids: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for pid in ids:
        key = str(pid).strip().upper()
        if key and key not in seen:
            seen.append(key)
    return seen


def _require_id(product_id: str) -> str:
    if not product_id or not str(product_id).strip():
        raise InvalidInputError("product_id is required")
    return str(product_id).strip()


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def list_available_products(category: Optional[str] = None) -> ProductList:
    products = repository.list_products()
    canonical = None
    if category and category.strip():
        canonical = normalize_category(category)
        products = [p for p in products if p.category.lower() == canonical.lower()]
    return ProductList(products=[_summary(p) for p in products], count=len(products), category=canonical)


def get_product_by_id(product_id: str) -> ProductDetail:
    pid = _require_id(product_id)
    record = repository.get_product(pid)
    if record is None:
        raise ProductNotFoundError(pid)
    return ProductDetail(
        product_id=record.product_id,
        product_name=record.product_name,
        category=record.category,
        technology=record.technology,
        speeds=record.speeds,
        description=record.description,
        features=record.features,
        available=record.available,
    )


def search_products_by_criteria(
    speed: Optional[str] = None, technology: Optional[str] = None
) -> SearchResult:
    op = target = None
    if speed and speed.strip():
        op, target = parse_speed_query(speed)
    tech = technology.strip().lower() if technology and technology.strip() else None
    matching = []
    for product in repository.list_products():
        if tech and product.technology.lower() != tech:
            continue
        if target is not None:
            value = download_mbps(product)
            if value is None or not _matches(value, op, target):
                continue
        matching.append(
            SearchItem(
                product_id=product.product_id,
                product_name=product.product_name,
                category=product.category,
                technology=product.technology,
                speeds=product.speeds,
                description=product.description,
            )
        )
    return SearchResult(
        products=matching,
        count=len(matching),
        criteria=SearchCriteria(
            speed=speed or None,
            speed_mbps=target,
            speed_operator=op,
            technology=technology or None,
        ),
    )


def get_product_categories() -> CategoryList:
    categories = repository.list_categories()
    return CategoryList(categories=categories, count=len(categories))


def _sla(product: ProductRecord) -> str:
    for feature in product.features:
        if "SLA" in feature or "uptime" in feature.lower():
            return feature
    return "N/A"


def compare_products(product_ids: list[str]) -> CompareResult:
    ids = _dedupe(product_ids or [])
    if len(ids) < MIN_COMPARE:
        raise InvalidInputError(f"At least {MIN_COMPARE} distinct products are required for comparison")
    if len(ids) > MAX_COMPARE:
        raise InvalidInputError(f"Maximum {MAX_COMPARE} products can be compared at once")
    found = repository.get_products(ids)
    products = [found[pid] for pid in ids if pid in found]
    not_found = [pid for pid in ids if pid not in found]
    if not products:
        raise ProductNotFoundError(", ".join(not_found))

    table = ComparisonTable(
        product_name=[p.product_name for p in products],
        technology=[p.technology for p in products],
        download_speed=[p.speeds.get("download", "N/A") for p in products],
        upload_speed=[p.speeds.get("upload", "N/A") for p in products],
        uptime_sla=[_sla(p) for p in products],
        key_features=[p.features[:3] for p in products],
    )
    speeds = [(throughput_mbps(p), i) for i, p in enumerate(products)]
    ranked = [(s, i) for s, i in speeds if s is not None]
    # Highest Mbps wins; ties go to the product listed first.
    fastest = products[max(ranked, key=lambda t: (t[0], -t[1]))[1]] if ranked else None
    if fastest is not None:
        recommendation = (
            f"For maximum performance, consider {fastest.product_name} ({fastest.product_id}). "
            "For general business fit, review SLA and feature requirements for each option."
        )
    else:
        recommendation = (
            "These products have no comparable speed metric; "
            "review SLA and feature requirements for each option."
        )
    return CompareResult(
        comparison=Comparison(products=[p.product_id for p in products], comparison_table=table),
        products_compared=len(products),
        not_found=not_found,
        fastest_product_id=fastest.product_id if fastest else None,
        recommendation=recommendation,
    )


def suggest_alternatives(product_id: str, criteria: Optional[str] = None) -> AlternativesResult:
    pid = _require_id(product_id)
    crit = criteria.strip().lower() if criteria and criteria.strip() else None
    if crit in {"general", "any"}:
        crit = None
    if crit == "cheaper":
        raise InvalidInputError("Price-based alternatives are handled by offer management")
    if crit is not None and crit not in CRITERIA:
        raise InvalidInputError(f"criteria must be one of {list(CRITERIA)}")
    base = repository.get_product(pid)
    if base is None:
        raise ProductNotFoundError(pid)

    base_speed = download_mbps(base)
    candidates: list[tuple[tuple, Alternative]] = []
    for product in repository.list_products():
        if product.product_id == base.product_id:
            continue
        reason = None
        sort_key: tuple = (product.sort_order, product.product_id)
        if crit == "faster":
            speed = download_mbps(product)
            if base_speed is not None and speed is not None and speed > base_speed:
                reason = f"Higher speed tier ({product.speeds.get('download')} download)"
                sort_key = (speed, product.product_id)
        elif crit == "similar":
            if product.technology.lower() == base.technology.lower():
                reason = "Similar technology profile"
        elif crit == "different_tech":
            same_family = (product.family or product.category) == (base.family or base.category)
            if same_family and product.technology.lower() != base.technology.lower():
                reason = f"Alternative technology ({product.technology})"
        elif product.category == base.category:
            reason = "Similar product category"
        if reason:
            candidates.append(
                (
                    sort_key,
                    Alternative(
                        product_id=product.product_id,
                        product_name=product.product_name,
                        category=product.category,
                        technology=product.technology,
                        speeds=product.speeds,
                        reason=reason,
                    ),
                )
            )
    candidates.sort(key=lambda c: c[0])
    alternatives = [alt for _, alt in candidates[:MAX_ALTERNATIVES]]
    return AlternativesResult(
        base_product=ProductRef(product_id=base.product_id, product_name=base.product_name),
        alternatives=alternatives,
        count=len(alternatives),
        criteria=crit or "general",
    )


def get_best_value_product(category: Optional[str] = None) -> BestValueResult:
    listing = repository.list_products()
    canonical = normalize_category(category) if category and category.strip() else None
    if canonical:
        listing = [p for p in listing if p.category.lower() == canonical.lower()]
    if not listing:
        return BestValueResult(found=False, category=canonical, reason="No available products match")
    scored = [(throughput_mbps(p), p) for p in listing]
    scored = [(s, p) for s, p in scored if s is not None]
    if not scored:
        return BestValueResult(
            found=False,
            category=canonical,
            reason="Products in this category have no comparable speed metric; use compare_products",
        )
    best = max(scored, key=lambda t: (t[0], -t[1].sort_order))[1]
    scope = f"in {canonical}" if canonical else "among available products"
    return BestValueResult(
        found=True,
        recommended=_summary(best),
        category=canonical,
        reason=f"Highest technical throughput {scope} (pricing is provided by offer management)",
    )


def search_product_knowledge(query: str, top_k: int = DEFAULT_TOP_K) -> KnowledgeResult:
    if not query or not query.strip():
        raise InvalidInputError("query is required")
    if not isinstance(top_k, int) or not 1 <= top_k <= MAX_TOP_K:
        raise InvalidInputError(f"top_k must be between 1 and {MAX_TOP_K}")
    return rag.search(query.strip(), top_k)
