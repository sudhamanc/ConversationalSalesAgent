"""Tool tests against a scratch PostgreSQL database (TEST_DATABASE_URL)."""

import uuid
from types import SimpleNamespace

from discovery_agent.tools import discovery_tools as tools

SEEDED = "VoiceStream Networks"


class FakeToolContext(SimpleNamespace):
    def __init__(self):
        super().__init__(state={})


def _unique(prefix: str) -> str:
    return f"{prefix} {uuid.uuid4().hex[:8]}"


def test_search_companies_by_name_and_address(seeded_db):
    result = tools.search_companies(company_name="voicestream networks.", city="New York")
    assert result["found"] == 1
    company = result["companies"][0]
    assert company["company_name"] == SEEDED
    assert company["address"]["street"] == "456 Park Avenue"
    assert company["address"]["state"] == "NY"
    assert company["address"]["zip_code"] == "10001"
    assert company["customer_status"] == "Prospect"
    assert company["customer_id"]


def test_search_companies_not_found(seeded_db):
    result = tools.search_companies(company_name=_unique("No Such Company"))
    assert result["found"] == 0
    assert result["companies"] == []


def test_search_companies_filters(seeded_db):
    result = tools.search_companies(industry="telecom", region="Northeast")
    assert result["found"] >= 1
    assert all(c["region"] == "Northeast" for c in result["companies"])


def test_get_company_profile_sets_customer_context(seeded_db):
    ctx = FakeToolContext()
    profile = tools.get_company_profile(SEEDED, tool_context=ctx)
    assert profile["company_name"] == SEEDED
    assert profile["advertising_spend"]["total"] == 246197
    assert profile["advertising_spend"]["primary_agency"] == "Carat"
    cc = ctx.state["customer_context"]
    assert cc["customer_id"] == profile["customer_id"]
    assert cc["company_name"] == SEEDED
    assert cc["address"]["street"] == "456 Park Avenue"
    assert cc["address"]["city"] == "New York"
    assert cc["address"]["zip_code"] == "10001"


def test_get_company_profile_not_found(seeded_db):
    ctx = FakeToolContext()
    result = tools.get_company_profile(_unique("Missing Co"), tool_context=ctx)
    assert "error" in result
    assert "customer_context" not in ctx.state


def test_get_contact_personas(seeded_db):
    result = tools.get_contact_personas(SEEDED)
    assert result["company_name"] == SEEDED
    assert any(c["email"] == "c11@ex.com" for c in result["economic_buyers"])


def test_add_new_company_writes_row_and_customer_context(seeded_db):
    name = _unique("Test Pizza Shop")
    ctx = FakeToolContext()
    result = tools.add_new_company(
        company_name=name, industry="Restaurant/Food Service", region="Northeast",
        street="123 Main St", city="Boston", state="MA", zip_code="02101",
        address_line2="Suite 4", products_of_interest="Internet", tool_context=ctx,
    )
    assert result["success"] is True, result
    customer_id = result["customer_id"]
    assert customer_id.startswith("CUST-")

    row = seeded_db.fetch_one(
        'SELECT "Street", "City", "State", zip_code, "Industry", "Website", customer_id '
        'FROM accounts WHERE "Company Name" = %s', (name,)
    )
    assert row == {
        "Street": "123 Main St", "City": "Boston", "State": "MA", "zip_code": "02101",
        "Industry": "Restaurant/Food Service", "Website": "N/A", "customer_id": customer_id,
    }
    assert ctx.state["customer_context"] == {
        "customer_id": customer_id,
        "company_name": name,
        "address": {"street": "123 Main St", "address_line2": "Suite 4", "city": "Boston",
                    "state": "MA", "zip_code": "02101"},
    }

    duplicate = tools.add_new_company(
        company_name=name, industry="x", region="Northeast", street="1 A St",
        city="Boston", state="MA", zip_code="02101", tool_context=FakeToolContext(),
    )
    assert duplicate["success"] is False
    assert "already exists" in duplicate["message"]


def test_update_company_contacts_insights_and_bant(seeded_db):
    name = _unique("Test Law Firm")
    assert tools.add_new_company(
        company_name=name, industry="Legal Services", region="West",
        street="9 Oak Ave", city="Los Angeles", state="CA", zip_code="90001",
    )["success"]

    upd = tools.update_company_info(name, website="www.example.com")
    assert upd["success"] is True and upd["fields_updated"] == ["website"]
    assert tools.update_company_info(name)["success"] is False

    assert tools.add_new_contact(name, "Max", "Owner", "Economic Buyer", "max@example.com", "555-0100")["success"]
    assert tools.update_contact_info(name, "Max", phone="555-0199")["success"]
    personas = tools.get_contact_personas(name)
    assert personas["economic_buyers"][0]["phone"] == "555-0199"

    assert tools.add_or_update_insights(name, buying_signals="funding round")["success"]
    assert tools.add_or_update_insights(name, buying_signals="expansion", pain_points="slow wifi")["success"]
    insights = seeded_db.fetch_all('SELECT * FROM insights WHERE "Company Name" = %s', (name,))
    assert len(insights) == 1 and insights[0]["Buying Signals"] == "expansion"

    opp = tools.create_opportunity_from_bant(
        name, "Internet Service - New Location", budget="Approved", authority="Confirmed",
        need="High", timeline_days=30, total_mrc=499.5,
    )
    assert opp["success"] is True
    assert opp["bant_scores"]["score_0to100"] == 100.0
    assert opp["bant_scores"]["priority_bucket"] == "A (High)"
    assert opp["bant_scores"]["data_gaps"] == ""

    intent = tools.get_customer_intent(name)
    assert intent["buying_signals"] == "expansion"
    assert intent["opportunities"][0]["bant_priority"] == "A (High)"
    assert tools.search_by_intent_signals("expansion")["found"] >= 1
    assert tools.get_high_priority_opportunities(limit=5)["found"] >= 1


def test_check_customer_state(seeded_db):
    customer_id = tools.search_companies(company_name=SEEDED)["companies"][0]["customer_id"]
    state = tools.check_customer_state(customer_id)
    assert state["customer_id"] == customer_id
    assert state["account"]["company_name"] == SEEDED
    for key in ("active_quotes", "pending_orders", "payments", "fulfillments"):
        assert isinstance(state[key], list)
