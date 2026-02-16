# Discovery Agent

**Type:** Operational Agent (Discovery Phase)
**Framework:** Google ADK 1.20.0
**Package:** `bootstrap_agent`
**Status:** ✅ Deployed in SuperAgent

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [Root CLAUDE.md](/CLAUDE.md)
   - [Root AGENTS.md](/AGENTS.md)
   - This file (DiscoveryAgent/AGENTS.md)
   - Component README if exists

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Agent development → [Root AGENTS.md - Golden Rule](/AGENTS.md#the-golden-rule)
   - Database changes → This file (see Database Schema section)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Purpose

The Discovery Agent specializes in **prospect identification, qualification, and data collection** for B2B sales. It:

1. **Extracts** company details from natural conversation
2. **Looks up** existing prospects in the database
3. **Creates** new prospect records with intelligent slot-filling
4. **Qualifies** leads using BANT scoring (Budget, Authority, Need, Timeline)
5. **Maps** contact personas and decision-makers

This is the **first agent invoked** when a customer shares their company information.

---

## Architecture

### Agent Classification

| Attribute | Value |
|-----------|-------|
| **Type** | Operational |
| **Phase** | Discovery (Phase 1 of sales cycle) |
| **Source of Truth** | SQLite Database (`data/discover_prospecting_clean.db`) |
| **Temperature** | 0.7 (conversational but structured) |
| **Invocation** | Once per conversation when company details shared |

### Component Structure

```
DiscoveryAgent/
├── pyproject.toml                          # Package definition
├── bootstrap_agent/
│   ├── __init__.py                         # Exports discovery_agent
│   ├── agent.py                            # Root agent (if standalone)
│   ├── sub_agents/
│   │   └── discovery/
│   │       ├── __init__.py
│   │       ├── discovery_agent.py          # Main agent + instruction
│   │       └── db_tools.py                 # Database tool functions
│   ├── utils/
│   │   ├── custom_logger.py
│   │   └── gcp_tools.py
│   └── data/
│       └── discover_prospecting_clean.db   # SQLite prospect database
└── tests/
    └── test_discovery_agent.py
```

---

## Tools

The Discovery Agent has **8 specialized tools** for prospect management:

### 1. `search_by_company_name(company_name: str)`

Searches the prospect database by company name (fuzzy matching).

**Returns:** Company records with BANT scores, contacts, insights

### 2. `search_by_address(street: str, city: str, state: str, zip_code: str)`

Looks up prospects by physical address.

**Returns:** Matching company records at that location

### 3. `search_by_phone(phone_number: str)`

Finds prospects by contact phone number.

**Returns:** Company and contact information

### 4. `search_by_email(email: str)`

Locates prospects by email address.

**Returns:** Contact and company details

### 5. `search_by_intent_signals(keywords: list[str])`

Searches for prospects expressing specific buying signals or product interests.

**Returns:** Prospects matching intent keywords

### 6. `get_high_priority_opportunities(min_bant_score: int = 70)`

Retrieves prospects with high BANT qualification scores.

**Returns:** List of hot leads ready for engagement

### 7. `add_new_company(...)`

Creates a new prospect record with intelligent slot-filling.

**Required Fields:**
- Company Name
- Industry
- Address (Street, City, State, Zip)
- Region (auto-inferred from state/zip)

**Optional Fields:**
- Website, Parent Company, Products of Interest

**Intelligent Inference:**
- Industry auto-detected from business type mentions
- Address components extracted from full address strings
- Region auto-assigned based on zip code/state
- Multi-field extraction from single user messages

### 8. `update_company_info(company_id: int, ...)`

Updates existing prospect data.

**Updatable Fields:** All company fields, BANT scores, status

---

## Intelligent Inference

The Discovery Agent uses **context clues** to minimize redundant questions:

### Industry Inference

Automatically maps business type mentions to industry codes:

- "pizza shop", "restaurant" → Restaurant/Food Service
- "law firm" → Legal Services
- "accounting firm", "CPA firm" → Professional Services - Accounting
- "dental clinic" → Healthcare - Dental
- "auto repair" → Automotive Services
- "retail store", "boutique" → Retail
- "tech company", "software company" → Technology

### Address Inference

Extracts ALL components from full address strings:

**Input:** "123 Main Street, Boston, MA 02101"
**Extracted:** Street="123 Main Street", City="Boston", State="MA", Zip="02101"

**Does NOT ask** for components already extracted.

### Multi-Field Extraction

Captures multiple fields from a single message:

**Input:** "We're a pizza shop at 123 Main St, Boston MA"
**Extracted:** Industry=Restaurant/Food Service, Street="123 Main St", City="Boston", State="MA"

### Territory/Region Auto-Assignment

**Never asks** the user for region—infers from zip code or state:

- **East:** NY, NJ, PA, CT, MA, RI, NH, VT, ME, MD, DE, VA, WV, DC
- **Central:** IL, IN, MI, OH, WI, MN, IA, MO, KS, NE, SD, ND
- **West:** CA, WA, OR, NV, AZ, NM, CO, UT, ID, MT, WY, AK, HI
- **South:** TX, OK, AR, LA, MS, AL, TN, KY, FL, GA, SC, NC

---

## BANT Scoring

The agent qualifies leads using BANT methodology:

| Factor | Weight | Criteria |
|--------|--------|----------|
| **Budget** | 25% | Authority to spend, budget cycle timing |
| **Authority** | 30% | Decision-maker access, procurement process |
| **Need** | 25% | Pain points, urgency, current solutions |
| **Timeline** | 20% | Purchase timeframe, contract renewal dates |

**Scoring:**
- 0-40: Cold lead (nurture only)
- 41-69: Warm lead (qualified follow-up)
- 70-100: Hot lead (immediate engagement)

---

## Integration with SuperAgent

### Importlib Wrapper

Located at: `SuperAgent/super_agent/sub_agents/discovery/agent.py`

**Why importlib?** ADK enforces one parent per agent. The wrapper loads DiscoveryAgent's `discovery_agent` instance without executing `__init__.py`, creating a fresh instance for SuperAgent's hierarchy.

### Routing Rule

**Priority:** #1 (Company/Business Identification)

**Trigger Examples:**
- "We're VoiceStream Networks"
- "I work at DataSync Technologies"
- "Our company is Acme Corp"

**Invocation:** **ONCE per conversation** when company details first shared

**SuperAgent forwards to DiscoveryAgent when:** Customer mentions company/business name or details

---

## Database Schema

### Companies Table

```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL,
    industry TEXT,
    employee_count INTEGER,
    annual_revenue REAL,
    address_street TEXT,
    address_city TEXT,
    address_state TEXT,
    address_zip TEXT,
    region TEXT,  -- East/Central/West/South
    phone TEXT,
    website TEXT,
    parent_company TEXT,
    products_of_interest TEXT,
    bant_budget_score INTEGER,
    bant_authority_score INTEGER,
    bant_need_score INTEGER,
    bant_timeline_score INTEGER,
    bant_total_score INTEGER,
    status TEXT,  -- Lead/Prospect/Customer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Contacts Table

```sql
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY,
    company_id INTEGER,
    first_name TEXT,
    last_name TEXT,
    title TEXT,
    email TEXT,
    phone TEXT,
    persona TEXT,  -- Decision Maker/Influencer/End User
    FOREIGN KEY (company_id) REFERENCES companies(id)
);
```

---

## Development

### Standalone Testing

```bash
cd DiscoveryAgent
pip install -e .
adk web  # Launch ADK web UI
```

### Running Tests

```bash
pytest tests/test_discovery_agent.py -v
```

### Adding New Tools

1. Define function in `bootstrap_agent/sub_agents/discovery/db_tools.py`
2. Add `@FunctionTool` decorator (or wrap in discovery_agent.py)
3. Add to `tools` list in `discovery_agent.py`
4. Update this documentation

---

## Key Behaviors

### Slot-Filling Guidelines

1. **FIRST**, check if you can **INFER** any fields from context
2. Ask for **one** missing required field at a time ONLY if you cannot infer it
3. If user provides multiple fields in one message, fill as many as possible
4. Do NOT ask for information you already have from the conversation
5. After all required fields are collected, use `add_new_company` to create the record
6. Never ask the user if they are a customer or prospect (infer from context)
7. Never ask for territory/region (auto-infer from zip/state)
8. Be polite and efficient, minimizing questions via intelligent inference

### Conversation Flow

```
User: "Hi, we're a pizza shop looking for internet"

