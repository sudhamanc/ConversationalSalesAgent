"""Unit tests for Offer Management pricing tools."""

from offer_management.tools.pricing_tools import find_best_bundle_offer, generate_offer_quote


def test_find_best_bundle_offer_success():
    result = find_best_bundle_offer(
        [
            {"product_id": "FIB-5G", "quantity": 1},
            {"product_id": "VOICE-STD", "quantity": 10},
        ],
        term_months=24,
    )

    assert result["found"] is True
    assert result["offer_id"].startswith("OFF-")
    assert result["bundle_discount_rate"] > 0
    assert result["term_discount_rate"] == 0.05


def test_generate_offer_quote_minimal_shape():
    result = generate_offer_quote(
        [
            {"product_id": "FIB-1G"},
            {"product_id": "SDWAN-ESS", "quantity": 1},
        ],
        term_months=12,
    )

    assert "offer_id" in result
    assert "items" in result
    assert "subtotal" in result
    assert "total_discount" in result
    assert "total_price" in result
    assert len(result["items"]) == 2


def test_generate_offer_quote_unknown_product():
    result = generate_offer_quote([
        {"product_id": "NOPE-1", "quantity": 1},
    ])

    assert result["found"] is False
    assert result["error"] == "unknown_products"
