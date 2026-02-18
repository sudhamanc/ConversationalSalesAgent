# Discovery Sub-Agent Documentation

This document describes the Discovery Sub-Agent created for identifying customer intent, company details, and contact personas using the prospecting database.

## Overview

The Discovery Agent is a specialized sales prospecting agent that queries the `discover_prospecting_clean.db` SQLite database to provide insights about companies, contacts, opportunities, and buying signals.

## Files Created

### 1. Sub-Agent Module: `bootstrap_agent/sub_agents/discovery/`

#### `__init__.py`
Package initialization file that exports the discovery_agent.

#### `db_tools.py`
Database interface layer containing the `ProspectingDatabase` class with the following methods:

- **`search_companies()`** - Search by company name, industry, or region
- **`get_company_details()`** - Full company profile with advertising spend data
- **`get_contacts_for_company()`** - All contacts for a specific company
- **`get_decision_makers()`** - Economic buyers and key decision makers
- **`get_opportunities_for_company()`** - Active opportunities with BANT scores
- **`get_insights_for_company()`** - Buying signals, pain points, and recommended positioning
- **`get_actions_for_company()`** - Recommended outreach actions
- **`get_high_priority_opportunities()`** - Top opportunities across all companies
- **`search_by_intent_signals()`** - Find companies by specific buying signals or pain points

#### `discovery_agent.py`
Main agent definition with 6 agent tools:

1. **`search_companies`** - Find companies by name, industry, or region
   ```python
   search_companies(company_name="Tech", industry="Technology", region="West")
   ```

2. **`get_company_profile`** - Comprehensive company information including spend breakdown
   ```python
   get_company_profile("Company 001")
   ```

3. **`get_contact_personas`** - Identifies decision makers by role
   - Economic Buyers (final decision authority)
   - Technical Buyers (technical evaluation)
   - Champions (internal advocates)
   - Influencers
   - End Users
   ```python
   get_contact_personas("Company 001")
   ```

4. **`get_customer_intent`** - Analyzes buying signals, pain points, and opportunities
   ```python
   get_customer_intent("Company 001")
   ```

5. **`search_by_intent_signals`** - Find companies showing specific buying behaviors
   ```python
   search_by_intent_signals("funding round")
   ```

6. **`get_high_priority_opportunities`** - Top BANT-scored opportunities
   ```python
   get_high_priority_opportunities(limit=10)
   ```

### 2. Root Agent Integration: `bootstrap_agent/agent.py`

The discovery agent has been registered with the root orchestrator agent:
- Imported `discovery_agent` from the sub_agents module
- Added to the `sub_agents` list
- Updated orchestrator instructions to route sales/prospecting queries to the discovery agent

### 3. Utility Scripts

#### `explore_db.py`
Database exploration script that displays:
- All tables in the database
- Column schemas for each table
- Sample data (first 3 rows)
- Row counts

#### `test_discovery_agent.py`
Comprehensive test script that verifies:
- Database tools functionality
- Agent tools functionality
- Example queries for each tool

## Database Schema

### Tables:
1. **accounts** - Company information (50 records)
   - Company Name, Parent Company, Industry, Territory/Region, Address, Website

2. **contacts** - Contact information (142 records)
   - Company Name, Name, Title, Role in Decision Making, Email, Phone, Notes

3. **spend** - Advertising spend data (50 records)
   - Estimated Annual Spend, Digital, Programmatic, TV, Audio, OOH, Search, Social, Primary Agency

4. **opportunities** - Sales opportunities (102 records)
   - Opportunity Name, Stage, Total MRC, Budget, Authority, Need, Timeline, BANT scores

5. **insights** - Customer intelligence (50 records)
   - Buying Signals, Pain Points, Recommended Positioning

6. **actions** - Recommended actions (50 records)
   - Owner, Priority, Initial Outreach Date, Follow-Up Cadence

## Agent Capabilities

### 1. Customer Intent Identification
- Analyzes buying signals (e.g., "funding round", "new product launch")
- Identifies pain points (e.g., "Rising CAC", "Low attribution visibility")
- Surfaces opportunities with BANT scoring
- Recommends positioning strategies

### 2. Company Details
- Industry and regional information
- Advertising spend breakdown by channel (Digital, TV, Audio, Search, Social, etc.)
- Parent company relationships
- Primary agency partnerships

### 3. Contact Persona Analysis
- Identifies decision maker hierarchy:
  - **Economic Buyers** - Final budget/purchase authority
  - **Technical Buyers** - Evaluate technical fit
  - **Champions** - Internal advocates for your solution
  - **Influencers** - Influence decision but no direct authority
  - **End Users** - Will use the product/service
- Provides contact details (email, phone)
- Includes relevant notes

## Usage Examples

### Example 1: Find Technology Companies
```
User: "Show me technology companies in the West region"
Agent: Uses search_companies(industry="Technology", region="West")
```

### Example 2: Analyze a Specific Company
```
User: "Tell me about Company 001"
Agent: Uses get_company_profile("Company 001") and get_customer_intent("Company 001")
```

### Example 3: Identify Decision Makers
```
User: "Who are the key contacts at Company 002?"
Agent: Uses get_contact_personas("Company 002")
```

### Example 4: Find High-Intent Prospects
```
User: "Show me companies with funding round signals"
Agent: Uses search_by_intent_signals("funding")
```

### Example 5: Prioritize Opportunities
```
User: "What are our top opportunities?"
Agent: Uses get_high_priority_opportunities()
```

## Known Issues

**ADK 1.20.0 Import Error**: There is currently a compatibility issue with the `agent_tool` decorator in Google ADK 1.20.0. The import should use `FunctionTool` class instead. This needs to be fixed before the agent can run successfully.

### Potential Fixes:
1. Downgrade to Python 3.11 (most stable)
2. Use ADK 1.10.0 instead of 1.20.0
3. Pin Pydantic to a compatible version (2.9.x or 2.10.x)
4. Update tool definitions to use `FunctionTool` class (recommended for ADK 1.20.0)

## Future Enhancements

Potential additions to the discovery agent:
1. Industry-specific analysis tools
2. Competitive intelligence integration
3. Predictive lead scoring
4. Automated outreach recommendations
5. Territory management tools
6. Integration with CRM systems
