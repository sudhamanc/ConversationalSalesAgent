"""
Deterministic pricing and offer tools.

All prices are controlled here so OfferManagement is the single source of truth.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..utils.cache import cache_result, get_cached_result
from ..utils.logger import get_logger
from ..utils.quote_db import insert_quote, get_quote, list_quotes_by_email

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

# BANT-score tiers → loyalty / readiness discount
# Prospects with higher qualification scores earn better rates.
BANT_DISCOUNTS = {
    "A": {"rate": 0.08, "label": "Preferred Business Discount (Tier A)"},
    "B": {"rate": 0.04, "label": "Business Advantage Discount (Tier B)"},
    "C": {"rate": 0.00, "label": None},  # No BANT discount for low-qualified
}


def _get_bant_discount_rate(bant_score: float) -> tuple[float, str | None]:
    """Return (discount_rate, customer_facing_label) based on BANT score 0-100."""
    if bant_score >= 66.7:
        tier = BANT_DISCOUNTS["A"]
    elif bant_score >= 33.3:
        tier = BANT_DISCOUNTS["B"]
    else:
        tier = BANT_DISCOUNTS["C"]
    return tier["rate"], tier["label"]


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


def find_best_bundle_offer(items: str, term_months: int = 12, bant_score: float = 0.0) -> Dict[str, Any]:
    """
    Evaluate bundle, term, and BANT-score discount rates for selected products.

    Args:
        items: JSON string — list of objects with product_id (str) and quantity (int).
               Example: '[{"product_id": "FIB-5G", "quantity": 1}]'
        term_months: Contract duration (12, 24, or 36)
        bant_score: Prospect's BANT qualification score (0-100). Defaults to 0.

    Returns JSON-like dict with selected discount rates and generated offer id.
    """
    # Parse items from JSON string (Gemini tool schemas don't support List[Dict])
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except (json.JSONDecodeError, ValueError):
            return {"found": False, "error": "items must be a valid JSON array string"}
    normalized_items = _normalize_items(items)
    cache_key = f"bundle:{json.dumps(normalized_items)}:{term_months}:{bant_score}"
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
    bant_discount_rate, bant_discount_label = _get_bant_discount_rate(float(bant_score))

    payload = {
        "items": normalized_items,
        "term_months": term_months,
        "bundle_discount_rate": bundle_discount_rate,
        "term_discount_rate": term_discount_rate,
        "bant_discount_rate": bant_discount_rate,
    }

    result = {
        "found": True,
        "offer_id": _make_offer_id(payload),
        "term_months": term_months,
        "bundle_discount_rate": bundle_discount_rate,
        "term_discount_rate": term_discount_rate,
        "bant_discount_rate": bant_discount_rate,
        "bant_discount_label": bant_discount_label,
    }

    cache_result(cache_key, result)
    return result


def generate_offer_quote(items: str, term_months: int = 12, bant_score: float = 0.0) -> Dict[str, Any]:
    """
    Generate an itemized quote with price points, discounts, and totals.

    Args:
        items: JSON string — list of objects with product_id (str) and quantity (int).
               Example: '[{"product_id": "FIB-5G", "quantity": 1}]'
        term_months: Contract duration (12, 24, or 36)
        bant_score: Prospect's BANT qualification score (0-100). Defaults to 0.

    Returns required JSON payload for downstream order placement.
    """
    # Parse items from JSON string (Gemini tool schemas don't support List[Dict])
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except (json.JSONDecodeError, ValueError):
            return {"found": False, "error": "items must be a valid JSON array string"}
    normalized_items = _normalize_items(items)
    bundle_result = find_best_bundle_offer(normalized_items, term_months, bant_score)
    if not bundle_result.get("found"):
        return bundle_result

    cache_key = f"quote:{json.dumps(normalized_items)}:{term_months}:{bant_score}"
    cached = get_cached_result(cache_key)
    if cached:
        return cached

    bundle_discount_rate = float(bundle_result["bundle_discount_rate"])
    term_discount_rate = float(bundle_result["term_discount_rate"])
    bant_discount_rate = float(bundle_result.get("bant_discount_rate", 0.0))
    bant_discount_label = bundle_result.get("bant_discount_label")

    priced_items: List[Dict[str, Any]] = []
    subtotal = 0.0
    total_bundle_discount = 0.0
    total_term_discount = 0.0
    total_bant_discount = 0.0
    total_discount = 0.0

    for item in normalized_items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        product = PRODUCT_PRICE_BOOK[product_id]

        unit_price = float(product["unit_price"])
        extended_price = round(unit_price * quantity, 2)

        # Layer 1: Bundle discount on base price
        item_bundle_discount = round(extended_price * bundle_discount_rate, 2)
        after_bundle = round(extended_price - item_bundle_discount, 2)

        # Layer 2: Term discount on post-bundle price
        item_term_discount = round(after_bundle * term_discount_rate, 2)
        after_term = round(after_bundle - item_term_discount, 2)

        # Layer 3: BANT qualification discount on post-term price
        item_bant_discount = round(after_term * bant_discount_rate, 2)

        item_total_discount = round(item_bundle_discount + item_term_discount + item_bant_discount, 2)
        final_price = round(extended_price - item_total_discount, 2)

        subtotal = round(subtotal + extended_price, 2)
        total_bundle_discount = round(total_bundle_discount + item_bundle_discount, 2)
        total_term_discount = round(total_term_discount + item_term_discount, 2)
        total_bant_discount = round(total_bant_discount + item_bant_discount, 2)
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
            "discount_detail": {
                "bundle_discount": item_bundle_discount,
                "term_discount": item_term_discount,
                "bant_discount": item_bant_discount,
            },
            "final_price": final_price,
        })

    total_price = round(subtotal - total_discount, 2)
    monthly_total = total_price
    yearly_total = round(monthly_total * 12, 2)

    # Build customer-friendly discount breakdown
    discount_breakdown: List[Dict[str, Any]] = []
    if bundle_discount_rate > 0:
        families = set()
        for item in normalized_items:
            pid = item["product_id"]
            if pid in PRODUCT_PRICE_BOOK:
                families.add(PRODUCT_PRICE_BOOK[pid]["family"])
        family_list = sorted(families)
        label = f"Multi-Product Bundle Discount ({' + '.join(f.title() for f in family_list)})"
        discount_breakdown.append({
            "type": "bundle",
            "label": label,
            "rate": bundle_discount_rate,
            "rate_display": f"{bundle_discount_rate * 100:.0f}%",
            "amount": total_bundle_discount,
        })
    if term_discount_rate > 0:
        discount_breakdown.append({
            "type": "term",
            "label": f"{term_months}-Month Commitment Discount",
            "rate": term_discount_rate,
            "rate_display": f"{term_discount_rate * 100:.0f}%",
            "amount": total_term_discount,
        })
    if bant_discount_rate > 0 and bant_discount_label:
        discount_breakdown.append({
            "type": "bant",
            "label": bant_discount_label,
            "rate": bant_discount_rate,
            "rate_display": f"{bant_discount_rate * 100:.0f}%",
            "amount": total_bant_discount,
        })

    result = {
        "offer_id": bundle_result["offer_id"],
        "term_months": term_months if term_months in TERM_DISCOUNTS else 12,
        "items": priced_items,
        "subtotal": subtotal,
        "discount_breakdown": discount_breakdown,
        "total_discount": total_discount,
        "total_price": total_price,
        "monthly_total": monthly_total,
        "yearly_total": yearly_total,
    }

    cache_result(cache_key, result)
    logger.info("Generated offer quote %s for %d items (bant_score=%.1f)", result["offer_id"], len(priced_items), bant_score)
    return result


# ---------------------------------------------------------------------------
# Quote persistence helpers
# ---------------------------------------------------------------------------

def _auto_send_quote_confirmation(
    quote_id: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    items_summary: str,
    monthly_total: float,
    term_months: int,
    total_discount: float,
) -> Dict[str, Any]:
    """
    Automatically send a quote confirmation email/SMS immediately after a quote
    is saved.  Uses sys.modules to call the already-loaded
    CustomerCommunicationAgent notification tools without a hard cross-package
    import dependency.
    """
    try:
        notif_mod = sys.modules.get("customer_communication_agent.tools.notification_tools")
        if notif_mod is None:
            notif_mod = sys.modules.get("customer_communication_agent.tools")

        if notif_mod is None or not hasattr(notif_mod, "send_quote_confirmation"):
            logger.warning(
                "CustomerCommunicationAgent notification tools not found in sys.modules; "
                "quote confirmation email will not be sent automatically."
            )
            return {"success": False, "error": "Notification module unavailable"}

        result = notif_mod.send_quote_confirmation(
            quote_id=quote_id,
            customer_name=customer_name,
            customer_email=customer_email or None,
            customer_phone=customer_phone or None,
            items_summary=items_summary,
            monthly_total=monthly_total,
            term_months=term_months,
            total_discount=total_discount,
        )
        logger.info(f"Auto quote confirmation triggered for {quote_id}: {result}")
        return result
    except Exception as exc:
        logger.warning(f"Auto quote confirmation failed (non-fatal): {exc}")
        return {"success": False, "error": str(exc)}


def save_quote(
    items: str,
    term_months: int = 12,
    bant_score: float = 0.0,
    customer_name: str = None,
    customer_email: str = None,
    customer_phone: str = None,
) -> Dict[str, Any]:
    """
    Generate a full quote and persist it to the QuoteDB.

    This is a convenience wrapper around ``generate_offer_quote`` that also
    saves the result to SQLite and sends a quote confirmation notification.

    Args:
        items: JSON string — list of objects with product_id (str) and quantity (int).
               Example: '[{"product_id": "FIB-5G", "quantity": 1}]'
        term_months: Contract duration (12, 24, or 36)
        bant_score: Prospect BANT qualification score (0-100). Defaults to 0.
        customer_name: Customer / company name (for notification)
        customer_email: Contact email (for notification)
        customer_phone: Contact phone (for notification)

    Returns:
        JSON dict with quote_id, full pricing breakdown, and notification status.
    """
    # Parse items from JSON string (Gemini tool schemas don't support List[Dict])
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except (json.JSONDecodeError, ValueError):
            return {"success": False, "error": "items must be a valid JSON array string"}
    # 1. Generate the pricing quote
    quote_data = generate_offer_quote(items, term_months, bant_score)
    if not quote_data.get("offer_id"):
        return quote_data  # Validation error – pass through

    # 2. Derive a unique quote_id
    now = datetime.now()
    quote_id = f"QT-{now.strftime('%Y%m%d%H%M%S')}-{quote_data['offer_id'][-6:]}"
    expires_at = (now + timedelta(days=30)).isoformat()

    # Build human-readable items summary
    product_names = [item.get("product_name", item.get("product_id", "?")) for item in quote_data.get("items", [])]
    items_summary = ", ".join(product_names)

    # 3. Persist to QuoteDB
    try:
        insert_quote(
            quote_id=quote_id,
            offer_id=quote_data["offer_id"],
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            items=quote_data["items"],
            term_months=quote_data.get("term_months", term_months),
            bant_score=bant_score,
            subtotal=quote_data["subtotal"],
            total_discount=quote_data["total_discount"],
            monthly_total=quote_data["monthly_total"],
            yearly_total=quote_data["yearly_total"],
            discount_breakdown=quote_data.get("discount_breakdown", []),
            created_at=now.isoformat(),
            expires_at=expires_at,
        )
        logger.info(f"Quote {quote_id} saved to QuoteDB")
    except Exception as exc:
        logger.error(f"Failed to persist quote: {exc}")
        return {
            "success": False,
            "error": f"Quote generation succeeded but persistence failed: {exc}",
            "quote_data": quote_data,
        }

    # 4. Auto-send quote confirmation notification
    notif_result = _auto_send_quote_confirmation(
        quote_id=quote_id,
        customer_name=customer_name or "Valued Customer",
        customer_email=customer_email,
        customer_phone=customer_phone,
        items_summary=items_summary,
        monthly_total=quote_data["monthly_total"],
        term_months=quote_data.get("term_months", term_months),
        total_discount=quote_data["total_discount"],
    )

    email_sent = bool(notif_result and notif_result.get("success"))
    email_notification_id = notif_result.get("notification_id") if notif_result else None

    # 5. Return combined result
    return {
        "success": True,
        "quote_id": quote_id,
        "expires_at": expires_at,
        **quote_data,
        "email_confirmation_sent": email_sent,
        "email_notification_id": email_notification_id,
        "message": f"Quote {quote_id} saved successfully. Valid for 30 days.",
    }


def get_saved_quote(quote_id: str) -> Dict[str, Any]:
    """
    Retrieve a previously saved quote by its quote_id.

    Args:
        quote_id: The quote identifier returned by save_quote.

    Returns:
        Quote details or an error dict if not found.
    """
    row = get_quote(quote_id)
    if row is None:
        return {"found": False, "error": f"No quote found with id {quote_id}"}
    return {"found": True, **row}
