"""Regression tests for Discovery tool bugs (scratch PostgreSQL via TEST_DATABASE_URL)."""

import uuid
from datetime import datetime, timezone

import pytest

from discovery_agent.tools import db_tools
from discovery_agent.tools import discovery_tools as tools


class _Rollback(Exception):
    """Raised at the end of a test transaction so its rows are discarded."""


def _unique(prefix: str) -> str:
    return f"{prefix} {uuid.uuid4().hex[:8]}"


def _insert_account(conn, customer_id: str) -> None:
    conn.execute(
        'INSERT INTO accounts ("Company Name", zip_code, customer_id) VALUES (%s, %s, %s)',
        (_unique("Id Seed Co"), "00000", customer_id),
    )


def _today_prefix() -> str:
    return f"CUST-{datetime.now(timezone.utc):%Y%m%d}-"


# ---- 1. customer_id uses today's counter only -------------------------------

def test_customer_id_ignores_other_dates(seeded_db):
    prefix = _today_prefix()
    with pytest.raises(_Rollback):
        with seeded_db.transaction() as conn:
            # Ids from other dates, including a later date and a large counter,
            # must not influence today's counter.
            _insert_account(conn, "CUST-20200101-950")
            _insert_account(conn, "CUST-29991231-777")
            conn.execute("DELETE FROM accounts WHERE customer_id LIKE %s", (prefix + "%",))
            assert db_tools._generate_customer_id(conn) == f"{prefix}001"

            _insert_account(conn, f"{prefix}001")
            _insert_account(conn, f"{prefix}007")
            assert db_tools._generate_customer_id(conn) == f"{prefix}008"
            raise _Rollback


def test_customer_id_widens_past_999(seeded_db):
    prefix = _today_prefix()
    with pytest.raises(_Rollback):
        with seeded_db.transaction() as conn:
            conn.execute("DELETE FROM accounts WHERE customer_id LIKE %s", (prefix + "%",))
            _insert_account(conn, f"{prefix}999")
            assert db_tools._generate_customer_id(conn) == f"{prefix}1000"
            _insert_account(conn, f"{prefix}1000")
            assert db_tools._generate_customer_id(conn) == f"{prefix}1001"
            raise _Rollback


def test_add_new_company_uses_todays_counter(seeded_db):
    prefix = _today_prefix()
    rows = seeded_db.fetch_all(
        "SELECT customer_id FROM accounts WHERE customer_id LIKE %s", (prefix + "%",)
    )
    current = max((int(r["customer_id"][len(prefix):]) for r in rows), default=0)
    result = tools.add_new_company(
        company_name=_unique("Counter Co"), industry="Retail", region="Northeast",
        street="1 Elm St", city="Boston", state="MA", zip_code="02101",
    )
    assert result["success"] is True, result
    assert result["customer_id"] == f"{prefix}{current + 1:03d}"


# ---- 2. add_new_contact requires an existing company ------------------------

def test_add_new_contact_unknown_company_fails(seeded_db):
    name = _unique("Ghost Company")
    result = tools.add_new_contact(name, "Pat", "CEO", "Economic Buyer", "pat@example.com")
    assert result["success"] is False
    assert "not found" in result["error"]
    count = seeded_db.fetch_one(
        'SELECT count(*) AS n FROM contacts WHERE "Company Name" = %s', (name,)
    )
    assert count["n"] == 0


def test_add_new_contact_matches_company_case_insensitively(seeded_db):
    name = _unique("Case Co")
    assert tools.add_new_company(
        company_name=name, industry="Retail", region="West",
        street="2 Pine St", city="Denver", state="CO", zip_code="80202",
    )["success"]
    result = tools.add_new_contact(name.upper(), "Lee", "CTO", "Technical Buyer", "lee@example.com")
    assert result["success"] is True, result
    assert result["company_name"] == name
    personas = tools.get_contact_personas(name)
    assert personas["technical_buyers"][0]["name"] == "Lee"


