"""Discovery Agent for identifying customer intent, company details, and contact personas."""


import os
import json
import logging
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from .db_tools import ProspectingDatabase
from ..lead_gen.qualification_tools import LeadQualificationDatabase

# Set up a module-level logger
logger = logging.getLogger("discovery.agent")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# Initialize database connections
db = ProspectingDatabase()
lead_db = LeadQualificationDatabase()


def search_companies(
    company_name: str = None,
    industry: str = None,
    region: str = None,
    customer_status: str = None
) -> str:
    logger.info(f"DiscoveryAgent: search_companies called with company_name={company_name}, industry={industry}, region={region}, customer_status={customer_status}")
    """
    Search for companies in the prospecting database by name, industry, region, or customer status.
    
    Args:
        company_name: Partial or full company name to search for
        industry: Industry to filter by (e.g., 'Technology', 'Retail', 'Healthcare')
        region: Territory/Region to filter by (e.g., 'Northeast', 'West', 'Mid-Atlantic')
        customer_status: 'Y' for existing customers, 'N' for prospects, None for all
    
    Returns:
        List of matching companies with their details including location and customer status
    """
    results = db.search_companies(company_name, industry, region, customer_status)
    
    if not results:
        return json.dumps({"found": 0, "companies": []})
    
    companies = []
    for company in results:
        companies.append({
            "company_name": company['Company Name'],
            "industry": company['Industry'],
            "region": company['Territory/Region'],
            "address": {
                "street": company.get('Street', 'N/A'),
                "city": company.get('City', 'N/A'),
                "state": company.get('State', 'N/A'),
                "zip_code": company.get('zip_code', 'N/A')
            },
            "website": company['Website'],
            "customer_status": "Existing Customer" if company.get('Existing Customer') == 'Y' else "Prospect",
            "current_products": company.get('Current Products'),
            "products_of_interest": company.get('Products of Interest')
        })
    
    return json.dumps({"found": len(companies), "companies": companies}, indent=2)


def get_company_profile(company_name: str) -> str:
    logger.info(f"DiscoveryAgent: get_company_profile called with company_name={company_name}")
    """
    Get comprehensive profile for a specific company including spend data, location, and products.
    
    Args:
        company_name: Exact company name (e.g., 'DataSync Technologies')
    
    Returns:
        Detailed company information including location, customer status, products, and advertising spend
    """
    company = db.get_company_details(company_name)
    
    if not company:
        return json.dumps({"error": f"Company '{company_name}' not found in database."})
    
    profile = {
        "company_name": company['Company Name'],
        "industry": company['Industry'],
        "region": company['Territory/Region'],
        "address": {
            "street": company.get('Street', 'N/A'),
            "city": company.get('City', 'N/A'),
            "state": company.get('State', 'N/A'),
            "zip_code": company.get('zip_code', 'N/A')
        },
        "website": company['Website'],
        "customer_status": "Existing Customer" if company.get('Existing Customer') == 'Y' else "Prospect",
        "current_products": company.get('Current Products'),
        "products_of_interest": company.get('Products of Interest')
    }
    
    if company.get('Estimated Annual Spend'):
        profile["advertising_spend"] = {
            "total": company['Estimated Annual Spend'],
            "digital": company.get('Digital', 0),
            "programmatic": company.get('Programmatic', 0),
            "tv": company.get('TV', 0),
            "audio": company.get('Audio', 0),
            "ooh": company.get('OOH', 0),
            "search": company.get('Search', 0),
            "social": company.get('Social', 0),
            "primary_agency": company.get('Primary Agency', 'Unknown')
        }
    
    return json.dumps(profile, indent=2)