Agent: (Infers Industry=Restaurant/Food Service)
       "Great! To check service availability, could you share your business address?"

User: "123 Main St, Boston MA 02101"

Agent: (Extracts all address components + infers Region=East)
       (Calls add_new_company with: Industry, Street, City, State, Zip, Region)
       "Welcome! I've registered [Company] at [Address].
       
       Would you like me to check if this address is serviceable and what network infrastructure is available?"

User: "Yes" or "Yes, check availability"

Agent: (SuperAgent routes to ServiceabilityAgent)
       ServiceabilityAgent: "✅ This location is serviceable..."
```

---

## Multi-Agent Workflow

### Current Implementation: Natural Two-Step Flow

The Discovery → Serviceability transition uses a **natural two-step conversational flow**:

**Step 1:** DiscoveryAgent registers company and **asks** user:
```
"Would you like me to check if this address is serviceable?"
```

**Step 2:** User confirms (e.g., "Yes"), then SuperAgent routes to ServiceabilityAgent

**Rationale:**
- ✅ **ADK-aligned:** Respects ADK's one-turn-per-agent model
- ✅ **User control:** Customer explicitly chooses next step
- ✅ **Simple:** No server-side pattern matching or recursive routing
- ✅ **Predictable:** No LLM text generation variations to handle

**Alternative Architectures Considered:**

1. **Recursive Router (Server-Side)** ❌
   - Server detects "Let me check..." pattern in response
   - Automatically sends follow-up message to continue workflow
   - **Issues:** Fights ADK architecture, brittle pattern matching, unpredictable LLM output

2. **Tool-Based Handoff** ⚠️ (Future)
   - DiscoveryAgent calls `initiate_serviceability_check(address)` tool
   - Tool signals SuperAgent to route to ServiceabilityAgent
   - **Benefits:** Deterministic, ADK-native, no text parsing
   - **Status:** Can be implemented if fully automatic flow needed

**Decision:** Natural two-step flow chosen for simplicity and ADK alignment. Can be revisited if automation requirements change.

---

## Common Issues

### Issue: Asking "What industry?" for "pizza shop"

**Fix:** Review INTELLIGENT INFERENCE section in `discovery_agent.py` instruction

### Issue: Asking for individual address components after full address provided

**Fix:** Ensure Address Inference logic is extracting all components

### Issue: Multiple company records created for same business

**Fix:** Use `search_by_company_name` before `add_new_company`

---

## Related Documentation

- **Root Architecture:** [/AGENTS.md](/AGENTS.md)
- **SuperAgent Integration:** [/SuperAgent/super_agent/sub_agents/AGENTS.md](/SuperAgent/super_agent/sub_agents/AGENTS.md)
- **Database Tools:** `bootstrap_agent/sub_agents/discovery/db_tools.py`
- **Test Scenarios:** [/Scenarios.md](/Scenarios.md)
