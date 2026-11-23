"""A2UI surfaces built from tool results (spec: generative-ui).

Surfaces are checked against the exported catalog
(``server/a2ui/catalog.json``, from ``client/scripts/export_a2ui_catalog.mjs``):
component names, allowed props, required props and enum values.
"""

import json
import re
from pathlib import Path

import pytest

from api.a2ui import ROOT_ID, SEND_FUNCTION, build_surface

CATALOG = json.loads((Path(__file__).resolve().parents[1] / "server" / "a2ui" / "catalog.json").read_text())
COMPONENTS = CATALOG["components"]

QUOTE = {
    "success": True,
    "offer_id": "OFF-1",
    "company_name": "Beacon Wealth Advisors",
    "term_months": 24,
    "items": [
        {"product_id": "FIB-1G", "product_name": "Fiber 1 Gbps", "quantity": 1,
         "price_points": {"unit_price": 400.0, "extended_price": 400.0}, "final_price": 380.0},
        {"product_id": "VOICE-STD", "product_name": "Business Voice Standard", "quantity": 2,
         "price_points": {"unit_price": 40.0, "extended_price": 80.0}, "final_price": 70.0},
    ],
    "total_discount": 30.0,
    "monthly_total": 450.0,
    "yearly_total": 5400.0,
    "expires_at": "2026-12-23T00:00:00Z",
}
SERVICEABLE = {
    "serviceable": True,
    "address": {"street": "234 Charles Street", "city": "Baltimore", "state": "MD", "zip_code": "21201"},
    "infrastructure_type": "FTTP",
    "max_speed_mbps": 5000,
    "service_zone": "BAL-1",
    "estimated_install_days": 7,
    "available_product_categories": ["Internet", "Voice", "SD-WAN", "Mobile"],
    "available_products": ["FIB-1G", "FIB-5G"],
}
PRODUCTS = {
    "products": [
        {"product_id": "FIB-1G", "product_name": "Fiber 1 Gbps", "category": "Internet", "technology": "FTTP",
         "speeds": {"download": "1 Gbps", "upload": "1 Gbps"}},
        {"product_id": "FIB-5G", "product_name": "Fiber 5 Gbps", "category": "Internet", "technology": "FTTP",
         "speeds": {"download": "5 Gbps", "upload": "5 Gbps"}},
        {"product_id": "COAX-500M", "product_name": "Cable 500 Mbps", "category": "Internet", "technology": "HFC",
         "speeds": {"download": "500 Mbps", "upload": "50 Mbps"}},
    ],
    "count": 3,
    "category": "Internet",
}
COMPARE = {
    "comparison": {
        "products": ["FIB-1G", "FIB-5G"],
        "comparison_table": {
            "product_name": ["Fiber 1 Gbps", "Fiber 5 Gbps"],
            "technology": ["FTTP", "FTTP"],
            "download_speed": ["1 Gbps", "5 Gbps"],
            "upload_speed": ["1 Gbps", "5 Gbps"],
            "uptime_sla": ["99.9%", "99.95%"],
            "key_features": [["Static IP"], ["Static IP", "Priority support"]],
        },
    },
    "products_compared": 2,
    "not_found": [],
    "fastest_product_id": "FIB-5G",
    "recommendation": "Fiber 5 Gbps suits heavy cloud use.",
}


def _mcp(payload):
    """An MCP CallToolResult as it crosses A2A (structuredContent + text)."""
    return {"content": [{"type": "text", "text": json.dumps(payload)}], "structuredContent": payload, "isError": False}


def _nodes(surface):
    ops = surface["operations"]
    assert ops[0]["version"] == "1.0"
    return ops[0]["createSurface"]["components"]


def _enum_ok(schema, value):
    """True unless the prop schema has string enums and ``value`` is a string outside all of them."""
    enums = [opt.get("enum") for opt in schema.get("anyOf", []) if isinstance(opt, dict) and opt.get("enum")]
    if schema.get("enum"):
        enums.append(schema["enum"])
    return not enums or not isinstance(value, str) or any(value in e for e in enums)


