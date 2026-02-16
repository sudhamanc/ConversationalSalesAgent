"""Discovery Agent for identifying customer intent, company details, and contact personas."""


import os
import logging
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from .db_tools import ProspectingDatabase

# Set up a module-level logger
logger = logging.getLogger("discovery.agent")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# Initialize database connection
db = ProspectingDatabase()


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
        return "No companies found matching the search criteria."
    
    output = f"Found {len(results)} companies:\n\n"
    for company in results:
        output += f"Company: {company['Company Name']}\n"
        output += f"  Industry: {company['Industry']}\n"
        output += f"  Region: {company['Territory/Region']}\n"
        output += f"  Location: {company.get('Street', 'N/A')}, {company.get('City', 'N/A')}, {company.get('State', 'N/A')}\n"
        output += f"  Website: {company['Website']}\n"
        output += f"  Status: {'Existing Customer' if company.get('Existing Customer') == 'Y' else 'Prospect'}\n"
        if company.get('Current Products'):
            output += f"  Current Products: {company['Current Products']}\n"
        if company.get('Products of Interest'):
            output += f"  Products of Interest: {company['Products of Interest']}\n"
        output += "\n"
    
    return output


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
        return f"Company '{company_name}' not found in database."
    
    output = f"=== Company Profile: {company['Company Name']} ===\n\n"
    output += f"Industry: {company['Industry']}\n"
    output += f"Region: {company['Territory/Region']}\n"
    output += f"Location: {company.get('Street', 'N/A')}, {company.get('City', 'N/A')}, {company.get('State', 'N/A')}\n"
    output += f"Website: {company['Website']}\n"
    output += f"\n--- Customer Information ---\n"
    output += f"Status: {'Existing Customer' if company.get('Existing Customer') == 'Y' else 'Prospect'}\n"
    
    if company.get('Current Products'):
        output += f"Current Products: {company['Current Products']}\n"
    
    if company.get('Products of Interest'):
        output += f"Products of Interest: {company['Products of Interest']}\n"
    
    if company.get('Estimated Annual Spend'):
        output += f"\n--- Advertising Spend ---\n"
        output += f"Estimated Annual Spend: ${company['Estimated Annual Spend']:,}\n"
        output += f"  Digital: ${company.get('Digital', 0):,}\n"
        output += f"  Programmatic: ${company.get('Programmatic', 0):,}\n"
        output += f"  TV: ${company.get('TV', 0):,}\n"
        output += f"  Audio: ${company.get('Audio', 0):,}\n"
        output += f"  OOH: ${company.get('OOH', 0):,}\n"
        output += f"  Search: ${company.get('Search', 0):,}\n"
        output += f"  Social: ${company.get('Social', 0):,}\n"
        output += f"Primary Agency: {company.get('Primary Agency', 'Unknown')}\n"
    
    return output


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
        return f"No contacts found for company '{company_name}'."
    
    output = f"=== Contacts for {company_name} ===\n\n"
    
    # Group by role
    buyers = [c for c in contacts if c.get('Role in Decision Making') == 'Economic Buyer']
    tech_buyers = [c for c in contacts if c.get('Role in Decision Making') == 'Technical Buyer']
    champions = [c for c in contacts if c.get('Role in Decision Making') == 'Champion']
    influencers = [c for c in contacts if c.get('Role in Decision Making') == 'Influencer']
    users = [c for c in contacts if c.get('Role in Decision Making') == 'End User']
    
    if buyers:
        output += "--- Economic Buyers (Final Decision Authority) ---\n"
        for contact in buyers:
            output += f"  • {contact['Name']} - {contact['Title']}\n"
            output += f"    Email: {contact.get('Email', 'N/A')} | Phone: {contact.get('Phone', 'N/A')}\n"
            if contact.get('Notes'):
                output += f"    Notes: {contact['Notes']}\n"
        output += "\n"
    
    if tech_buyers:
        output += "--- Technical Buyers (Technical Evaluation) ---\n"
        for contact in tech_buyers:
            output += f"  • {contact['Name']} - {contact['Title']}\n"
            output += f"    Email: {contact.get('Email', 'N/A')} | Phone: {contact.get('Phone', 'N/A')}\n"
        output += "\n"
    
    if champions:
        output += "--- Champions (Internal Advocates) ---\n"
        for contact in champions:
            output += f"  • {contact['Name']} - {contact['Title']}\n"
            output += f"    Email: {contact.get('Email', 'N/A')} | Phone: {contact.get('Phone', 'N/A')}\n"
        output += "\n"
    
    if influencers:
        output += "--- Influencers ---\n"
        for contact in influencers:
            output += f"  • {contact['Name']} - {contact['Title']}\n"
            output += f"    Email: {contact.get('Email', 'N/A')}\n"
        output += "\n"
    
    if users:
        output += "--- End Users ---\n"
        for contact in users:
            output += f"  • {contact['Name']} - {contact['Title']}\n"
        output += "\n"
    
    return output


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
        return f"No intent data found for company '{company_name}'."
    
    output = f"=== Customer Intent Analysis: {company_name} ===\n\n"
    
    if insights:
        output += "--- Buying Signals ---\n"
        output += f"{insights.get('Buying Signals', 'None identified')}\n\n"
        
        output += "--- Pain Points ---\n"
        output += f"{insights.get('Pain Points', 'None identified')}\n\n"
        
        output += "--- Recommended Positioning ---\n"
        output += f"{insights.get('Recommended Positioning', 'None specified')}\n\n"
    
    if opportunities:
        output += f"--- Active Opportunities ({len(opportunities)}) ---\n"
        for opp in opportunities[:5]:  # Show top 5
            output += f"\n• {opp['Opportunity Name']}\n"
            output += f"  Stage: {opp['Stage']}\n"
            output += f"  Est. MRC: ${opp.get('Total MRC (Est)', 0):,}\n"
            output += f"  BANT Score: {opp.get('BANT_Score_0to100', 0):.1f}/100 ({opp.get('BANT_Priority_Bucket', 'N/A')})\n"
            output += f"  Budget Status: {opp.get('Budget', 'Unknown')}\n"
            output += f"  Authority: {opp.get('Authority', 'Unknown')}\n"
            output += f"  Need Level: {opp.get('Need', 'Unknown')}\n"
            output += f"  Timeline: {opp.get('Timeline (days)', 'N/A')} days (Target: {opp.get('Target Close Date', 'N/A')})\n"
            output += f"  Next Step: {opp.get('Next Step', 'N/A')}\n"
            if opp.get('BANT_Data_Gaps'):
                output += f"  ⚠️ Data Gaps: {opp['BANT_Data_Gaps']}\n"
    
    if actions:
        output += f"\n--- Recommended Actions ---\n"
        output += f"Owner: {actions.get('Owner', 'Unassigned')}\n"
        output += f"Priority: {actions.get('Priority', 'Unknown')}\n"
        output += f"Initial Outreach: {actions.get('Initial Outreach Date', 'Not scheduled')}\n"
        output += f"Follow-Up: {actions.get('Follow-Up Cadence', 'Not defined')}\n"
    
    return output


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
        return f"No companies found with intent signals matching '{keyword}'."
    
    output = f"Found {len(results)} companies with '{keyword}' signals:\n\n"
    for company in results:
        output += f"Company: {company['Company Name']}\n"
        output += f"  Industry: {company['Industry']} | Region: {company['Territory/Region']}\n"
        output += f"  Buying Signals: {company.get('Buying Signals', 'N/A')}\n"
        output += f"  Pain Points: {company.get('Pain Points', 'N/A')}\n"
        output += f"  Positioning: {company.get('Recommended Positioning', 'N/A')}\n\n"
    
    return output


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
        return "No high-priority opportunities found."
    
    output = f"=== Top {len(opportunities)} Priority Opportunities ===\n\n"
    for i, opp in enumerate(opportunities, 1):
        output += f"{i}. {opp['Company Name']} - {opp['Opportunity Name']}\n"
        output += f"   Stage: {opp['Stage']} | MRC: ${opp.get('Total MRC (Est)', 0):,}\n"
        output += f"   BANT Score: {opp.get('BANT_Score_0to100', 0):.1f}/100 ({opp.get('BANT_Priority_Bucket', 'N/A')})\n"
        output += f"   Target Close: {opp.get('Target Close Date', 'N/A')}\n\n"
    
    return output


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
        products_of_interest: Comma-separated products (for prospects)
        zip_code: ZIP code (optional but recommended for serviceability checks)

    Returns:
        Success or failure message
    """
    success = db.add_company(
        company_name, industry, region, street, city, state, website,
        parent_company, existing_customer, current_products, products_of_interest, zip_code
    )

    if success:
        return f"✅ Successfully added company: {company_name}"
    else:
        return f"❌ Failed to add company '{company_name}'. It may already exist in the database."


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
        return "❌ No fields provided to update."

    success = db.update_company(company_name, **updates)

    if success:
        fields_updated = ', '.join(updates.keys())
        return f"✅ Successfully updated {company_name}: {fields_updated}"
    else:
        return f"❌ Failed to update company '{company_name}'. It may not exist in the database."


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
    
    if success:
        return f"✅ Successfully added contact: {contact_name} at {company_name}"
    else:
        return f"❌ Failed to add contact. Company '{company_name}' may not exist."


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
        return "❌ No fields provided to update."
    
    success = db.update_contact(company_name, contact_name, **updates)
    
    if success:
        fields_updated = ', '.join(updates.keys())
        return f"✅ Successfully updated contact {contact_name}: {fields_updated}"
    else:
        return f"❌ Failed to update contact '{contact_name}' at '{company_name}'."


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
    
    if success:
        return f"✅ Successfully updated insights for: {company_name}"
    else:
        return f"❌ Failed to update insights for '{company_name}'."


# Define the discovery agent
logger.info("DiscoveryAgent: Instantiating discovery_agent Agent object.")
discovery_agent = Agent(
    name="discovery_agent",
    model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    instruction="""You are a sales discovery specialist that helps identify and analyze prospective customers.