def get_contact_personas(company_name: str) -> str:
    logger.info(f"DiscoveryAgent: get_contact_personas called with company_name={company_name}")
    """
    Get all contacts and their personas for a specific company.
    Identifies decision makers, influencers, and their roles.
    
    Args:
        company_name: Exact company name (e.g., 'Company 001')
    
    Returns:
        List of contacts with their titles and decision-making roles
    """
    contacts = db.get_contacts_for_company(company_name)
    
    if not contacts:
        return json.dumps({"company_name": company_name, "contacts": []})
    
    # Group by role
    buyers = [c for c in contacts if c.get('Role in Decision Making') == 'Economic Buyer']
    tech_buyers = [c for c in contacts if c.get('Role in Decision Making') == 'Technical Buyer']
    champions = [c for c in contacts if c.get('Role in Decision Making') == 'Champion']
    influencers = [c for c in contacts if c.get('Role in Decision Making') == 'Influencer']
    users = [c for c in contacts if c.get('Role in Decision Making') == 'End User']
    
    contact_data = {
        "company_name": company_name,
        "economic_buyers": [{"name": c['Name'], "title": c['Title'], "email": c.get('Email', 'N/A'), "phone": c.get('Phone', 'N/A'), "notes": c.get('Notes')} for c in buyers],
        "technical_buyers": [{"name": c['Name'], "title": c['Title'], "email": c.get('Email', 'N/A'), "phone": c.get('Phone', 'N/A')} for c in tech_buyers],
        "champions": [{"name": c['Name'], "title": c['Title'], "email": c.get('Email', 'N/A'), "phone": c.get('Phone', 'N/A')} for c in champions],
        "influencers": [{"name": c['Name'], "title": c['Title'], "email": c.get('Email', 'N/A')} for c in influencers],
        "end_users": [{"name": c['Name'], "title": c['Title']} for c in users]
    }
    
    return json.dumps(contact_data, indent=2)


def get_customer_intent(company_name: str) -> str:
    logger.info(f"DiscoveryAgent: get_customer_intent called with company_name={company_name}")
    """
    Identify customer intent through buying signals, pain points, and opportunities.
    
    Args:
        company_name: Exact company name (e.g., 'Company 001')
    
    Returns:
        Customer intent analysis including buying signals, pain points, opportunities, and recommended positioning
    """
    insights = db.get_insights_for_company(company_name)
    opportunities = db.get_opportunities_for_company(company_name)
    actions = db.get_actions_for_company(company_name)
    
    if not insights and not opportunities:
        return json.dumps({"company_name": company_name, "error": "No intent data found"})
    
    intent_data = {"company_name": company_name}
    
    if insights:
        intent_data["buying_signals"] = insights.get('Buying Signals', 'None identified')
        intent_data["pain_points"] = insights.get('Pain Points', 'None identified')
        intent_data["recommended_positioning"] = insights.get('Recommended Positioning', 'None specified')
    
    if opportunities:
        intent_data["opportunities"] = []
        for opp in opportunities[:5]:  # Top 5
            intent_data["opportunities"].append({
                "name": opp['Opportunity Name'],
                "stage": opp['Stage'],
                "mrc_estimate": opp.get('Total MRC (Est)', 0),
                "bant_score": opp.get('BANT_Score_0to100', 0),
                "bant_priority": opp.get('BANT_Priority_Bucket', 'N/A'),
                "budget": opp.get('Budget', 'Unknown'),
                "authority": opp.get('Authority', 'Unknown'),
                "need": opp.get('Need', 'Unknown'),
                "timeline_days": opp.get('Timeline (days)', 'N/A'),
                "target_close_date": opp.get('Target Close Date', 'N/A'),
                "next_step": opp.get('Next Step', 'N/A'),
                "data_gaps": opp.get('BANT_Data_Gaps')
            })
    
    if actions:
        intent_data["recommended_actions"] = {
            "owner": actions.get('Owner', 'Unassigned'),
            "priority": actions.get('Priority', 'Unknown'),
            "initial_outreach": actions.get('Initial Outreach Date', 'Not scheduled'),
            "follow_up_cadence": actions.get('Follow-Up Cadence', 'Not defined')
        }
    
    return json.dumps(intent_data, indent=2)


