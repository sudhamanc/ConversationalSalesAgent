"""Simple chat interface using Gemini API with prospect database tools"""

import os
from typing import Dict, Any
from google import genai
from dotenv import load_dotenv

# Import database tools
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bootstrap_agent'))
from bootstrap_agent.sub_agents.discovery.db_tools import ProspectingDatabase
from bootstrap_agent.sub_agents.lead_gen.qualification_tools import LeadQualificationDatabase

# Load environment
load_dotenv()

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'discover_prospecting_clean.db')

# Initialize databases
discovery_db = ProspectingDatabase(DB_PATH)
qualification_db = LeadQualificationDatabase(DB_PATH)


class ProspectChatAgent:
    """Simple chat agent for prospect queries using Gemini API"""
    
    def __init__(self, api_key: str = None):
        # Configure Gemini
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            raise ValueError("GOOGLE_API_KEY not configured in .env file")
        
        # Initialize client
        self.client = genai.Client(api_key=api_key)
        
        # Model name
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        
        # System prompt
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with available tools and data context"""
        return """You are a sales intelligence assistant with access to a prospecting database. 

You can help with:
1. **Company Discovery**: Find companies by name, industry, region, or product interest
2. **Contact Information**: Identify decision makers, economic buyers, champions
3. **Customer Intent**: Analyze buying signals and pain points
4. **Lead Qualification**: BANT scoring and sales readiness assessment
5. **Pipeline Prioritization**: Rank opportunities by score and urgency
6. **Product Analysis**: Find customers with current products or prospects interested in specific products

Available data:
- 100 companies across various industries (Technology, Retail, Healthcare, Finance, etc.)
- Customer Status: 61 existing customers, 39 prospects
- Products: Internet, Voice, Video, SDWAN, Business Mobile
- Existing Customers have "Current Products"
- Prospects have "Products of Interest"
- 142+ contacts with roles (Economic Buyer, Champion, Influencer, etc.)
- 138+ opportunities with BANT qualification scores
- Buying signals, pain points, and recommended positioning
- Advertising spend data by channel

When asked about specific companies or prospects:
1. I will query the database to get accurate, real information
2. Provide specific data points from the database, never make up companies
3. Use BANT scores (0-100) to assess qualification
4. Highlight decision makers and key contacts
5. Surface actionable insights and next steps