def _assert_valid(surface):
    nodes = _nodes(surface)
    ids = [n["id"] for n in nodes]
    assert len(ids) == len(set(ids)), "component ids are unique"
    assert ROOT_ID in ids
    for node in nodes:
        name = node["component"]
        assert name in COMPONENTS, f"{name} is not in the standard catalog"
        schema = COMPONENTS[name]
        props = schema["properties"]
        for key, value in node.items():
            if key == "id":
                continue
            assert key in props, f"{name}.{key} is not a catalog prop"
            assert _enum_ok(props[key], value), f"{name}.{key}={value!r} is not an allowed value"
        for required in schema.get("required", []):
            assert required in node, f"{name} is missing required prop {required}"
        for child in node.get("children", []):
            assert child in ids, f"{name} child {child} does not exist"


def _buttons(surface):
    return [n for n in _nodes(surface) if n["component"] == "Button"]


def _all_text(surface):
    return json.dumps(_nodes(surface))


@pytest.mark.parametrize("tool,response,kind", [
    ("generate_offer_quote", QUOTE, "quote"),
    ("find_best_bundle_offer", QUOTE, "quote"),
    ("get_quote_details", {"success": True, "quote": QUOTE}, "quote"),
    ("check_service_availability", _mcp(SERVICEABLE), "serviceability"),
    ("check_service_availability", _mcp({"serviceable": False, "address": SERVICEABLE["address"],
                                          "reason": "Outside the coverage area"}), "serviceability"),
    ("list_available_products", _mcp(PRODUCTS), "products"),
    ("search_products_by_criteria", _mcp({**PRODUCTS, "criteria": {"technology": "FTTP"}}), "products"),
    ("compare_products", _mcp(COMPARE), "products"),
])
def test_surfaces_are_valid_against_the_catalog(tool, response, kind):
    surface = build_surface(tool, response)
    assert surface is not None and surface["kind"] == kind
    assert surface["surface_id"].startswith(f"{tool}-")
    assert surface["operations"][0]["createSurface"]["surfaceId"] == surface["surface_id"]
    _assert_valid(surface)
    _assert_buttons(surface)


def _assert_buttons(surface, required=True):
    buttons = _buttons(surface)
    if required:
        assert buttons, "this surface offers a next step"
    for button in buttons:
        call = button["onClick"]["functionCall"]
        assert call["@call"] == SEND_FUNCTION
        assert call["args"]["message"].strip()
        assert "[" not in call["args"]["message"], "a click sends immediately, so no placeholders"
    if required:
        assert any(b.get("variant") == "primary" for b in buttons)


def test_quote_shows_items_and_totals():
    text = _all_text(build_surface("generate_offer_quote", QUOTE))
    for expected in ("Fiber 1 Gbps", "Business Voice Standard", "$450.00", "$5,400.00", "24 months", "OFF-1",
                     "I'll take quote OFF-1 (24 months). Please place my order."):
        assert expected in text


def test_serviceability_shows_technology_and_speed():
    text = _all_text(build_surface("check_service_availability", _mcp(SERVICEABLE)))
    assert "Service is available" in text and "FTTP" in text and "5,000 Mbps" in text
    assert "234 Charles Street, Baltimore, MD 21201" in text


def test_product_surfaces_have_no_prices():
    for tool, data in (("list_available_products", PRODUCTS), ("compare_products", COMPARE)):
        text = _all_text(build_surface(tool, _mcp(data)))
        assert not re.search(r"\$\s?\d", text), f"{tool} surface shows a price"
        assert "price" not in text.lower()


def test_compare_quotes_the_fastest_first():
    buttons = _buttons(build_surface("compare_products", _mcp(COMPARE)))
    assert buttons[0]["onClick"]["functionCall"]["args"]["message"] == "I'd like a quote for Fiber 5 Gbps"


def test_surface_id_is_stable_for_the_same_result():
    assert build_surface("generate_offer_quote", QUOTE)["surface_id"] == build_surface("generate_offer_quote", dict(QUOTE))["surface_id"]
    assert build_surface("generate_offer_quote", QUOTE)["surface_id"] != build_surface(
        "generate_offer_quote", {**QUOTE, "offer_id": "OFF-2"})["surface_id"]


@pytest.mark.parametrize("tool,response", [
    ("generate_offer_quote", {"success": False, "error": "quote_not_saved"}),
    ("generate_offer_quote", {"total_price": 10.0}),
    ("get_quote_details", {"success": False, "error": "Quote OFF-9 not found"}),
    ("check_service_availability", {"content": [{"type": "text", "text": "boom"}], "isError": True}),
    ("check_service_availability", _mcp({"valid": False})),
    ("list_available_products", _mcp({"products": [], "count": 0})),
    ("compare_products", _mcp({"comparison": {"products": ["FIB-1G"], "comparison_table": {"product_name": ["x"]}}})),
    ("get_cart", {"success": True, "cart": {"items": []}}),
    ("generate_offer_quote", "not a dict"),
])
def test_unusable_results_give_no_surface(tool, response):
    assert build_surface(tool, response) is None