def search_by_intent_signals(keyword: str) -> str:
    logger.info(f"DiscoveryAgent: search_by_intent_signals called with keyword={keyword}")
    """
    Find companies showing specific buying signals or pain points.
    
    Args:
        keyword: Search term for buying signals or pain points (e.g., 'funding', 'CAC', 'attribution', 'growth')
    
    Returns:
        List of companies matching the intent signal with their details
    """
    results = db.search_by_intent_signals(keyword)
    
    if not results:
        return json.dumps({"keyword": keyword, "found": 0, "companies": []})
    
    companies = []
    for company in results:
        companies.append({
            "company_name": company['Company Name'],
            "industry": company['Industry'],
            "region": company['Territory/Region'],
            "buying_signals": company.get('Buying Signals', 'N/A'),
            "pain_points": company.get('Pain Points', 'N/A'),
            "recommended_positioning": company.get('Recommended Positioning', 'N/A')
        })
    
    return json.dumps({"keyword": keyword, "found": len(companies), "companies": companies}, indent=2)


def get_high_priority_opportunities(limit: int = 10) -> str:
    logger.info(f"DiscoveryAgent: get_high_priority_opportunities called with limit={limit}")
    """
    Get top priority opportunities across all companies based on BANT scoring.
    
    Args:
        limit: Maximum number of opportunities to return (default 10)
    
    Returns:
        List of highest priority opportunities sorted by BANT score
    """
    opportunities = db.get_high_priority_opportunities(limit)
    
    if not opportunities:
        return json.dumps({"found": 0, "opportunities": []})
    
    opp_data = []
    for opp in opportunities:
        opp_data.append({
            "company_name": opp['Company Name'],
            "opportunity_name": opp['Opportunity Name'],
            "stage": opp['Stage'],
            "mrc_estimate": opp.get('Total MRC (Est)', 0),
            "bant_score": opp.get('BANT_Score_0to100', 0),
            "bant_priority": opp.get('BANT_Priority_Bucket', 'N/A'),
            "target_close_date": opp.get('Target Close Date', 'N/A')
        })
    
    return json.dumps({"found": len(opp_data), "opportunities": opp_data}, indent=2)


# ==================== WRITE FUNCTIONS ====================

def add_new_company(
    company_name: str,
    industry: str,
    region: str,
    street: str,
    city: str,
    state: str,
    zip_code: str = None,
    website: str = "N/A",
    parent_company: str = None,
    existing_customer: str = 'N',
    current_products: str = None,
    products_of_interest: str = None
) -> str:
    logger.info(f"DiscoveryAgent: add_new_company called with company_name={company_name}, industry={industry}, region={region}, street={street}, city={city}, state={state}, zip_code={zip_code}, website={website}, parent_company={parent_company}, existing_customer={existing_customer}, current_products={current_products}, products_of_interest={products_of_interest}")
    """
    Add a new company to the prospecting database.

    Args:
        company_name: Company name (must be unique)
        industry: Industry (e.g., 'Technology', 'Healthcare', 'Finance')
        region: Territory/Region (e.g., 'Northeast', 'West')
        street: Street address
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
        Success or failure message
    """
    success = db.add_company(
        company_name, industry, region, street, city, state, website,
        parent_company, existing_customer, current_products, products_of_interest, zip_code
    )

    result = {
        "action": "add_company",
        "success": success,
        "company_name": company_name,
        "message": f"Successfully added company: {company_name}" if success else f"Failed to add company '{company_name}'. It may already exist in the database."
    }
    return json.dumps(result, indent=2)