IMPORTANT: I must ONLY return actual companies from the database. I will never invent or hallucinate company names."""

    def query_database(self, intent: str, query_params: Dict[str, Any]) -> str:
        """Query the database based on detected intent"""
        
        intent = intent.lower()
        
        try:
            # Product interest search (NEW)
            if any(prod in intent for prod in ["internet", "voice", "video", "sdwan", "mobile", "product"]):
                # Extract product name
                products = []
                if "internet" in intent:
                    products.append("Internet")
                if "voice" in intent:
                    products.append("Voice")
                if "video" in intent:
                    products.append("Video")
                if "sdwan" in intent:
                    products.append("SDWAN")
                if "mobile" in intent or "business mobile" in intent:
                    products.append("Business Mobile")
                
                if products:
                    # Check if looking for customers or prospects
                    is_existing = "customer" in intent or "existing" in intent or "current" in intent
                    is_prospect = "prospect" in intent or "interested" in intent
                    
                    all_results = []
                    
                    # Search prospects (Products of Interest)
                    if is_prospect or not is_existing:
                        companies = discovery_db.search_companies(customer_status='N')
                        for c in companies:
                            poi = c.get('Products of Interest', '')
                            if poi and any(p in poi for p in products):
                                all_results.append({
                                    'company': c,
                                    'status': 'Prospect',
                                    'products': poi
                                })
                    
                    # Search existing customers (Current Products)
                    if is_existing or not is_prospect:
                        companies = discovery_db.search_companies(customer_status='Y')
                        for c in companies:
                            cp = c.get('Current Products', '')
                            if cp and any(p in cp for p in products):
                                all_results.append({
                                    'company': c,
                                    'status': 'Existing Customer',
                                    'products': cp
                                })
                    
                    if all_results:
                        result = f"Found {len(all_results)} companies with {', '.join(products)}:\n\n"
                        for item in all_results[:15]:  # Show up to 15
                            c = item['company']
                            result += f"**{c['Company Name']}**\n"
                            result += f"  Industry: {c['Industry']}\n"
                            result += f"  Location: {c['Street']}, {c['City']}, {c['State']}\n"
                            result += f"  Status: {item['status']}\n"
                            if item['status'] == 'Prospect':
                                result += f"  Products of Interest: {item['products']}\n"
                            else:
                                result += f"  Current Products: {item['products']}\n"
                            result += "\n"
                        return result
                    return f"No companies found with {', '.join(products)}."
            
            # Company search
            if "search" in intent or "find companies" in intent:
                companies = discovery_db.search_companies(
                    company_name=query_params.get("company_name"),
                    industry=query_params.get("industry"),
                    region=query_params.get("region"),
                    customer_status=query_params.get("customer_status")
                )
                if companies:
                    result = f"Found {len(companies)} companies:\n"
                    for c in companies[:10]:
                        status = "Existing Customer" if c.get('Existing Customer') == 'Y' else "Prospect"
                        result += f"- **{c['Company Name']}** ({c['Industry']}, {c['City']}, {c['State']}) - {status}\n"
                    return result
                return "No companies found matching criteria."
            
            # Company details (address, location, or general info about a company)
            if query_params.get("company_name") and any(keyword in intent for keyword in ["address", "location", "where", "company", "about", "tell me", "information", "details"]):
                company = discovery_db.get_company_details(query_params["company_name"])
                if company:
                    result = f"**{company['Company Name']}**\n"
                    result += f"Industry: {company['Industry']}\n"
                    result += f"Location: {company['Street']}, {company['City']}, {company['State']}\n"
                    result += f"Region: {company['Territory/Region']}\n"
                    result += f"Status: {'Existing Customer' if company.get('Existing Customer') == 'Y' else 'Prospect'}\n"
                    if company.get('Current Products'):
                        result += f"Current Products: {company['Current Products']}\n"
                    if company.get('Products of Interest'):
                        result += f"Products of Interest: {company['Products of Interest']}\n"
                    if company.get('Estimated Annual Spend'):
                        result += f"Annual Spend: ${company['Estimated Annual Spend']:,}\n"
                    return result
                return f"Company '{query_params['company_name']}' not found."
            
            # Contacts
            elif "contact" in intent or "decision maker" in intent:
                contacts = discovery_db.get_contacts_for_company(query_params.get("company_name", ""))
                if contacts:
                    result = f"Contacts for {query_params.get('company_name')}:\n"
                    for c in contacts[:5]:
                        result += f"- {c['Name']}: {c['Title']} ({c['Role in Decision Making']})\n"
                    return result
                return "No contacts found."
            
            # Intent/Insights
            elif "intent" in intent or "signal" in intent:
                insights = discovery_db.get_insights_for_company(query_params.get("company_name", ""))
                if insights:
                    result = f"Intent Analysis:\n"
                    result += f"Buying Signals: {insights.get('Buying Signals')}\n"
                    result += f"Pain Points: {insights.get('Pain Points')}\n"
                    result += f"Positioning: {insights.get('Recommended Positioning')}\n"
                    return result
                return "No intent data found."
            
            # Qualification
            elif "bant" in intent or "qualified" in intent or "score" in intent:
                opps = qualification_db.get_opportunity_qualification(query_params.get("company_name", ""))
                if opps:
                    result = f"BANT Qualification:\n"
                    for opp in opps[:3]:
                        result += f"\n{opp['Opportunity Name']}: {opp['BANT_Score_0to100']:.1f}/100\n"
                        result += f"  Budget: {opp.get('Budget')}, Authority: {opp.get('Authority')}\n"
                        result += f"  Need: {opp.get('Need')}, Timeline: {opp.get('Timeline (days)')} days\n"
                    return result
                return "No qualification data found."
            
            # High priority
            elif "priority" in intent or "top" in intent:
                opps = qualification_db.get_high_priority_opportunities(10)
                if opps:
                    result = "Top Priority Opportunities:\n"
                    for i, opp in enumerate(opps[:5], 1):
                        result += f"{i}. {opp['Company Name']}: {opp['BANT_Score_0to100']:.1f}/100\n"
                    return result
                return "No high-priority opportunities found."
            
        except Exception as e:
            return f"Database query error: {str(e)}"
        
        return "Query type not recognized."
    
    def _extract_company_name(self, user_message: str) -> str:
        """Extract company name from user message using smart patterns"""
        msg_lower = user_message.lower()
        
        # Pattern 1: Various prepositions before company name
        prep_patterns = [
            " for ",
            " about ",
            " on ",
            " at ",
            "tell me about ",
            "information about ",
            "details about ",
            "info on "
        ]
        
        for prep in prep_patterns:
            if prep in msg_lower:
                idx = msg_lower.index(prep) + len(prep)
                remaining = user_message[idx:].strip()
                # Take words until we hit a common stop word or punctuation
                words = []
                for word in remaining.split():
                    word_clean = word.strip("?,.")
                    if word_clean.lower() in ["and", "or", "with", "in", "the"]:
                        break
                    if word_clean:
                        words.append(word_clean)
                if words:
                    potential = " ".join(words).strip("?,.")
                    # Try to search - if we get results, this is the company name
                    results = discovery_db.search_companies(company_name=potential)
                    if results and len(results) > 0:
                        # Return the exact company name from the database
                        return results[0]['Company Name']
        
        # Pattern 2: Look for capitalized sequences (2-4 words) that look like company names
        words = user_message.split()
        for i in range(len(words)):
            # Try sequences of different lengths, longest first
            for length in [4, 3, 2]:
                if i + length <= len(words):
                    potential_words = [w.strip("?,.") for w in words[i:i+length]]
                    # Check if most words start with capital (allowing for lowercase words like "and")
                    caps_count = sum(1 for w in potential_words if w and len(w) > 0 and w[0].isupper())
                    if caps_count >= max(1, len(potential_words) - 1):  # Allow one lowercase word
                        potential = " ".join(potential_words)
                        # Try to find in database
                        results = discovery_db.search_companies(company_name=potential)
                        if results and len(results) > 0:
                            return results[0]['Company Name']
        
        # Pattern 3: "Company XXX" format (original logic)
        for i, word in enumerate(words):
            if word.lower() == "company" and i + 1 < len(words):
                potential_name = f"Company {words[i+1].strip('?.,')}"
                results = discovery_db.search_companies(company_name=potential_name)
                if results and len(results) > 0:
                    return results[0]['Company Name']
        
        return None

    def send_message(self, user_message: str) -> str:
        """Process a user message and return response"""
        
        # Detect if this needs database query
        needs_data = any(keyword in user_message.lower() for keyword in [
            "company", "companies", "contact", "bant", "score", "qualified", "priority",
            "signal", "intent", "decision maker", "opportunity", "pipeline",
            "internet", "voice", "video", "sdwan", "mobile", "product",
            "customer", "prospect", "interested", "show me", "find", "list",
            "address", "location", "where"
        ])
        
        if needs_data:
            # Extract company name if mentioned
            company_name = self._extract_company_name(user_message)
            
            # Extract customer status
            customer_status = None
            msg_lower = user_message.lower()
            if "existing customer" in msg_lower or "current customer" in msg_lower:
                customer_status = 'Y'
            elif "prospect" in msg_lower:
                customer_status = 'N'
            
            # Build query params
            query_params = {
                "company_name": company_name,
                "customer_status": customer_status
            }
            
            # Detect intent and query database
            db_result = self.query_database(user_message.lower(), query_params)
            
            # Build prompt with system context and database results
            full_prompt = f"""{self.system_prompt}

User Question: {user_message}

Database Results:
{db_result}

Based on the database results above, provide a clear and helpful answer. Use ONLY the companies listed in the database results - do not make up or hallucinate any company names."""
        else:
            # Regular chat with system context
            full_prompt = f"""{self.system_prompt}

User Question: {user_message}"""
        
        # Generate response using the client
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=full_prompt
        )
        
        # Extract response text
        return response.text


# Initialize global chat agent
chat_agent = None

def get_chat_agent() -> ProspectChatAgent:
    """Get or create the global chat agent"""
    global chat_agent
    if chat_agent is None:
        chat_agent = ProspectChatAgent()
    return chat_agent

def send_chat_message(message: str) -> str:
    """Send a chat message and get response"""
    agent = get_chat_agent()
    return agent.send_message(message)
