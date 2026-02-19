"""
Deterministic pricing and offer tools.

All prices are controlled here so OfferManagement is the single source of truth.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from ..utils.cache import cache_result, get_cached_result
from ..utils.logger import get_logger

logger = get_logger(__name__)

PRODUCT_PRICE_BOOK = {
    "FIB-1G": {"product_name": "Business Fiber 1 Gbps", "unit_price": 249.0, "family": "internet"},
    "FIB-5G": {"product_name": "Business Fiber 5 Gbps", "unit_price": 599.0, "family": "internet"},
    "FIB-10G": {"product_name": "Business Fiber 10 Gbps", "unit_price": 999.0, "family": "internet"},
    "COAX-200M": {"product_name": "Business Internet 200 Mbps", "unit_price": 79.0, "family": "internet"},
    "COAX-500M": {"product_name": "Business Internet 500 Mbps", "unit_price": 149.0, "family": "internet"},
    "COAX-1G": {"product_name": "Business Internet 1 Gbps", "unit_price": 249.0, "family": "internet"},
    "VOICE-BAS": {"product_name": "Business Voice Basic", "unit_price": 29.0, "family": "voice"},
    "VOICE-STD": {"product_name": "Business Voice Standard", "unit_price": 24.0, "family": "voice"},
    "VOICE-ENT": {"product_name": "Business Voice Enterprise", "unit_price": 19.0, "family": "voice"},
    "VOICE-UCAAS": {"product_name": "Unified Communications (UCaaS)", "unit_price": 39.0, "family": "voice"},
    "SDWAN-ESS": {"product_name": "SD-WAN Essentials", "unit_price": 199.0, "family": "sdwan"},
    "SDWAN-PRO": {"product_name": "SD-WAN Professional", "unit_price": 399.0, "family": "sdwan"},
    "SDWAN-ENT": {"product_name": "SD-WAN Enterprise", "unit_price": 699.0, "family": "sdwan"},
    "MOB-BAS": {"product_name": "Business Mobile Basic", "unit_price": 35.0, "family": "mobile"},
    "MOB-UNL": {"product_name": "Business Mobile Unlimited", "unit_price": 55.0, "family": "mobile"},
    "MOB-PREM": {"product_name": "Business Mobile Premium", "unit_price": 75.0, "family": "mobile"},
}

TERM_DISCOUNTS = {
    12: 0.0,
    24: 0.05,
    36: 0.10,
}

BUNDLE_DISCOUNTS = {
    "internet_plus_voice": 0.05,
    "internet_plus_sdwan": 0.07,
    "triple_play": 0.10,
}


def _normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in items:
        product_id = str(item.get("product_id", "")).strip().upper()
        quantity = item.get("quantity", 1)
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 1
        if quantity < 1:
            quantity = 1
        if product_id:
            normalized.append({"product_id": product_id, "quantity": quantity})
    normalized.sort(key=lambda x: x["product_id"])
    return normalized


def _get_bundle_discount_rate(product_ids: List[str]) -> float:
    families = {PRODUCT_PRICE_BOOK[pid]["family"] for pid in product_ids if pid in PRODUCT_PRICE_BOOK}
    has_internet = "internet" in families
    has_voice = "voice" in families
    has_sdwan = "sdwan" in families

    if has_internet and has_voice and has_sdwan:
        return BUNDLE_DISCOUNTS["triple_play"]
    if has_internet and has_sdwan:
        return BUNDLE_DISCOUNTS["internet_plus_sdwan"]
    if has_internet and has_voice:
        return BUNDLE_DISCOUNTS["internet_plus_voice"]
    return 0.0


def _make_offer_id(payload: Dict[str, Any]) -> str:
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:10]
    return f"OFF-{digest.upper()}"


def find_best_bundle_offer(items: List[Dict[str, Any]], term_months: int = 12) -> Dict[str, Any]:
    """
    Evaluate bundle and term discount rates for selected products.

    Returns JSON-like dict with selected discount rates and generated offer id.
    """
    normalized_items = _normalize_items(items)
    cache_key = f"bundle:{json.dumps(normalized_items)}:{term_months}"
    cached = get_cached_result(cache_key)
    if cached:
        return cached

    invalid_ids = [item["product_id"] for item in normalized_items if item["product_id"] not in PRODUCT_PRICE_BOOK]
    if invalid_ids:
        result = {
            "found": False,
            "error": "unknown_products",
            "unknown_product_ids": sorted(set(invalid_ids)),
            "message": "One or more product ids are not recognized."
        }
        cache_result(cache_key, result)
        return result

    if term_months not in TERM_DISCOUNTS:
        term_months = 12

    product_ids = [item["product_id"] for item in normalized_items]
    bundle_discount_rate = _get_bundle_discount_rate(product_ids)
    term_discount_rate = TERM_DISCOUNTS[term_months]

    payload = {
        "items": normalized_items,
        "term_months": term_months,
        "bundle_discount_rate": bundle_discount_rate,
        "term_discount_rate": term_discount_rate,
    }

    result = {
        "found": True,
        "offer_id": _make_offer_id(payload),
        "term_months": term_months,
        "bundle_discount_rate": bundle_discount_rate,
        "term_discount_rate": term_discount_rate,
    }

    cache_result(cache_key, result)
    return result


def generate_offer_quote(items: List[Dict[str, Any]], term_months: int = 12) -> Dict[str, Any]:
    """
    Generate an itemized quote with price points, discounts, and totals.

    Returns required JSON payload for downstream order placement.
    """
    normalized_items = _normalize_items(items)
    bundle_result = find_best_bundle_offer(normalized_items, term_months)
    if not bundle_result.get("found"):
        return bundle_result

    cache_key = f"quote:{json.dumps(normalized_items)}:{term_months}"
    cached = get_cached_result(cache_key)
    if cached:
        return cached

    bundle_discount_rate = float(bundle_result["bundle_discount_rate"])
    term_discount_rate = float(bundle_result["term_discount_rate"])

    priced_items: List[Dict[str, Any]] = []
    subtotal = 0.0
    total_discount = 0.0

    for item in normalized_items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        product = PRODUCT_PRICE_BOOK[product_id]

        unit_price = float(product["unit_price"])
        extended_price = round(unit_price * quantity, 2)
        item_bundle_discount = round(extended_price * bundle_discount_rate, 2)
        after_bundle = round(extended_price - item_bundle_discount, 2)
        item_term_discount = round(after_bundle * term_discount_rate, 2)
        item_total_discount = round(item_bundle_discount + item_term_discount, 2)
        final_price = round(extended_price - item_total_discount, 2)

        subtotal = round(subtotal + extended_price, 2)
        total_discount = round(total_discount + item_total_discount, 2)

        priced_items.append({
            "product_id": product_id,
            "product_name": product["product_name"],
            "quantity": quantity,
            "price_points": {
                "unit_price": unit_price,
                "extended_price": extended_price,
            },
            "discount": item_total_discount,
            "final_price": final_price,
        })

    total_price = round(subtotal - total_discount, 2)
    monthly_total = total_price
    yearly_total = round(monthly_total * 12, 2)

    result = {
        "offer_id": bundle_result["offer_id"],
        "term_months": term_months if term_months in TERM_DISCOUNTS else 12,
        "items": priced_items,
        "subtotal": subtotal,
        "total_discount": total_discount,
        "total_price": total_price,
        "monthly_total": monthly_total,
        "yearly_total": yearly_total,
    }

    cache_result(cache_key, result)
    logger.info("Generated offer quote %s for %d items", result["offer_id"], len(priced_items))
    return result
