# Discovery Agent

**Type:** Operational Agent (Discovery Phase)
**Framework:** Google ADK 1.20.0+
**Package:** `bootstrap_agent`
**Status:** ✅ Deployed in SuperAgent

---

## Purpose

The Discovery Agent specializes in **prospect identification, qualification, and data collection** for B2B sales. It:

1. **Extracts** company details from natural conversation
2. **Looks up** existing prospects in the unified database
3. **Creates** new prospect records with intelligent slot-filling
4. **Qualifies** leads using conversational BANT scoring (Budget, Authority, Need, Timeline)
5. **Maps** contact personas and decision-makers
6. **Captures** products of interest using explicit keyword-to-category mapping
7. **Creates** opportunity records with automatic BANT scoring

This is the **first agent invoked** when a customer shares their company information.

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `discovery_agent` (hardcoded) |
| **Model** | `os.getenv("GEMINI_MODEL")` — no default, fails fast |
| **Temperature** | 0.7 (conversational but structured) |
| **Phase** | Discovery (Phase 1 of sales cycle) |
| **Database** | Unified `sales_agent.db` via `SALES_AGENT_DB_PATH` env var |
| **Fallback DB** | `DiscoveryAgent/data/discover_prospecting_clean.db` |

### Component Structure

```
DiscoveryAgent/
├── pyproject.toml
├── bootstrap_agent/
│   ├── __init__.py
│   ├── agent.py                            # Root agent (standalone mode)
│   ├── sub_agents/
│   │   ├── discovery/
│   │   │   ├── __init__.py
│   │   │   ├── discovery_agent.py          # Agent definition + instructions
│   │   │   └── db_tools.py                 # ProspectingDatabase class
│   │   └── lead_gen/
│   │       └── qualification_tools.py      # BANT scoring
│   └── utils/
│       ├── custom_logger.py
│       └── gcp_tools.py
├── data/
│   └── discover_prospecting_clean.db       # Legacy standalone DB
└── tests/
```

### Database Tables (6 tables — Discovery Domain)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `accounts` | Company records | Company Name (PK), Street, City, State, zip_code, Industry, customer_id |
| `contacts` | People at companies | Company Name (FK), Name, Title, Role, Email, Phone |
| `spend` | Advertising spend data | Company Name (FK), Estimated Annual Spend, channel breakdowns |
| `opportunities` | Sales pipeline | Company Name (FK), Stage, BANT scores, Target Close Date |
| `insights` | Buying intelligence | Company Name (FK), Buying Signals, Pain Points |
| `actions` | Follow-up tasks | Company Name (FK), Owner, Priority, Cadence |

---

## Tools (13 Functions)

### Read Tools

| Tool | Signature | Tables Read |
|------|-----------|-------------|
| `search_companies` | `(company_name, industry, region, customer_status, street, city, state)` | `accounts` |
| `get_company_profile` | `(company_name)` | `accounts` JOIN `spend` |
| `get_contact_personas` | `(company_name)` | `contacts` |
| `get_customer_intent` | `(company_name)` | `insights`, `opportunities` |
| `search_by_intent_signals` | `(keyword)` | `accounts` JOIN `insights` |
| `get_high_priority_opportunities` | `(limit=10)` | `opportunities` |
| `check_customer_state` | `(customer_id)` | All tables (cross-domain query) |

### Write Tools

| Tool | Signature | Tables Written |
|------|-----------|----------------|
| `add_new_company` | `(company_name, industry, region, street, city, state, zip_code, ...)` | `accounts` INSERT |
| `update_company_info` | `(company_name, **fields)` | `accounts` UPDATE |
| `add_new_contact` | `(company_name, contact_name, title, role, email, phone, notes)` | `contacts` INSERT |
| `update_contact_info` | `(company_name, contact_name, **fields)` | `contacts` UPDATE |
| `add_or_update_insights` | `(company_name, buying_signals, pain_points, positioning)` | `insights` INSERT OR REPLACE |
| `create_opportunity_from_bant` | `(company_name, opportunity_name, budget, authority, need, timeline_days, total_mrc, next_step)` | `opportunities` INSERT |

### Intelligent Features

- **Company Name fuzzy matching** via SQL LIKE
- **Auto-generated customer_id** (UUID) on company creation
- **BANT scoring** — automatic weighted score (0-100) with priority bucketing (A/B/C)
- **Zip code validation** — NOT NULL constraint enforced
- **Email & phone collection** — both required during BANT Authority phase; asked explicitly, retried once if skipped
- **JSON tool outputs** — all tools return structured JSON to prevent LLM hallucination

---

## Conversation Behavior

### When Invoked
SuperAgent routes to DiscoveryAgent when user mentions a company name, business, or office location.

### Handoff Pattern (Programmatic — Zero User Input)

After registering a company with a full address, DiscoveryAgent signals completion:
> "Welcome! I've registered **[Company]** at **[Address]**. Let me check if this address is serviceable..."

The SuperAgent wrapper's `after_agent_callback` detects this completion phrase and **programmatically transfers to `serviceability_agent`** in the same turn — no user message needed.

**Mechanism:** `SuperAgent/super_agent/sub_agents/discovery/agent.py` attaches `_discovery_after_agent` callback which:
1. Scans the agent's last output for phrases like "let me check", "serviceability", "check if this address"
2. Sets `callback_context.actions.transfer_to_agent = "serviceability_agent"`
3. ServiceabilityAgent executes immediately in the same ADK invocation

This is a **deterministic, same-turn handoff** — no LLM variability.

---

## Integration with SuperAgent

Loaded via **importlib isolation** in `SuperAgent/super_agent/sub_agents/discovery/agent.py` to avoid ADK parent-binding conflicts. The agent name `discovery_agent` is hardcoded — never read from environment.

**Wrapper features:**
- Importlib isolation (avoids `__init__.py` parent-binding)
- `after_agent_callback` for programmatic Discovery → Serviceability handoff
