"""PostgreSQL queries for the discovery domain (accounts, contacts, spend, insights, actions, opportunities).

All column names of the legacy discovery tables are quoted, case-sensitive
identifiers (``"Company Name"``, ``"Street"``, ...). Rows are returned as dicts
keyed by those column names. The schema lives in ``db/migrations``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from psycopg import errors as pg_errors

from sales_common import db


def normalize_company_name(name: Optional[str]) -> Optional[str]:
    """Strip trailing punctuation and normalize whitespace for fuzzy matching.

    'SpinDrift Inc.' -> 'SpinDrift Inc'
    'SpinDrift  Inc' -> 'SpinDrift Inc'
    """
    if not name:
        return name
    name = name.strip().rstrip(".,;")
    return re.sub(r"\s+", " ", name)


# ==================== READ OPERATIONS ====================

_ACCOUNT_COLUMNS = (
    '"Company Name", "Parent Company", "Industry", "Territory/Region", '
    '"Street", address_line2, "City", "State", zip_code, "Website", "Existing Customer", '
    '"Current Products", "Products of Interest", customer_id'
)


def search_companies(
    company_name: Optional[str] = None,
    industry: Optional[str] = None,
    region: Optional[str] = None,
    customer_status: Optional[str] = None,
    street: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search accounts by name, address, industry, region or customer status (compound match).

    Matching is case-insensitive substring matching (SQLite ``LIKE`` semantics).
    """
    query = f"SELECT {_ACCOUNT_COLUMNS} FROM accounts WHERE 1=1"
    conditions: list[str] = []
    params: list[Any] = []

    if company_name:
        conditions.append('"Company Name" ILIKE %s')
        params.append(f"%{normalize_company_name(company_name)}%")
    if street:
        conditions.append('"Street" ILIKE %s')
        params.append(f"%{street}%")
    if city:
        conditions.append('"City" ILIKE %s')
        params.append(f"%{city}%")
    if state:
        conditions.append('"State" ILIKE %s')
        params.append(f"%{state}%")
    if industry:
        conditions.append('"Industry" ILIKE %s')
        params.append(f"%{industry}%")
    if region:
        conditions.append('"Territory/Region" ILIKE %s')
        params.append(f"%{region}%")
    if customer_status:
        conditions.append('"Existing Customer" = %s')
        params.append(customer_status)

    if conditions:
        query += " AND " + " AND ".join(conditions)
    return db.fetch_all(query, params)


def get_company_details(company_name: str) -> Optional[Dict[str, Any]]:
    """Account row joined with advertising spend for an exact company name."""
    query = """
    SELECT a."Company Name", a."Parent Company", a."Industry", a."Territory/Region",
           a."Street", a.address_line2, a."City", a."State", a.zip_code, a."Website",
           a."Existing Customer", a."Current Products", a."Products of Interest",
           a.customer_id,
           s."Estimated Annual Spend", s."Digital", s."Programmatic",
           s."TV", s."Audio", s."OOH", s."Search", s."Social", s."Primary Agency"
    FROM accounts a
    LEFT JOIN spend s ON a."Company Name" = s."Company Name"
    WHERE a."Company Name" = %s
    LIMIT 1
    """
    return db.fetch_one(query, (normalize_company_name(company_name),))


def get_contacts_for_company(company_name: str) -> List[Dict[str, Any]]:
    query = """
    SELECT "Name", "Title", "Role in Decision Making", "Email", "Phone", "Notes"
    FROM contacts
    WHERE "Company Name" = %s
    """
    return db.fetch_all(query, (company_name,))


def get_opportunities_for_company(company_name: str) -> List[Dict[str, Any]]:
    query = """
    SELECT "Opportunity Name", "Stage", "Total MRC (Est)", "Budget", "Authority", "Need",
           "Timeline (days)", "Target Close Date", "Next Step",
           "BANT_Score_0to100", "BANT_Priority_Bucket", "BANT_Data_Gaps"
    FROM opportunities
    WHERE "Company Name" = %s
    ORDER BY "BANT_Score_0to100" DESC NULLS LAST
    """
    return db.fetch_all(query, (company_name,))


def get_insights_for_company(company_name: str) -> Optional[Dict[str, Any]]:
    query = """
    SELECT "Buying Signals", "Pain Points", "Recommended Positioning"
    FROM insights
    WHERE "Company Name" = %s
    LIMIT 1
    """
    return db.fetch_one(query, (company_name,))


def get_actions_for_company(company_name: str) -> Optional[Dict[str, Any]]:
    query = """
    SELECT "Owner", "Priority", "Initial Outreach Date", "Follow-Up Cadence"
    FROM actions
    WHERE "Company Name" = %s
    LIMIT 1
    """
    return db.fetch_one(query, (company_name,))


def get_high_priority_opportunities(limit: int = 10) -> List[Dict[str, Any]]:
    query = """
    SELECT o."Company Name", o."Opportunity Name", o."Stage", o."Total MRC (Est)",
           o."BANT_Score_0to100", o."BANT_Priority_Bucket", o."Target Close Date"
    FROM opportunities o
    WHERE o."BANT_Priority_Bucket" IN ('A (High)', 'B (Medium)')
    ORDER BY o."BANT_Score_0to100" DESC NULLS LAST
    LIMIT %s
    """
    return db.fetch_all(query, (limit,))


def search_by_intent_signals(signal_keyword: str) -> List[Dict[str, Any]]:
    query = """
    SELECT a."Company Name", a."Industry", a."Territory/Region",
           a."Street", a."City", a."State",
           a."Existing Customer", a."Current Products", a."Products of Interest",
           i."Buying Signals", i."Pain Points", i."Recommended Positioning"
    FROM accounts a
    JOIN insights i ON a."Company Name" = i."Company Name"
    WHERE i."Buying Signals" ILIKE %s OR i."Pain Points" ILIKE %s
    """
    keyword = f"%{signal_keyword}%"
    return db.fetch_all(query, (keyword, keyword))