# --- guided checkout surfaces (spec: guided-checkout) ------------------------

STATE = {
    "serviceability_context": {"is_serviceable": True, "available_products": ["FIB-1G", "FIB-5G"]},
    "order_context": {"order_id": "ORD-1", "total_amount": 224.1, "status": "pending_payment"},
}
CATALOG_16 = {"products": [
    {"product_id": pid, "product_name": name, "category": cat, "technology": tech,
     "speeds": {"download": "1 Gbps", "upload": "1 Gbps"}}
    for pid, name, cat, tech in [
        ("FIB-1G", "Business Fiber 1 Gbps", "Fiber Internet", "FTTP"),
        ("FIB-5G", "Business Fiber 5 Gbps", "Fiber Internet", "FTTP"),
        ("FIB-10G", "Business Fiber 10 Gbps", "Fiber Internet", "FTTP"),
        ("COAX-200M", "Business Internet 200 Mbps", "Coax Internet", "HFC"),
        ("VOICE-STD", "Business Voice Standard", "Voice", "VoIP"),
        ("MOB-UNL", "Business Mobile Unlimited", "Business Mobile", "5G"),
    ]
], "count": 6}
SLOTS = {"success": True, "service_address": "314 Main Street, Philadelphia, PA 19103", "available_slots": [
    {"date": "2026-11-27", "window": "AM", "start_time": "08:00", "end_time": "12:00"},
    {"date": "2026-11-27", "window": "PM", "start_time": "13:00", "end_time": "17:00"},
    {"date": "2026-11-30", "window": "AM", "start_time": "08:00", "end_time": "12:00"},
]}
CART = {"success": True, "cart_id": "CART-1", "cart": {"items": [
    {"service_type": "Business Fiber 1 Gbps", "price": 224.1, "quantity": 1.0, "subtotal": 224.1}],
    "total_amount": 224.1}}
METHODS = {"success": True, "customer_id": "C1", "count": 1, "payment_methods": [
    {"token": "tok_secret", "payment_type": "credit_card", "card_brand": "visa", "last_four": "1111"}]}


@pytest.mark.parametrize("tool,response,kind,needs_buttons", [
    ("add_to_cart", CART, "cart", True),
    ("get_cart", CART, "cart", True),
    ("create_order", {"success": True, "order_id": "ORD-1", "status": "pending_payment",
                      "service_type": "Business Fiber 1 Gbps", "total_amount": 224.1}, "order", False),
    ("get_order", {"success": True, "order": {"order_id": "ORD-1", "status": "paid"}}, "order", False),
    ("check_availability", SLOTS, "scheduling", True),
    ("schedule_installation", {"success": True, "appointment_id": "APT-1", "scheduled_date": "2026-11-27",
                               "window": "AM", "start_time": "08:00", "end_time": "12:00"}, "scheduling", False),
    ("get_payment_methods", METHODS, "payment", True),
    ("get_payment_methods", {"success": True, "payment_methods": [], "count": 0}, "payment", False),
    ("process_payment", {"success": True, "status": "completed", "amount": 224.1, "order_id": "ORD-1",
                         "transaction_id": "TXN-1", "payment_method_token": "tok_secret"}, "payment", False),
    ("get_product_by_id", _mcp({**CATALOG_16["products"][0], "description": "Fiber.", "features": ["SLA"],
                                "available": True, "found": True}), "products", True),
])
def test_checkout_surfaces_are_valid(tool, response, kind, needs_buttons):
    surface = build_surface(tool, response, STATE)
    assert surface is not None and surface["kind"] == kind
    _assert_valid(surface)
    _assert_buttons(surface, required=needs_buttons)
    assert "tok_" not in _all_text(surface), "tokens never reach the browser"


def test_slots_have_one_exact_button_per_slot():
    buttons = _buttons(build_surface("check_availability", SLOTS, STATE))
    messages = [b["onClick"]["functionCall"]["args"]["message"] for b in buttons]
    assert messages == [
        "Please book my installation for Friday, November 27, 2026, 8 AM–12 PM (morning).",
        "Please book my installation for Friday, November 27, 2026, 1 PM–5 PM (afternoon).",
        "Please book my installation for Monday, November 30, 2026, 8 AM–12 PM (morning).",
    ]
    assert [b["label"] for b in buttons] == ["8 AM–12 PM", "1 PM–5 PM", "8 AM–12 PM"]