def test_add_new_contact_rejects_duplicates(seeded_db):
    """Regression: contacts had no uniqueness, so the same person could be added repeatedly."""
    name = _unique("Dup Contact Co")
    assert tools.add_new_company(
        company_name=name, industry="Retail", region="West",
        street="3 Oak St", city="Denver", state="CO", zip_code="80202",
    )["success"]
    first = tools.add_new_contact(name, "Pat Doe", "CIO", "Decision Maker", "pat@example.com")
    assert first["success"] is True and first["duplicate"] is False
    same_name = tools.add_new_contact(name, "pat doe", "CIO", "Decision Maker")
    same_email = tools.add_new_contact(name, "Patricia Doe", "CIO", "Decision Maker", "PAT@example.com")
    for result in (same_name, same_email):
        assert result["success"] is False and result["duplicate"] is True, result
    count = seeded_db.fetch_one(
        'SELECT count(*) AS n FROM contacts WHERE "Company Name" = %s', (name,)
    )["n"]
    assert count == 1
    other = tools.add_new_contact(name, "Sam Roe", "CFO", "Economic Buyer", "sam@example.com")
    assert other["success"] is True


# ---- 3. duplicate opportunity detection -------------------------------------

def test_create_opportunity_duplicate_is_not_inserted(seeded_db):
    name = _unique("Dup Opp Co")
    assert tools.add_new_company(
        company_name=name, industry="Retail", region="West",
        street="3 Oak St", city="Austin", state="TX", zip_code="73301",
    )["success"]
    first = tools.create_opportunity_from_bant(name, "Internet Service", budget="Approved")
    assert first["success"] is True

    dup = tools.create_opportunity_from_bant(name.lower(), "internet SERVICE ", need="High")
    assert dup["success"] is False
    assert dup["duplicate"] is True
    assert "already exists" in dup["message"]
    assert dup["opportunity_name"] == "Internet Service"

    rows = seeded_db.fetch_all(
        'SELECT 1 FROM opportunities WHERE "Company Name" = %s', (name,)
    )
    assert len(rows) == 1

    other = tools.create_opportunity_from_bant(name, "SD-WAN Upgrade")
    assert other["success"] is True


# ---- 4. NULL columns render as 'N/A' ----------------------------------------

def test_null_columns_render_as_na(seeded_db):
    name = _unique("Null Co")
    seeded_db.execute(
        'INSERT INTO accounts ("Company Name", "Industry", "Territory/Region", "Street", '
        '"City", "State", zip_code, "Website", customer_id) '
        "VALUES (%s, 'Retail', 'West', NULL, '', NULL, '94105', 'N/A', NULL)",
        (name,),
    )
    seeded_db.execute(
        'INSERT INTO contacts ("Company Name", "Name", "Title", "Role in Decision Making", '
        '"Email", "Phone") VALUES (%s, %s, %s, %s, NULL, %s)',
        (name, "Ann", "CFO", "Economic Buyer", ""),
    )
    seeded_db.execute(
        'INSERT INTO insights ("Company Name", "Buying Signals", "Pain Points", '
        '"Recommended Positioning") VALUES (%s, %s, NULL, NULL)',
        (name, "nullsignal" + uuid.uuid4().hex[:6]),
    )

    company = tools.search_companies(company_name=name)["companies"][0]
    assert company["address"] == {
        "street": "N/A", "address_line2": "", "city": "N/A", "state": "N/A", "zip_code": "94105",
    }
    profile = tools.get_company_profile(name)
    assert profile["address"]["street"] == "N/A"
    assert profile["address"]["state"] == "N/A"

    buyer = tools.get_contact_personas(name)["economic_buyers"][0]
    assert buyer["email"] == "N/A"
    assert buyer["phone"] == "N/A"

    intent = tools.get_customer_intent(name)
    assert intent["pain_points"] == "None identified"
    assert intent["recommended_positioning"] == "None specified"

    signal = seeded_db.fetch_one(
        'SELECT "Buying Signals" FROM insights WHERE "Company Name" = %s', (name,)
    )["Buying Signals"]
    match = tools.search_by_intent_signals(signal)["companies"][0]
    assert match["pain_points"] == "N/A"
    assert match["recommended_positioning"] == "N/A"


def test_val_helper():
    assert tools._val({"a": None}, "a") == "N/A"
    assert tools._val({"a": "  "}, "a") == "N/A"
    assert tools._val({}, "a", "x") == "x"
    assert tools._val(None, "a") == "N/A"
    assert tools._val({"a": 0}, "a") == 0
    assert tools._val({"a": "v"}, "a") == "v"