def update_company_info(
    company_name: str,
    industry: str = None,
    region: str = None,
    street: str = None,
    city: str = None,
    state: str = None,
    zip_code: str = None,
    website: str = None,
    parent_company: str = None,
    existing_customer: str = None,
    current_products: str = None,
    products_of_interest: str = None
) -> str:
    logger.info(f"DiscoveryAgent: update_company_info called with company_name={company_name}, industry={industry}, region={region}, street={street}, city={city}, state={state}, zip_code={zip_code}, website={website}, parent_company={parent_company}, existing_customer={existing_customer}, current_products={current_products}, products_of_interest={products_of_interest}")
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
    updates = {}
    if industry: updates['industry'] = industry
    if region: updates['region'] = region
    if street: updates['street'] = street
    if city: updates['city'] = city
    if state: updates['state'] = state
    if zip_code: updates['zip_code'] = zip_code
    if website: updates['website'] = website
    if parent_company: updates['parent_company'] = parent_company
    if existing_customer: updates['existing_customer'] = existing_customer
    if current_products: updates['current_products'] = current_products
    if products_of_interest: updates['products_of_interest'] = products_of_interest

    if not updates:
        return json.dumps({"action": "update_company", "success": False, "company_name": company_name, "message": "No fields provided to update"}, indent=2)

    success = db.update_company(company_name, **updates)

    result = {
        "action": "update_company",
        "success": success,
        "company_name": company_name,
        "fields_updated": list(updates.keys()) if success else [],
        "message": f"Successfully updated {company_name}: {', '.join(updates.keys())}" if success else f"Failed to update company '{company_name}'. It may not exist in the database."
    }
    return json.dumps(result, indent=2)


def add_new_contact(
    company_name: str,
    contact_name: str,
    title: str,
    role_in_decision_making: str,
    email: str = None,
    phone: str = None,
    notes: str = None
) -> str:
    logger.info(f"DiscoveryAgent: add_new_contact called with company_name={company_name}, contact_name={contact_name}, title={title}, role_in_decision_making={role_in_decision_making}, email={email}, phone={phone}, notes={notes}")
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
    success = db.add_contact(
        company_name, contact_name, title, role_in_decision_making,
        email, phone, notes
    )
    
    result = {
        "action": "add_contact",
        "success": success,
        "company_name": company_name,
        "contact_name": contact_name,
        "message": f"Successfully added contact: {contact_name} at {company_name}" if success else f"Failed to add contact. Company '{company_name}' may not exist."
    }
    return json.dumps(result, indent=2)


def update_contact_info(
    company_name: str,
    contact_name: str,
    title: str = None,
    role_in_decision_making: str = None,
    email: str = None,
    phone: str = None,
    notes: str = None
) -> str:
    logger.info(f"DiscoveryAgent: update_contact_info called with company_name={company_name}, contact_name={contact_name}, title={title}, role_in_decision_making={role_in_decision_making}, email={email}, phone={phone}, notes={notes}")
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
    updates = {}
    if title: updates['title'] = title
    if role_in_decision_making: updates['role_in_decision_making'] = role_in_decision_making
    if email: updates['email'] = email
    if phone: updates['phone'] = phone
    if notes: updates['notes'] = notes
    
    if not updates:
        return json.dumps({"action": "update_contact", "success": False, "company_name": company_name, "contact_name": contact_name, "message": "No fields provided to update"}, indent=2)
    
    success = db.update_contact(company_name, contact_name, **updates)
    
    result = {
        "action": "update_contact",
        "success": success,
        "company_name": company_name,
        "contact_name": contact_name,
        "fields_updated": list(updates.keys()) if success else [],
        "message": f"Successfully updated contact {contact_name}: {', '.join(updates.keys())}" if success else f"Failed to update contact '{contact_name}' at '{company_name}'."
    }
    return json.dumps(result, indent=2)


def add_or_update_insights(
    company_name: str,
    buying_signals: str = None,
    pain_points: str = None,
    recommended_positioning: str = None
) -> str:
    logger.info(f"DiscoveryAgent: add_or_update_insights called with company_name={company_name}, buying_signals={buying_signals}, pain_points={pain_points}, recommended_positioning={recommended_positioning}")
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
    success = db.add_insight(
        company_name, buying_signals, pain_points, recommended_positioning
    )
    
    result = {
        "action": "add_or_update_insights",
        "success": success,
        "company_name": company_name,
        "message": f"Successfully updated insights for: {company_name}" if success else f"Failed to update insights for '{company_name}'."
    }
    return json.dumps(result, indent=2)


