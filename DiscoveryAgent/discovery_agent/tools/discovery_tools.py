"""Discovery tools: company lookup/registration, contacts, insights, BANT opportunities.

All tools are deterministic PostgreSQL operations (``sales_common.db``) and
return JSON-serializable dicts. Tools that identify the customer write
``tool_context.state["customer_context"]``; the shared ``export_context_delta``
callback forwards that to the gateway as ``_context_update``.
"""

import functools
import logging
from typing import Any, Callable, Optional

import psycopg
from google.adk.tools.tool_context import ToolContext

from sales_common.repositories.customer_state import check_customer_state as _check_customer_state

from . import db_tools as db
from . import qualification_tools as lead_db

logger = logging.getLogger("discovery_agent.tools")


def _db_guard(func: Callable[..., dict]) -> Callable[..., dict]:
    """Return ``{"success": False, "error": ...}`` on database errors instead of raising."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict:
        try:
            return func(*args, **kwargs)
        except psycopg.Error as exc:
            logger.error("DiscoveryAgent: %s failed: %s", func.__name__, exc)
            return {"success": False, "error": f"Database error in {func.__name__}: {type(exc).__name__}"}

    return wrapper


def _customer_context(customer_id: str, company_name: str, address: dict) -> dict:
    return {"customer_id": customer_id, "company_name": company_name, "address": address}


@_db_guard
def search_companies(
    company_name: Optional[str] = None,
    industry: Optional[str] = None,
    region: Optional[str] = None,
    customer_status: Optional[str] = None,
    street: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
) -> dict:
    """
    Search for companies in the prospecting database.

    Use company_name + address fields together for a compound match to avoid
    returning the wrong company when multiple companies share a similar address.
    Always pass company_name when the caller states a specific company name.

    Args:
        company_name: Partial or full company name to search for
        street: Street address to narrow match (use with company_name)
        city: City to narrow match
        state: State abbreviation to narrow match
        industry: Industry to filter by (e.g., 'Technology', 'Retail', 'Healthcare')
        region: Territory/Region to filter by (e.g., 'Northeast', 'West', 'Mid-Atlantic')
        customer_status: 'Y' for existing customers, 'N' for prospects, None for all

    Returns:
        List of matching companies with their details including location and customer status.
        When company_name is provided and found=0, the company does NOT exist in the DB.
    """
    logger.info(f"DiscoveryAgent: search_companies called with company_name={company_name}, street={street}, city={city}, state={state}, industry={industry}, region={region}, customer_status={customer_status}")
    results = db.search_companies(company_name, industry, region, customer_status, street, city, state)

    if not results:
        return {"found": 0, "companies": [],
                "note": f"No company matching '{company_name}' found. Do not present a different company as this one."}

    companies = []
    for company in results:
        companies.append({
            "company_name": company["Company Name"],
            "industry": company["Industry"],
            "region": company["Territory/Region"],
            "address": {
                "street": company.get("Street", "N/A"),
                "address_line2": company.get("address_line2") or "",
                "city": company.get("City", "N/A"),
                "state": company.get("State", "N/A"),
                "zip_code": company.get("zip_code", "N/A"),
            },
            "website": company["Website"],
            "customer_status": "Existing Customer" if company.get("Existing Customer") == "Y" else "Prospect",
            "customer_id": company.get("customer_id"),
            "current_products": company.get("Current Products"),
            "products_of_interest": company.get("Products of Interest"),
        })

    return {"found": len(companies), "companies": companies}


@_db_guard
def get_company_profile(company_name: str, tool_context: Optional[ToolContext] = None) -> dict:
    """
    Get comprehensive profile for a specific company including spend data, location, and products.

    Args:
        company_name: Exact company name (e.g., 'DataSync Technologies')

    Returns:
        Detailed company information including location, customer status, products, and advertising spend
    """
    logger.info(f"DiscoveryAgent: get_company_profile called with company_name={company_name}")
    company = db.get_company_details(company_name)

    if not company:
        return {"error": f"Company '{company_name}' not found in database."}

    profile = {
        "company_name": company["Company Name"],
        "industry": company["Industry"],
        "region": company["Territory/Region"],
        "address": {
            "street": company.get("Street", "N/A"),
            "address_line2": company.get("address_line2") or "",
            "city": company.get("City", "N/A"),
            "state": company.get("State", "N/A"),
            "zip_code": company.get("zip_code", "N/A"),
        },
        "website": company["Website"],
        "customer_status": "Existing Customer" if company.get("Existing Customer") == "Y" else "Prospect",
        "customer_id": company.get("customer_id"),
        "current_products": company.get("Current Products"),
        "products_of_interest": company.get("Products of Interest"),
    }

    if company.get("Estimated Annual Spend"):
        profile["advertising_spend"] = {
            "total": company["Estimated Annual Spend"],
            "digital": company.get("Digital", 0),
            "programmatic": company.get("Programmatic", 0),
            "tv": company.get("TV", 0),
            "audio": company.get("Audio", 0),
            "ooh": company.get("OOH", 0),
            "search": company.get("Search", 0),
            "social": company.get("Social", 0),
            "primary_agency": company.get("Primary Agency", "Unknown"),
        }

    # Publish customer identity to session state; export_context_delta forwards
    # it to the gateway so downstream agents share the same customer_context.
    if tool_context is not None and profile.get("customer_id"):
        tool_context.state["customer_context"] = _customer_context(
            profile["customer_id"], profile["company_name"], profile["address"]
        )
        logger.info(f"[STATE WRITE] get_company_profile -> customer_context = {tool_context.state['customer_context']}")

    return profile


@_db_guard
def get_contact_personas(company_name: str) -> dict:
    """
    Get all contacts and their personas for a specific company.
    Identifies decision makers, influencers, and their roles.

    Args:
        company_name: Exact company name (e.g., 'Company 001')

    Returns:
        List of contacts with their titles and decision-making roles
    """
    logger.info(f"DiscoveryAgent: get_contact_personas called with company_name={company_name}")
    contacts = db.get_contacts_for_company(company_name)

    if not contacts:
        return {"company_name": company_name, "contacts": []}

    buyers = [c for c in contacts if c.get("Role in Decision Making") == "Economic Buyer"]
    tech_buyers = [c for c in contacts if c.get("Role in Decision Making") == "Technical Buyer"]
    champions = [c for c in contacts if c.get("Role in Decision Making") == "Champion"]
    influencers = [c for c in contacts if c.get("Role in Decision Making") == "Influencer"]
    users = [c for c in contacts if c.get("Role in Decision Making") == "End User"]

    return {
        "company_name": company_name,
        "economic_buyers": [{"name": c["Name"], "title": c["Title"], "email": c.get("Email", "N/A"), "phone": c.get("Phone", "N/A"), "notes": c.get("Notes")} for c in buyers],
        "technical_buyers": [{"name": c["Name"], "title": c["Title"], "email": c.get("Email", "N/A"), "phone": c.get("Phone", "N/A")} for c in tech_buyers],
        "champions": [{"name": c["Name"], "title": c["Title"], "email": c.get("Email", "N/A"), "phone": c.get("Phone", "N/A")} for c in champions],
        "influencers": [{"name": c["Name"], "title": c["Title"], "email": c.get("Email", "N/A")} for c in influencers],
        "end_users": [{"name": c["Name"], "title": c["Title"]} for c in users],
    }


@_db_guard
def get_customer_intent(company_name: str) -> dict:
    """
    Identify customer intent through buying signals, pain points, and opportunities.

    Args:
        company_name: Exact company name (e.g., 'Company 001')

    Returns:
        Customer intent analysis including buying signals, pain points, opportunities, and recommended positioning
    """
    logger.info(f"DiscoveryAgent: get_customer_intent called with company_name={company_name}")
    insights = db.get_insights_for_company(company_name)
    opportunities = db.get_opportunities_for_company(company_name)
    actions = db.get_actions_for_company(company_name)

    if not insights and not opportunities:
        return {"company_name": company_name, "error": "No intent data found"}

    intent_data: dict[str, Any] = {"company_name": company_name}

    if insights:
        intent_data["buying_signals"] = insights.get("Buying Signals", "None identified")
        intent_data["pain_points"] = insights.get("Pain Points", "None identified")
        intent_data["recommended_positioning"] = insights.get("Recommended Positioning", "None specified")

    if opportunities:
        intent_data["opportunities"] = []
        for opp in opportunities[:5]:  # Top 5
            intent_data["opportunities"].append({
                "name": opp["Opportunity Name"],
                "stage": opp["Stage"],
                "mrc_estimate": opp.get("Total MRC (Est)", 0),
                "bant_score": opp.get("BANT_Score_0to100", 0),
                "bant_priority": opp.get("BANT_Priority_Bucket", "N/A"),
                "budget": opp.get("Budget", "Unknown"),
                "authority": opp.get("Authority", "Unknown"),
                "need": opp.get("Need", "Unknown"),
                "timeline_days": opp.get("Timeline (days)", "N/A"),
                "target_close_date": opp.get("Target Close Date", "N/A"),
                "next_step": opp.get("Next Step", "N/A"),
                "data_gaps": opp.get("BANT_Data_Gaps"),
            })

    if actions:
        intent_data["recommended_actions"] = {
            "owner": actions.get("Owner", "Unassigned"),
            "priority": actions.get("Priority", "Unknown"),
            "initial_outreach": actions.get("Initial Outreach Date", "Not scheduled"),
            "follow_up_cadence": actions.get("Follow-Up Cadence", "Not defined"),
        }

    return intent_data


@_db_guard
def search_by_intent_signals(keyword: str) -> dict:
    """
    Find companies showing specific buying signals or pain points.

    Args:
        keyword: Search term for buying signals or pain points (e.g., 'funding', 'CAC', 'attribution', 'growth')

    Returns:
        List of companies matching the intent signal with their details
    """
    logger.info(f"DiscoveryAgent: search_by_intent_signals called with keyword={keyword}")
    results = db.search_by_intent_signals(keyword)

    if not results:
        return {"keyword": keyword, "found": 0, "companies": []}

    companies = []
    for company in results:
        companies.append({
            "company_name": company["Company Name"],
            "industry": company["Industry"],
            "region": company["Territory/Region"],
            "buying_signals": company.get("Buying Signals", "N/A"),
            "pain_points": company.get("Pain Points", "N/A"),
            "recommended_positioning": company.get("Recommended Positioning", "N/A"),
        })

    return {"keyword": keyword, "found": len(companies), "companies": companies}


@_db_guard
def get_high_priority_opportunities(limit: int = 10) -> dict:
    """
    Get top priority opportunities across all companies based on BANT scoring.

    Args:
        limit: Maximum number of opportunities to return (default 10)

    Returns:
        List of highest priority opportunities sorted by BANT score
    """
    logger.info(f"DiscoveryAgent: get_high_priority_opportunities called with limit={limit}")
    opportunities = db.get_high_priority_opportunities(limit)

    if not opportunities:
        return {"found": 0, "opportunities": []}

    opp_data = []
    for opp in opportunities:
        opp_data.append({
            "company_name": opp["Company Name"],
            "opportunity_name": opp["Opportunity Name"],
            "stage": opp["Stage"],
            "mrc_estimate": opp.get("Total MRC (Est)", 0),
            "bant_score": opp.get("BANT_Score_0to100", 0),
            "bant_priority": opp.get("BANT_Priority_Bucket", "N/A"),
            "target_close_date": opp.get("Target Close Date", "N/A"),
        })

    return {"found": len(opp_data), "opportunities": opp_data}


# ==================== WRITE FUNCTIONS ====================

@_db_guard
def add_new_company(
    company_name: str,
    industry: str,
    region: str,
    street: str,
    city: str,
    state: str,
    zip_code: Optional[str] = None,
    address_line2: Optional[str] = None,
    website: str = "N/A",
    parent_company: Optional[str] = None,
    existing_customer: str = "N",
    current_products: Optional[str] = None,
    products_of_interest: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """
    Add a new company to the prospecting database.

    Args:
        company_name: Company name (must be unique)
        industry: Industry (e.g., 'Technology', 'Healthcare', 'Finance')
        region: Territory/Region (e.g., 'Northeast', 'West')
        street: Street address (e.g. '123 Main St')
        address_line2: Suite, floor, unit, or building — always collect this to uniquely
            identify the business location (e.g., 'Suite 400', 'Floor 3', 'Unit B').
            Ask the caller for this if not provided.
        city: City name
        state: State abbreviation (e.g., 'CA', 'NY')
        website: Company website
        parent_company: Parent company name (optional)
        existing_customer: 'Y' for customer, 'N' for prospect
        current_products: Comma-separated products (for existing customers)
        products_of_interest: Comma-separated products (for prospects).
            If the customer clearly states they "need internet" or is asking
            about connectivity for this business location, you MUST include
            "Internet" in this field (e.g., "Internet" or
            "Internet, Dedicated Internet"). Do not leave this empty in
            those cases.
        zip_code: ZIP code (optional but recommended for serviceability checks)

    Returns:
        Success or failure message with customer_id
    """
    logger.info(f"DiscoveryAgent: add_new_company called with company_name={company_name}, industry={industry}, region={region}, street={street}, city={city}, state={state}, zip_code={zip_code}, website={website}, parent_company={parent_company}, existing_customer={existing_customer}, current_products={current_products}, products_of_interest={products_of_interest}")
    result = db.add_company(
        company_name, industry, region, street, city, state, website,
        parent_company, existing_customer, current_products, products_of_interest,
        zip_code, address_line2,
    )

    output = {
        "action": "add_company",
        "success": result["success"],
        "customer_id": result.get("customer_id"),
        "company_name": company_name,
        "message": result["message"],
    }

    # Publish customer identity to session state (forwarded as _context_update).
    if tool_context is not None and result.get("success") and result.get("customer_id"):
        tool_context.state["customer_context"] = _customer_context(
            result["customer_id"],
            company_name,
            {
                "street": street,
                "address_line2": address_line2 or "",
                "city": city,
                "state": state,
                "zip_code": zip_code or "",
            },
        )
        logger.info(f"[STATE WRITE] add_new_company -> customer_context = {tool_context.state['customer_context']}")

    return output


@_db_guard
def update_company_info(
    company_name: str,
    industry: Optional[str] = None,
    region: Optional[str] = None,
    street: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    website: Optional[str] = None,
    parent_company: Optional[str] = None,
    existing_customer: Optional[str] = None,
    current_products: Optional[str] = None,
    products_of_interest: Optional[str] = None,
) -> dict:
    """
    Update existing company information in the database.

    Args:
        company_name: Company name to update (required)
        industry: New industry (optional)
        region: New region (optional)
        street: New street address (optional)
        city: New city (optional)
        state: New state (optional)
        zip_code: New ZIP code (optional)
        website: New website (optional)
        parent_company: New parent company (optional)
        existing_customer: New customer status 'Y' or 'N' (optional)
        current_products: New current products (optional)
        products_of_interest: New products of interest (optional)

    Returns:
        Success or failure message
    """
    logger.info(f"DiscoveryAgent: update_company_info called with company_name={company_name}, industry={industry}, region={region}, street={street}, city={city}, state={state}, zip_code={zip_code}, website={website}, parent_company={parent_company}, existing_customer={existing_customer}, current_products={current_products}, products_of_interest={products_of_interest}")
    updates = {}
    if industry: updates["industry"] = industry
    if region: updates["region"] = region
    if street: updates["street"] = street
    if city: updates["city"] = city
    if state: updates["state"] = state
    if zip_code: updates["zip_code"] = zip_code
    if website: updates["website"] = website
    if parent_company: updates["parent_company"] = parent_company
    if existing_customer: updates["existing_customer"] = existing_customer
    if current_products: updates["current_products"] = current_products
    if products_of_interest: updates["products_of_interest"] = products_of_interest

    if not updates:
        return {"action": "update_company", "success": False, "company_name": company_name, "message": "No fields provided to update"}

    success = db.update_company(company_name, **updates)

    return {
        "action": "update_company",
        "success": success,
        "company_name": company_name,
        "fields_updated": list(updates.keys()) if success else [],
        "message": f"Successfully updated {company_name}: {', '.join(updates.keys())}" if success else f"Failed to update company '{company_name}'. It may not exist in the database.",
    }


@_db_guard
def add_new_contact(
    company_name: str,
    contact_name: str,
    title: str,
    role_in_decision_making: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Add a new contact for a company.

    Args:
        company_name: Company name (must exist)
        contact_name: Contact full name
        title: Job title
        role_in_decision_making: Role (e.g., 'Economic Buyer', 'Technical Buyer', 'Influencer', 'Champion', 'End User')
        email: Email address (optional)
        phone: Phone number (optional)
        notes: Additional notes (optional)

    Returns:
        Success or failure message
    """
    logger.info(f"DiscoveryAgent: add_new_contact called with company_name={company_name}, contact_name={contact_name}, title={title}, role_in_decision_making={role_in_decision_making}, email={email}, phone={phone}, notes={notes}")
    success = db.add_contact(
        company_name, contact_name, title, role_in_decision_making,
        email, phone, notes,
    )

    return {
        "action": "add_contact",
        "success": success,
        "company_name": company_name,
        "contact_name": contact_name,
        "message": f"Successfully added contact: {contact_name} at {company_name}" if success else f"Failed to add contact. Company '{company_name}' may not exist.",
    }