def test_payment_surface_has_amount_saved_methods_and_secure_form():
    nodes = _nodes(build_surface("get_payment_methods", METHODS, STATE))
    text = json.dumps(nodes)
    assert "$224.10" in text and "ORD-1" in text
    assert [b["label"] for b in nodes if b["component"] == "Button"] == ["Pay with Visa ending 1111"]
    form = [n for n in nodes if n["component"] == "SecurePaymentForm"]
    assert form and form[0]["amount"] == "$224.10"


def test_product_list_is_filtered_to_the_address():
    text = _all_text(build_surface("list_available_products", _mcp(CATALOG_16), STATE))
    assert "Business Fiber 1 Gbps" in text and "Business Fiber 5 Gbps" in text
    assert "Fiber 10 Gbps" not in text and "Internet 200 Mbps" not in text
    assert "Business Voice Standard" in text and "Business Mobile Unlimited" in text
    assert "at your address" in text
    unfiltered = _all_text(build_surface("list_available_products", _mcp(CATALOG_16)))
    assert "Fiber 10 Gbps" in unfiltered


def test_whole_numbers_have_no_decimal_part():
    svc = build_surface("check_service_availability",
                        _mcp({**SERVICEABLE, "max_speed_mbps": 5000.0, "estimated_install_days": 5.0}))
    text = _all_text(svc)
    assert "5,000 Mbps" in text and "5 days" in text and ".0" not in text
    quote = _all_text(build_surface("generate_offer_quote", {**QUOTE, "term_months": 12.0, "items": [
        {**QUOTE["items"][0], "quantity": 1.0}]}))
    assert "12 months" in quote and '"1"' in quote and "1.0" not in quote


def test_quote_offers_the_other_contract_terms():
    buttons = _buttons(build_surface("generate_offer_quote", {**QUOTE, "term_months": 12.0}))
    by_label = {b["label"]: b["onClick"]["functionCall"]["args"]["message"] for b in buttons}
    assert by_label["24 months"] == "Please re-quote OFF-1 on a 24-month term."
    assert by_label["36 months"] == "Please re-quote OFF-1 on a 36-month term."
    assert "12 months" not in by_label and "Adjust" not in by_label
    assert by_label["Add a service"] == "I'd like to add another service to quote OFF-1 (12 months)."
    assert [b["label"] for b in buttons][0] == "Accept quote"


# --- contact card (spec: guided-checkout) ----------------------------------------

def _contact_button(surface):
    [button] = _buttons(surface)
    return button


@pytest.mark.parametrize("tool,response,then", [
    ("add_new_company", {"action": "add_company", "success": True, "customer_id": "C1", "company_name": "Crane"}, ""),
    ("create_order", {"success": False, "error": "contact_email_required", "message": "..."}, " Please place my order."),
])
def test_contact_card(tool, response, then):
    surface = build_surface(tool, response, {"customer_context": {"customer_id": "C1"}})
    assert surface["kind"] == "contact"
    _assert_valid(surface)
    create = surface["operations"][0]["createSurface"]
    assert create["dataModel"] == {"contact": {"name": "", "email": "", "phone": ""}}
    fields = {n["label"]: n["value"] for n in create["components"] if n["component"] == "TextField"}
    assert fields == {"Your name": {"@path": "/contact/name"}, "Email": {"@path": "/contact/email"},
                      "Phone (optional)": {"@path": "/contact/phone"}}
    button = _contact_button(surface)
    message = button["onClick"]["functionCall"]["args"]["message"]
    assert message["@call"] == "formatString"
    assert message["args"]["value"] == (
        "My contact details: name ${/contact/name}, email ${/contact/email}, phone ${/contact/phone}." + then)
    assert [c["condition"]["@call"] for c in button["checks"]] == ["required", "email"]


def test_no_registration_card_when_contact_is_on_file():
    state = {"customer_context": {"customer_id": "C1", "contact": {"email": "jane@crane.io"}}}
    assert build_surface("add_new_company", {"success": True, "customer_id": "C1"}, state) is None
    assert build_surface("create_order", {"success": False, "error": "order_save_failed"}) is None