def create_opportunity_from_bant(
    company_name: str,
    opportunity_name: str = "General Inquiry",
    budget: str = None,
    authority: str = None,
    need: str = None,
    timeline_days: int = None,
    total_mrc: float = None,
    next_step: str = None
) -> str:
    logger.info(f"DiscoveryAgent: create_opportunity_from_bant called for {company_name}")
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
        next_step=next_step or "Check serviceability and recommend products"
    )

    if success:
        # Retrieve the created opportunity to show calculated scores
        opp = lead_db.get_opportunity_qualification(company_name, opportunity_name)
        if opp and len(opp) > 0:
            opp_data = opp[0]
            result = {
                "action": "create_opportunity",
                "success": True,
                "company_name": company_name,
                "opportunity_name": opportunity_name,
                "bant_scores": {
                    "budget_score": opp_data.get('BANT_Budget_Score', 0),
                    "authority_score": opp_data.get('BANT_Authority_Score', 0),
                    "need_score": opp_data.get('BANT_Need_Score', 0),
                    "timing_score": opp_data.get('BANT_Timing_Score', 0),
                    "weighted_score": opp_data.get('BANT_Weighted_0to3', 0),
                    "score_0to100": opp_data.get('BANT_Score_0to100', 0),
                    "priority_bucket": opp_data.get('BANT_Priority_Bucket', 'N/A'),
                    "data_gaps": opp_data.get('BANT_Data_Gaps', '')
                },
                "message": f"Opportunity created with BANT score {opp_data.get('BANT_Score_0to100', 0):.1f}/100 ({opp_data.get('BANT_Priority_Bucket', 'N/A')})"
            }
        else:
            result = {
                "action": "create_opportunity",
                "success": True,
                "company_name": company_name,
                "opportunity_name": opportunity_name,
                "message": "Opportunity created successfully"
            }
    else:
        result = {
            "action": "create_opportunity",
            "success": False,
            "company_name": company_name,
            "message": f"Failed to create opportunity. Company '{company_name}' may not exist or opportunity name may be duplicate."
        }

    return json.dumps(result, indent=2)