@_db_guard
def update_contact_info(
    company_name: str,
    contact_name: str,
    title: Optional[str] = None,
    role_in_decision_making: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Update contact information.

    Args:
        company_name: Company name (required)
        contact_name: Contact name to update (required)
        title: New title (optional)
        role_in_decision_making: New role (optional)
        email: New email (optional)
        phone: New phone (optional)
        notes: New notes (optional)

    Returns:
        Success or failure message
    """
    logger.info(f"DiscoveryAgent: update_contact_info called with company_name={company_name}, contact_name={contact_name}, title={title}, role_in_decision_making={role_in_decision_making}, email={email}, phone={phone}, notes={notes}")
    updates = {}
    if title: updates["title"] = title
    if role_in_decision_making: updates["role_in_decision_making"] = role_in_decision_making
    if email: updates["email"] = email
    if phone: updates["phone"] = phone
    if notes: updates["notes"] = notes

    if not updates:
        return {"action": "update_contact", "success": False, "company_name": company_name, "contact_name": contact_name, "message": "No fields provided to update"}

    success = db.update_contact(company_name, contact_name, **updates)

    return {
        "action": "update_contact",
        "success": success,
        "company_name": company_name,
        "contact_name": contact_name,
        "fields_updated": list(updates.keys()) if success else [],
        "message": f"Successfully updated contact {contact_name}: {', '.join(updates.keys())}" if success else f"Failed to update contact '{contact_name}' at '{company_name}'.",
    }


@_db_guard
def add_or_update_insights(
    company_name: str,
    buying_signals: Optional[str] = None,
    pain_points: Optional[str] = None,
    recommended_positioning: Optional[str] = None,
) -> dict:
    """
    Add or update customer insights (buying signals, pain points, positioning).

    Args:
        company_name: Company name (must exist)
        buying_signals: Buying signals text (optional)
        pain_points: Pain points text (optional)
        recommended_positioning: Positioning recommendations (optional)

    Returns:
        Success or failure message
    """
    logger.info(f"DiscoveryAgent: add_or_update_insights called with company_name={company_name}, buying_signals={buying_signals}, pain_points={pain_points}, recommended_positioning={recommended_positioning}")
    success = db.add_insight(company_name, buying_signals, pain_points, recommended_positioning)

    return {
        "action": "add_or_update_insights",
        "success": success,
        "company_name": company_name,
        "message": f"Successfully updated insights for: {company_name}" if success else f"Failed to update insights for '{company_name}'.",
    }


@_db_guard
def create_opportunity_from_bant(
    company_name: str,
    opportunity_name: str = "General Inquiry",
    budget: Optional[str] = None,
    authority: Optional[str] = None,
    need: Optional[str] = None,
    timeline_days: Optional[int] = None,
    total_mrc: Optional[float] = None,
    next_step: Optional[str] = None,
) -> dict:
    """
    Create a new sales opportunity with BANT qualification scoring for a customer.
    Call this AFTER gathering BANT signals conversationally from a new customer.
    BANT scores are automatically calculated from the inputs.

    Args:
        company_name: Company name (must already exist in database)
        opportunity_name: A descriptive name for this opportunity (e.g., "Internet Service - New Location")
        budget: Budget status gathered from customer conversation.
            Use: 'Approved' (customer has confirmed budget), 'Identified' (budget exists but not confirmed),
            'Estimated' (customer gave a rough range), 'Unknown' (customer didn't share budget info)
        authority: Authority status based on who you're speaking with.
            Use: 'Confirmed' (speaking with decision-maker), 'Identified' (decision-maker is known but not on call),
            'Suspected' (likely has authority but not confirmed), 'Unknown' (unclear who decides)
        need: Need level inferred from customer's stated requirements.
            Use: 'High' (urgent/critical need), 'Medium' (important but not urgent),
            'Low' (exploring options), 'Unknown' (unclear)
        timeline_days: Approximate number of days until customer wants service active.
            Infer from customer statements like "ASAP" (7), "next month" (30),
            "next quarter" (90), "sometime this year" (180)
        total_mrc: Estimated Monthly Recurring Revenue if known (optional)
        next_step: Recommended next action (e.g., "Check serviceability", "Schedule demo")

    Returns:
        JSON with success status, BANT score, and priority bucket
    """
    logger.info(f"DiscoveryAgent: create_opportunity_from_bant called for {company_name}")
    success = lead_db.add_opportunity(
        company_name=company_name,
        opportunity_name=opportunity_name,
        stage="Discovery",
        total_mrc=total_mrc,
        budget=budget,
        authority=authority,
        need=need,
        timeline_days=timeline_days,
        target_close_date=None,
        next_step=next_step or "Check serviceability and recommend products",
    )

    if not success:
        return {
            "action": "create_opportunity",
            "success": False,
            "company_name": company_name,
            "message": f"Failed to create opportunity. Company '{company_name}' may not exist or opportunity name may be duplicate.",
        }

    # Retrieve the created opportunity to show calculated scores
    opp = lead_db.get_opportunity_qualification(company_name, opportunity_name)
    if not opp:
        return {
            "action": "create_opportunity",
            "success": True,
            "company_name": company_name,
            "opportunity_name": opportunity_name,
            "message": "Opportunity created successfully",
        }
    opp_data = opp[0]
    return {
        "action": "create_opportunity",
        "success": True,
        "company_name": company_name,
        "opportunity_name": opportunity_name,
        "bant_scores": {
            "budget_score": opp_data.get("BANT_Budget_Score", 0),
            "authority_score": opp_data.get("BANT_Authority_Score", 0),
            "need_score": opp_data.get("BANT_Need_Score", 0),
            "timing_score": opp_data.get("BANT_Timing_Score", 0),
            "weighted_score": opp_data.get("BANT_Weighted_0to3", 0),
            "score_0to100": opp_data.get("BANT_Score_0to100", 0),
            "priority_bucket": opp_data.get("BANT_Priority_Bucket", "N/A"),
            "data_gaps": opp_data.get("BANT_Data_Gaps", ""),
        },
        "message": f"Opportunity created with BANT score {opp_data.get('BANT_Score_0to100') or 0:.1f}/100 ({opp_data.get('BANT_Priority_Bucket', 'N/A')})",
    }


@_db_guard
def check_customer_state(customer_id: str) -> dict:
    """
    Check the current pipeline state for a returning customer.

    Queries all tables (quotes, carts, orders, payments, fulfillments, customer_master)
    to return a summary of where this customer left off. Use this when a customer is
    identified as existing and you want to offer to resume their previous activity.

    Args:
        customer_id: The customer identifier (e.g., CUST-20260415-001)

    Returns:
        JSON summary of the customer's current pipeline state including active quotes,
        pending orders, payment status, and fulfillment progress.
    """
    logger.info(f"DiscoveryAgent: check_customer_state called with customer_id={customer_id}")
    return _check_customer_state(customer_id)


ALL_TOOLS = [
    search_companies,
    get_company_profile,
    get_contact_personas,
    get_customer_intent,
    search_by_intent_signals,
    get_high_priority_opportunities,
    add_new_company,
    update_company_info,
    add_new_contact,
    update_contact_info,
    add_or_update_insights,
    create_opportunity_from_bant,
    check_customer_state,
]