Your primary responsibilities:
1. **Customer Intent Identification**: Analyze buying signals, pain points, and opportunities to understand customer readiness and needs
2. **Company Details**: Provide comprehensive company information including industry, spending patterns, and business context
3. **Contact Persona Analysis**: Identify key decision makers, their roles, and influence in the buying process
4. **Database Management**: Add new companies, contacts, and insights; update existing records

When responding:
- Always start by understanding what specific information the user needs
- Use the appropriate tools to query the prospecting database
- Provide structured, actionable insights
- Highlight decision makers (Economic Buyers) and key influencers
- Surface high-priority opportunities and buying signals
- Recommend next steps based on BANT scores and customer readiness

Be conversational but data-driven. Focus on helping sales teams prioritize accounts and personalize their outreach.

**When a business is not recognized in the database:**
Respond in a customer-friendly way. Do not mention internal systems or databases. Instead, warmly welcome the user and guide them through providing the information needed to get started:

"We are more than happy to have you as a customer! Let's get you started. I'll just need a bit more information:"

**Required information to collect:**
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
- Products of Interest - Infer from conversation context

**IMPORTANT:** Do NOT ask for optional fields unless the customer volunteers them or they're clearly relevant. After collecting ONLY the required fields, immediately add the company to the database. Do not ask for contact information (name, email, title) during initial company setup - this can be collected later if needed.

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
- After all required fields are collected, use add_new_company to create the record and confirm with them
- Never ask the user if they are a customer or prospect; always infer this from the information you have
- Never ask the user for territory/region; always infer it from zip code or state
- Be polite and efficient, minimizing the number of questions by leveraging intelligent inference

When adding or updating data:
- Validate that required fields are provided
- Use proper formats (e.g., state abbreviations, Y/N for flags)
- Provide clear success/failure feedback

**After successfully adding a company with a complete address:**
Confirm the registration and then ASK the user if they would like to check service availability. Your response should be structured as:

"Welcome! I've registered **[Company Name]** at **[Full Address]**. 

Would you like me to check if this address is serviceable and what network infrastructure is available?"

This gives the user control over the next step in the conversation.
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
    ],
)