# ==================== WRITE OPERATIONS ====================

def _generate_customer_id(conn) -> str:
    """Generate a customer_id in format CUST-YYYYMMDD-XXX (legacy algorithm)."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    row = conn.execute(
        "SELECT customer_id FROM accounts WHERE customer_id IS NOT NULL "
        "ORDER BY customer_id DESC LIMIT 1"
    ).fetchone()
    next_idx = 1
    if row and row["customer_id"]:
        try:
            next_idx = int(row["customer_id"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            next_idx = 1
    return f"CUST-{today}-{next_idx:03d}"


def add_company(
    company_name: str,
    industry: str,
    region: str,
    street: str,
    city: str,
    state: str,
    website: str,
    parent_company: Optional[str] = None,
    existing_customer: str = "N",
    current_products: Optional[str] = None,
    products_of_interest: Optional[str] = None,
    zip_code: Optional[str] = None,
    address_line2: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert an account row. Returns ``{success, customer_id, message}``."""
    now = db.now_iso()
    query = """
    INSERT INTO accounts (
        "Company Name", "Parent Company", "Industry", "Territory/Region",
        "Street", address_line2, "City", "State", zip_code, "Website", "Existing Customer",
        "Current Products", "Products of Interest",
        customer_id, created_at, updated_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        with db.transaction() as conn:
            # Serialize customer_id allocation across concurrent registrations.
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('discovery.customer_id'))")
            customer_id = _generate_customer_id(conn)
            rows = conn.execute(
                query,
                (
                    company_name, parent_company, industry, region,
                    street, address_line2, city, state, zip_code, website, existing_customer,
                    current_products, products_of_interest,
                    customer_id, now, now,
                ),
            ).rowcount
    except pg_errors.UniqueViolation:
        return {"success": False, "customer_id": None,
                "message": f"Company '{company_name}' already exists"}
    except pg_errors.NotNullViolation as exc:
        column = getattr(exc.diag, "column_name", None) or "a required field"
        return {"success": False, "customer_id": None,
                "message": f"Missing required field: {column}"}
    if rows > 0:
        return {"success": True, "customer_id": customer_id,
                "message": f"Company '{company_name}' added with customer_id {customer_id}"}
    return {"success": False, "customer_id": None, "message": "Insert failed"}


_COMPANY_FIELDS = {
    "industry": '"Industry"',
    "region": '"Territory/Region"',
    "street": '"Street"',
    "address_line2": "address_line2",
    "city": '"City"',
    "state": '"State"',
    "zip_code": "zip_code",
    "website": '"Website"',
    "parent_company": '"Parent Company"',
    "existing_customer": '"Existing Customer"',
    "current_products": '"Current Products"',
    "products_of_interest": '"Products of Interest"',
}


def update_company(company_name: str, **kwargs: Any) -> bool:
    """Update account fields (keys of ``_COMPANY_FIELDS``). True when a row changed."""
    updates, values = [], []
    for key, value in kwargs.items():
        if key in _COMPANY_FIELDS:
            updates.append(f"{_COMPANY_FIELDS[key]} = %s")
            values.append(value)
    if not updates:
        return False
    updates.append("updated_at = %s")
    values.append(db.now_iso())
    values.append(company_name)
    query = f'UPDATE accounts SET {", ".join(updates)} WHERE "Company Name" = %s'
    return db.execute(query, values) > 0


def add_contact(
    company_name: str,
    contact_name: str,
    title: str,
    role_in_decision_making: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    query = """
    INSERT INTO contacts (
        "Company Name", "Name", "Title", "Role in Decision Making",
        "Email", "Phone", "Notes", created_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        rows = db.execute(query, (
            company_name, contact_name, title, role_in_decision_making,
            email, phone, notes, db.now_iso(),
        ))
    except pg_errors.IntegrityError:
        return False
    return rows > 0


_CONTACT_FIELDS = {
    "title": '"Title"',
    "role_in_decision_making": '"Role in Decision Making"',
    "email": '"Email"',
    "phone": '"Phone"',
    "notes": '"Notes"',
}


def update_contact(company_name: str, contact_name: str, **kwargs: Any) -> bool:
    updates, values = [], []
    for key, value in kwargs.items():
        if key in _CONTACT_FIELDS:
            updates.append(f"{_CONTACT_FIELDS[key]} = %s")
            values.append(value)
    if not updates:
        return False
    values.extend([company_name, contact_name])
    query = f'UPDATE contacts SET {", ".join(updates)} WHERE "Company Name" = %s AND "Name" = %s'
    return db.execute(query, values) > 0


def add_insight(
    company_name: str,
    buying_signals: Optional[str] = None,
    pain_points: Optional[str] = None,
    recommended_positioning: Optional[str] = None,
) -> bool:
    """Replace the insights for a company (legacy ``INSERT OR REPLACE``).

    ``insights`` has no primary key, so the row is updated when present and
    inserted otherwise.
    """
    values = (buying_signals, pain_points, recommended_positioning, company_name)
    with db.transaction() as conn:
        rows = conn.execute(
            'UPDATE insights SET "Buying Signals" = %s, "Pain Points" = %s, '
            '"Recommended Positioning" = %s WHERE "Company Name" = %s',
            values,
        ).rowcount
        if rows == 0:
            rows = conn.execute(
                'INSERT INTO insights ("Buying Signals", "Pain Points", '
                '"Recommended Positioning", "Company Name") VALUES (%s, %s, %s, %s)',
                values,
            ).rowcount
    return rows > 0
