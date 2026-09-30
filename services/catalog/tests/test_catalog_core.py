"""Unit tests for catalog_service.core (parsing is pure; the rest uses the seeded DB)."""

import pytest

from catalog_service import core
from catalog_service.core import InvalidInputError, ProductNotFoundError

PRICE_FIELDS = {"price", "unit_price", "family", "sort_order"}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,mbps",
    [
        ("1 Gbps", 1000.0),
        ("10 Gbps", 10000.0),
        ("500 Mbps", 500.0),
        ("Up to 250 Mbps", 250.0),
        ("2.5 Gbps", 2500.0),
        ("1G", 1000.0),
        ("300", 300.0),
        ("Unlimited", None),
        (None, None),
    ],
)
def test_parse_speed_mbps(text, mbps):
    assert core.parse_speed_mbps(text) == mbps


def test_numeric_speed_beats_lexical_order():
    # Lexically "5 Gbps" > "10 Gbps" (the legacy max() bug); numerically it is not.
    assert core.parse_speed_mbps("10 Gbps") > core.parse_speed_mbps("5 Gbps")
    assert core.parse_speed_mbps("1 Gbps") > core.parse_speed_mbps("500 Mbps")


@pytest.mark.parametrize(
    "query,expected",
    [
        ("1 Gbps", ("=", 1000.0)),
        (">= 500 Mbps", (">=", 500.0)),
        ("at least 1 Gbps", (">=", 1000.0)),
        ("under 500 Mbps", ("<", 500.0)),
        ("up to 1 Gbps", ("<=", 1000.0)),
        ("1 Gbps or more", (">=", 1000.0)),
    ],
)
def test_parse_speed_query(query, expected):
    assert core.parse_speed_query(query) == expected


def test_parse_speed_query_rejects_garbage():
    with pytest.raises(InvalidInputError):
        core.parse_speed_query("fast please")


@pytest.mark.parametrize(
    "alias,canonical",
    [("fiber", "Fiber Internet"), ("SDWAN", "SD-WAN"), ("mobile", "Business Mobile"), ("Voice", "Voice")],
)
def test_normalize_category(alias, canonical):
    assert core.normalize_category(alias) == canonical


# ---------------------------------------------------------------------------
# Database-backed operations
# ---------------------------------------------------------------------------

pytestmark_db = pytest.mark.usefixtures("seeded_db")


@pytestmark_db
def test_list_all_products():
    result = core.list_available_products()
    ids = [p.product_id for p in result.products]
    assert result.count == 16 == len(ids)
    assert ids[:3] == ["FIB-1G", "FIB-5G", "FIB-10G"]
    assert {"FIB-5G", "SDWAN-PRO", "MOB-PREM", "VOICE-UCAAS"} <= set(ids)


@pytestmark_db
def test_list_by_category_alias():
    result = core.list_available_products("sdwan")
    assert result.category == "SD-WAN"
    assert [p.product_id for p in result.products] == ["SDWAN-ESS", "SDWAN-PRO", "SDWAN-ENT"]


@pytestmark_db
def test_list_unknown_category_is_empty():
    result = core.list_available_products("Satellite")
    assert result.count == 0 and result.products == []


@pytestmark_db
@pytest.mark.parametrize("pid", ["FIB-5G", "fib-5g", "  Fib-5G "])
def test_get_product_case_insensitive(pid):
    product = core.get_product_by_id(pid)
    assert product.product_id == "FIB-5G"
    assert product.found is True
    assert product.speeds == {"download": "5 Gbps", "upload": "5 Gbps"}
    assert "99.9% uptime SLA" in product.features


@pytestmark_db
def test_get_product_has_no_price_fields():
    dumped = core.get_product_by_id("FIB-5G").model_dump()
    assert not PRICE_FIELDS & set(dumped)


@pytestmark_db
def test_get_product_not_found():
    with pytest.raises(ProductNotFoundError):
        core.get_product_by_id("NOPE-1")


@pytestmark_db
def test_search_by_technology_case_insensitive():
    result = core.search_products_by_criteria(technology="fttp")
    assert [p.product_id for p in result.products] == ["FIB-1G", "FIB-5G", "FIB-10G"]