# Define the discovery agent
logger.info("DiscoveryAgent: Instantiating discovery_agent Agent object.")
discovery_agent = Agent(
    name="discovery_agent",
    model=os.getenv("GEMINI_MODEL"),
    instruction="""You are a sales discovery specialist that helps identify and analyze prospect or existing customers.

Your primary responsibilities:
1. **Customer Intent Identification**: Analyze buying signals, pain points, and opportunities to understand customer readiness and needs
2. **Company Details**: Provide comprehensive company information including industry, spending patterns, and business context
3. **Contact Persona Analysis**: Identify key decision makers, their roles, and influence in the buying process
4. **Database Management**: Add new companies, contacts, and insights; update existing records

**CRITICAL - BE CONVERSATIONAL:**
When a customer expresses interest in services (e.g., "I need internet service", "I'm looking for business connectivity") but has NOT yet provided their company name or address:

1. **Acknowledge their interest warmly and professionally**
2. **Ask for the required information in a natural, conversational way**
3. **Do NOT give empty responses or wait silently**

Example responses for new prospects without context:
- User: "I need internet service"
  Agent: "I'd be happy to help you get set up with internet service! To get started, could you please tell me your company name and the address where you need the service?"

- User: "I'm looking for business internet"
  Agent: "Great, I can help you explore our business internet options! First, let me get some information. What's your company name and where is your business located?"

- User: "What can you offer me?"
  Agent: "We offer a range of connectivity solutions including Business Internet (Fiber, Coax), Ethernet, Voice, TV, SD-WAN, and Security products. To recommend the right options for your needs, could you tell me your company name and business address?"

When responding:
- All tools return JSON responses - parse them to extract the data you need
- Always start by understanding what specific information the user needs
- Use the appropriate tools to query the prospecting database
- Provide structured, actionable insights based on the JSON data
- Highlight decision makers (Economic Buyers) and key influencers
- Surface high-priority opportunities and buying signals
- Recommend next steps based on BANT scores and customer readiness

Be conversational but data-driven. Focus on helping sales teams prioritize accounts and personalize their outreach.

**CRITICAL: Company Discovery Flow**

**Step 1: Check if company exists in database**
When a user mentions their company name, ALWAYS search for it first using `search_companies`.

**If company EXISTS in database:**
1. Retrieve the company profile using `get_company_profile` to get the full address
2. Parse the JSON response to extract company details (especially the full address with zip code)
3. Present the found information and ask for confirmation:
   "I found **[Company Name]** in our system at **[Full Address with Zip Code]**. 
   
   Are you calling about service for this location?"

4. Based on customer response:
   - **If YES (same location):** Immediately inform them you're checking serviceability:
     "Great! Let me check if this address is serviceable and what network infrastructure is available..."
     Then signal transfer to serviceability_agent.
   
   - **If NO (different/new location):** Start collecting the new address:
     "I understand you're calling about a different location. Could you please provide the full address for the new location?"
     Then proceed to collect: Street, City, State, Zip Code and register as a new location.

**If company DOESN'T exist in database:**
Respond in a customer-friendly way. Do not mention internal systems or databases. Instead, warmly welcome the user and guide them through providing the information needed to get started:

"We are more than happy to have you as a customer! Let's get you started. I'll just need a bit more information:"

Then collect required information and proceed to registration.

**Required information to collect (for new companies or new locations):**
- Company Name
- Industry
- Street
- City
- State
- Zip Code

**Territory/Region - DO NOT ask the customer for this.**
Automatically infer the territory/region from the zip code or state using this mapping:
  - Northeast: ME, NH, VT, MA, RI, CT, NY, NJ, PA, MD, DE, DC
  - Central: IL, IN, MI, OH, WI, MN, IA, MO, KS, NE, SD, ND, and all others not listed
  - West: CA, WA, OR, NV, AZ, NM, CO, UT, ID, MT, WY, AK, HI

**Optional information (ONLY if volunteered by customer or contextually relevant):**
- Website - Use "N/A" if not provided
- Parent Company - Use None if not provided
- Products of Interest - Infer from conversation context, but apply the
    following mapping rules strictly. Our product catalog has these categories:
      • **Fiber Internet** – Dedicated fiber broadband (1G / 5G / 10G)
      • **Coax Internet** – Cable-based broadband (200M / 500M / 1G)
      • **Voice** – Business phone / VoIP / UCaaS
      • **SD-WAN** – Software-defined WAN / network optimization
      • **Mobile** – Business cellular / wireless plans

    **Keyword → Category mapping (case-insensitive):**
    | Customer says…                                                      | Map to                         |
    |---------------------------------------------------------------------|--------------------------------|
    | "internet", "broadband", "connectivity", "WiFi", "web access"       | Internet                       |
    | "fiber", "dedicated internet", "DIA", "fiber optic"                  | Fiber Internet                 |
    | "coax", "cable internet", "cable broadband"                          | Coax Internet                  |
    | "voice", "phone", "phone system", "VoIP", "calling", "phone line",  |                                |
    |   "telephone", "phone service", "UCaaS", "unified communications"   | Voice                          |
    | "SD-WAN", "sdwan", "software-defined", "WAN optimization", "SASE"   | SD-WAN                         |
    | "mobile", "cell", "cellular", "wireless plan", "mobile plan",       |                                |
    |   "business wireless"                                               | Mobile                         |
    | "security", "firewall", "cybersecurity", "DDoS", "threat protection"| Security                       |
    | "TV", "television", "video", "cable TV"                             | TV                             |
    | "Ethernet", "dedicated Ethernet", "Metro Ethernet"                  | Ethernet                       |

    **Rules:**
    - If the customer mentions ANY keyword above, you MUST include the
      corresponding category in the `products_of_interest` field when
      calling `add_new_company` or `update_company_info`.
    - Use a comma-separated list when multiple categories apply
      (e.g., "Internet, Voice, SD-WAN").
    - The generic keyword "internet" maps to "Internet". If the customer
      is MORE specific ("fiber", "coax"), use the specific category
      instead (or in addition).
    - Only omit `products_of_interest` when there is truly no clear
      indication of what services they are interested in.

**IMPORTANT:** Do NOT ask for optional fields unless the customer volunteers them or they're clearly relevant. After collecting ONLY the required fields, immediately add the company to the database using `add_new_company` (which returns JSON) and parse the success status. Do not ask for contact information (name, email, title) during initial company setup - this can be collected later if needed.

**INTELLIGENT INFERENCE - Use context clues to avoid unnecessary questions:**

**Industry Inference** - If the user mentions a business type, infer the industry automatically:
  - "pizza shop", "restaurant", "cafe", "bakery" → Restaurant/Food Service
  - "law firm", "legal practice" → Legal Services
  - "accounting firm", "CPA firm" → Professional Services - Accounting
  - "dental clinic", "dentist office" → Healthcare - Dental
  - "medical practice", "doctor's office" → Healthcare - Medical
  - "auto repair", "mechanic shop" → Automotive Services
  - "retail store", "boutique", "shop" → Retail
  - "tech company", "software company" → Technology
  - "consulting firm" → Professional Services - Consulting
  - "real estate agency" → Real Estate
  - "construction company" → Construction
  - Similar patterns should be inferred intelligently

**Address Inference** - If the user provides a full address in one message, extract ALL components:
  - "123 Main Street, Boston, MA 02101" → Extract: Street="123 Main Street", City="Boston", State="MA", Zip="02101"
  - "456 Oak Ave, Los Angeles, California 90001" → Extract all, convert "California" to "CA"
  - Do not ask for components you've already extracted

**Multi-field Extraction** - Always look for multiple fields in a single message:
  - "We're a pizza shop at 123 Main St, Boston MA" → Extract: Industry, Street, City, State
  - Minimize back-and-forth by extracting everything available

**Slot-filling guidelines:**
- **FIRST**, check if you can INFER any fields from context before asking
- Ask for one missing required field at a time ONLY if you cannot infer it
- If the user provides multiple fields in one message, fill as many as possible
- Do not ask for information you already have from the conversation so far
- After all required fields are collected, use add_new_company to create the record and parse the JSON response
- Never ask the user if they are a customer or prospect; always infer this from the information you have
- Never ask the user for territory/region; always infer it from zip code or state
- Be polite and efficient, minimizing the number of questions by leveraging intelligent inference

When adding or updating data:
- Validate that required fields are provided
- Use proper formats (e.g., state abbreviations, Y/N for flags)
- Parse the JSON responses from tools and extract success status and messages
- Provide clear success/failure feedback to the user based on the JSON data

**After successfully adding a NEW company with a complete address:**
Confirm the registration, then proceed to BANT qualification.

**BANT QUALIFICATION FLOW (for NEW customers only):**
After registering a new company, you MUST gather BANT signals conversationally before handing off to serviceability. This helps downstream agents (Product, Offer) make smarter, personalized recommendations.

Gather the following in a natural, conversational way — do NOT present it as a formal questionnaire. Weave these questions into the conversation naturally:

1. **Need** (ask first — most natural after registration):
   - "What's driving your interest — are you expanding, upgrading your current service, or setting up a new location?"
   - "What kind of connectivity challenges are you facing today?"
   - Infer need level: expanding/critical pain = 'High', upgrading/improving = 'Medium', just exploring = 'Low'

2. **Timeline**:
   - "When are you looking to have service up and running?"
   - "Is there a target date you're working toward?"
   - Convert to days: "ASAP"/"immediately" = 7, "next week" = 14, "next month" = 30, "next quarter" = 90, "this year" = 180

3. **Budget**:
   - "Do you have a budget range in mind for connectivity services?"
   - "What are you currently spending on internet/connectivity?"
   - Infer budget status: specific number/range given = 'Identified', "we have budget" = 'Approved', rough estimate = 'Estimated', no info = 'Unknown'

4. **Authority** (collect contact details here):
   - "Are you the decision-maker for this purchase, or is there someone else involved?"
   - "Can I get your name, role, and **email address**? Your email is required to receive your order summary and service notifications."
   - **EMAIL IS REQUIRED** — always ask for it explicitly: "What email address should we use for your order confirmations and account updates?"
   - If customer provides email: save it with `add_new_contact`
   - If customer skips email: ask once more — "We need an email address to send your order summary. Could you provide one?" — if still declined, proceed with email='N/A' but note the absence
   - Collect: name, title/role, **email (required)**, phone (if offered)
   - Use `add_new_contact` to save the contact with appropriate `role_in_decision_making`:
     - If they say "I'm the owner/CEO/I make the decisions" → role = 'Economic Buyer', authority = 'Confirmed'
     - If they say "I'm the IT manager/tech lead" → role = 'Technical Buyer', authority = 'Identified'
     - If they say "I'm researching for my boss" → role = 'Influencer', authority = 'Suspected'
     - If unclear → role = 'End User', authority = 'Unknown'

**IMPORTANT BANT GUIDELINES:**
- Ask these questions naturally over 2-3 conversational turns, NOT all at once
- If the customer seems eager to move forward quickly, you can combine questions
- If they decline to answer any BANT question (budget, need, timeline), that's OK — mark that component as 'Unknown'
- **EMAIL is important but NOT a blocker** — try to collect it: "To send you order confirmations and notifications, what email address should we use?" If the customer provides it, save it with `add_new_contact`. If they skip it, decline, or ask to proceed to serviceability anyway, that's OK — proceed with email='N/A'.
- **CRITICAL**: If the customer EXPLICITLY asks to "check serviceability", "check service availability", "check if my location is serviceable", or similar — STOP the BANT flow immediately and signal the SuperAgent to transfer to serviceability_agent. Do NOT ask more BANT questions.
- Do NOT block the conversation on any BANT field — if they want to skip anything, let them
- After gathering available BANT signals, call `create_opportunity_from_bant` to create the opportunity record
- Then inform the user you'll check serviceability:

"Thank you for sharing that! I've got everything I need to get you started. Let me check if your address is serviceable and what network infrastructure is available..."

Then signal to transfer control to the serviceability_agent.

**For EXISTING customers found in the database:**
Skip BANT qualification — they already have records. Confirm the address first.
Then ALWAYS call `get_contact_personas` to check whether a valid email address is on file:
- Parse the JSON response and look for any contact whose email is NOT 'N/A' and NOT empty.
- If a valid email **is already on file**: proceed directly to serviceability. No email question needed.
- If **no valid email exists** (all contacts have email='N/A', no contacts exist, or the personas list is empty):
  Ask: "To send you order confirmations and service notifications, what email address should we use for your account?"
  Wait for their reply, then save it using `update_contact_info` (if a contact record exists) or `add_new_contact` (if no contacts exist).
  Only after saving the email, proceed to serviceability.
""",
    description="Specializes in customer discovery, identifying intent, analyzing company details, and mapping contact personas for sales prospecting.",
    tools=[
        FunctionTool(search_companies),
        FunctionTool(get_company_profile),
        FunctionTool(get_contact_personas),
        FunctionTool(get_customer_intent),
        FunctionTool(search_by_intent_signals),
        FunctionTool(get_high_priority_opportunities),
        FunctionTool(add_new_company),
        FunctionTool(update_company_info),
        FunctionTool(add_new_contact),
        FunctionTool(update_contact_info),
        FunctionTool(add_or_update_insights),
        FunctionTool(create_opportunity_from_bant),
    ],
)