@pytestmark_db
def test_search_by_exact_speed_is_numeric():
    result = core.search_products_by_criteria(speed="1000 Mbps")
    assert {p.product_id for p in result.products} == {"FIB-1G", "COAX-1G"}
    assert result.criteria.speed_mbps == 1000.0


@pytestmark_db
def test_search_by_speed_range_and_technology():
    result = core.search_products_by_criteria(speed="under 1 Gbps", technology="HFC")
    assert [p.product_id for p in result.products] == ["COAX-200M", "COAX-500M"]


@pytestmark_db
def test_categories():
    result = core.get_product_categories()
    assert result.categories == sorted(
        ["Business Mobile", "Coax Internet", "Fiber Internet", "SD-WAN", "Voice"]
    )
    assert result.count == 5


@pytestmark_db
def test_compare_fastest_is_numeric():
    result = core.compare_products(["FIB-1G", "FIB-5G", "FIB-10G"])
    assert result.fastest_product_id == "FIB-10G"
    assert "FIB-10G" in result.recommendation
    assert result.products_compared == 3
    assert result.comparison.comparison_table.uptime_sla[2] == "99.95% uptime SLA"


@pytestmark_db
def test_compare_mixed_units_and_case():
    result = core.compare_products(["coax-500m", "COAX-1G"])
    assert result.fastest_product_id == "COAX-1G"


@pytestmark_db
def test_compare_reports_not_found():
    result = core.compare_products(["FIB-1G", "FIB-5G", "BOGUS"])
    assert result.not_found == ["BOGUS"]
    assert result.products_compared == 2


@pytestmark_db
@pytest.mark.parametrize("ids", [["FIB-1G"], ["FIB-1G", "fib-1g"], [f"X{i}" for i in range(6)]])
def test_compare_count_limits(ids):
    with pytest.raises(InvalidInputError):
        core.compare_products(ids)


@pytestmark_db
def test_compare_all_unknown():
    with pytest.raises(ProductNotFoundError):
        core.compare_products(["A-1", "B-2"])


@pytestmark_db
def test_alternatives_faster_sorted_by_speed():
    result = core.suggest_alternatives("coax-500m", "faster")
    ids = [a.product_id for a in result.alternatives]
    assert ids[-1] == "FIB-10G"
    assert "COAX-200M" not in ids and "COAX-500M" not in ids
    assert result.base_product.product_id == "COAX-500M"


@pytestmark_db
def test_alternatives_fastest_has_none_faster():
    assert core.suggest_alternatives("FIB-10G", "faster").count == 0


@pytestmark_db
def test_alternatives_similar_and_default():
    similar = core.suggest_alternatives("FIB-1G", "similar")
    assert [a.product_id for a in similar.alternatives] == ["FIB-5G", "FIB-10G"]
    default = core.suggest_alternatives("VOICE-BAS")
    assert default.criteria == "general"
    assert {a.product_id for a in default.alternatives} == {"VOICE-STD", "VOICE-ENT", "VOICE-UCAAS"}


@pytestmark_db
def test_alternatives_different_tech_stays_in_family():
    result = core.suggest_alternatives("FIB-1G", "different_tech")
    assert {a.product_id for a in result.alternatives} == {"COAX-200M", "COAX-500M", "COAX-1G"}


@pytestmark_db
@pytest.mark.parametrize("criteria", ["cheaper", "bogus"])
def test_alternatives_invalid_criteria(criteria):
    with pytest.raises(InvalidInputError):
        core.suggest_alternatives("FIB-1G", criteria)


@pytestmark_db
def test_best_value_overall_and_by_category():
    assert core.get_best_value_product().recommended.product_id == "FIB-10G"
    assert core.get_best_value_product("coax").recommended.product_id == "COAX-1G"
    assert core.get_best_value_product("SD-WAN").recommended.product_id == "SDWAN-ENT"
    voice = core.get_best_value_product("voice")
    assert voice.found is False


def test_knowledge_validation():
    with pytest.raises(InvalidInputError):
        core.search_product_knowledge("  ")
    with pytest.raises(InvalidInputError):
        core.search_product_knowledge("sla", top_k=11)
