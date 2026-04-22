# Serviceability Agent

**Type:** Deterministic Configuration Agent (PRE-SALE)
**Framework:** Google ADK 1.20.0
**Package:** `serviceability_agent`
**Status:** ✅ Deployed in SuperAgent

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [Root CLAUDE.md](/CLAUDE.md)
   - [Root AGENTS.md](/AGENTS.md)
   - This file (ServiceabilityAgent/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Agent development → [Root AGENTS.md - Golden Rule](/AGENTS.md#the-golden-rule)
   - GIS/Coverage tools → This file (see Tools section)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Purpose

The Serviceability Agent is a **PRE-SALE deterministic agent** that validates customer addresses and determines **network infrastructure availability** BEFORE any product quotes are generated. It acts as a gatekeeper to ensure service feasibility.

**Key Responsibilities:**

1. **Address Validation** - Parse and validate physical addresses
2. **Coverage Verification** - Check GIS/Coverage Map for infrastructure
3. **Technology Assessment** - Identify infrastructure type (FTTP, HFC, DOCSIS 3.1)
4. **Speed Capabilities** - Return min/max speed ranges supported
5. **Zone Classification** - Identify service zones for routing

**What it DOES NOT do:**
- ❌ Product recommendations (handled by ProductAgent)
- ❌ Pricing (handled by OfferManagementAgent)
- ❌ Installation scheduling (handled by ServiceFulfillmentAgent - POST-SALE)

---

## Architecture

### Agent Classification

| Attribute | Value |
|-----------|-------|
| **Type** | Deterministic |
| **Phase** | Configuration (Phase 2 - PRE-SALE) |
| **Source of Truth** | GIS/Coverage Map API |
| **Temperature** | 0.0 (fully deterministic, no creativity) |
| **top_p** | 0.1 (low sampling) |
| **top_k** | 10 (restricted tokens) |
| **Invocation** | After address extraction, before product recommendations |

### Component Structure

```
ServiceabilityAgent/
├── pyproject.toml                          # Package definition
├── serviceability_agent/
│   ├── __init__.py                         # Exports serviceability_agent
│   ├── agent.py                            # Main agent + config
│   ├── prompts.py                          # Agent instructions
│   ├── tools/
│   │   ├── address_tools.py                # Address validation (3 tools)
│   │   └── gis_tools.py                    # GIS/Coverage API (3 tools)
│   └── utils/
│       ├── logger.py                       # Structured logging
│       └── cache.py                        # 24-hour TTL cache
└── tests/
    ├── test_address_tools.py
    └── test_gis_tools.py
```

---

## Tools

The Serviceability Agent has **6 specialized tools** organized into two categories:

### Address Validation Tools

#### 1. `validate_and_parse_address(full_address: str)`

Parses and validates a complete address string.

**Input:** `"123 Main Street, Boston, MA 02101"`

**Returns:**
```python
{
    "valid": True,
    "street": "123 Main Street",
    "city": "Boston",
    "state": "MA",
    "zip_code": "02101",
    "standardized": "123 Main St, Boston, MA 02101"
}
```

**Handles:**
- Standardization (Street → St, Avenue → Ave)
- Validation (missing components, invalid formats)
- Correction suggestions for typos

#### 2. `normalize_address(street: str, city: str, state: str, zip_code: str)`

Normalizes address components into standardized format.

**Returns:** USPS-standardized address

#### 3. `extract_zip_code(address: str)`

Extracts ZIP code from unstructured address text.

**Returns:** 5-digit or 9-digit ZIP code

### GIS/Coverage Tools

#### 4. `check_service_availability(address: dict)`

**PRIMARY TOOL** - Checks if address is serviceable.

**Input:**
```python
{
    "street": "123 Main Street",
    "city": "Boston",
    "state": "MA",
    "zip_code": "02101"
}
```

**Returns:**
```python
{
    "serviceable": True,
    "infrastructure_type": "FTTP",  # Fiber-To-The-Premises
    "technology": "Fiber",
    "min_speed_mbps": 100,
    "max_speed_mbps": 10000,
    "service_zone": "Metro-East-MA",
    "network_elements": {
        "olt_id": "BOS-OLT-01",
        "splitter": "SPL-123",
        "fiber_pairs": 24
    }
}
```

**Possible Outcomes:**
- **Serviceable** (`serviceable: true`) - Infrastructure exists, speeds available
- **Not Serviceable** (`serviceable: false`) - No infrastructure at location
- **Partial Coverage** - Limited speeds or technology

#### 5. `get_infrastructure_by_technology(address: dict, technology: str)`

Queries coverage for specific technology type.

**Technologies:** `"Fiber"`, `"Coax"`, `"DSL"`, `"Fixed Wireless"`

**Returns:** Infrastructure details for that technology only

#### 6. `get_coverage_zones(city: str, state: str)`

Retrieves all service zones for a city/state.

**Returns:** List of serviceable zones with coverage maps

---

## GIS Coverage Map (Mock Data)

### Major Metro Areas

| Metro Area | Infrastructure | Max Speed | Service Zone |
|------------|---------------|-----------|--------------|
| **Boston, MA** | FTTP (Fiber) | 10 Gbps | Metro-East-MA |
| **Philadelphia, PA** | FTTP (Fiber) | 10 Gbps | Metro-East-PA |
| **New York, NY** | FTTP (Fiber) | 10 Gbps | Metro-East-NY |
| **Chicago, IL** | HFC (Coax) | 1 Gbps | Metro-Central-IL |
| **Los Angeles, CA** | FTTP (Fiber) | 10 Gbps | Metro-West-CA |
| **San Francisco, CA** | FTTP (Fiber) | 10 Gbps | Metro-West-CA |

### Infrastructure Types

| Type | Description | Technologies | Typical Speeds |
|------|-------------|--------------|----------------|
| **FTTP** | Fiber-To-The-Premises | Fiber Optic | 100 Mbps - 10 Gbps |
| **HFC** | Hybrid Fiber-Coax | DOCSIS 3.1 | 100 Mbps - 1 Gbps |
| **FTTN** | Fiber-To-The-Node | VDSL2 | 25 Mbps - 100 Mbps |
| **Fixed Wireless** | 5G/LTE | Wireless | 50 Mbps - 1 Gbps |

---

## Integration with SuperAgent

### Importlib Wrapper

Located at: `SuperAgent/super_agent/sub_agents/serviceability/agent.py`

**Pattern:** Same importlib isolation as DiscoveryAgent

**Loaded modules:**
- `prompts.py`
- `utils/logger.py`
- `tools/address_tools.py`
- `tools/gis_tools.py`
- `agent.py`

### Routing Rule

**Priority:** #2 (Service Availability and Address Validation)

**Trigger Examples:**
- "Is fiber available at 123 Main Street, Boston, MA?"
- "Can you check if my address is serviceable?"
- "What network infrastructure do you have at my location?"
- "What speeds are available at my address?"

**SuperAgent forwards to ServiceabilityAgent when:** Customer requests address validation or coverage check

---

## Workflow

### Typical Flow

```
1. User provides address
   ↓
2. validate_and_parse_address()
   → Returns standardized address
   ↓
3. check_service_availability()
   → Queries GIS API
   → Returns infrastructure details
   ↓
4. Agent responds:
   "Your location is serviceable!
    Infrastructure: Fiber (FTTP)
    Speeds: 100 Mbps - 10 Gbps
    Zone: Metro-East-MA"
   ↓
5. SuperAgent routes to ProductAgent
   → ProductAgent filters products by infrastructure constraints
```

### Response Format

**Serviceable Address:**
```
Your address is serviceable!

Infrastructure Type: Fiber (FTTP)
Speed Capability: 100 Mbps - 10 Gbps (symmetrical)
Service Zone: Metro-East-MA
Network Element: BOS-OLT-01

Available products will be filtered based on this infrastructure.
```

**Non-Serviceable Address:**
```
I apologize, but we don't currently service that address.

Reason: No fiber infrastructure at location
Nearest Serviceable Zone: 2.5 miles away (Metro-East-MA)

Would you like us to notify you when coverage expands to your area?
```

---

## Caching Strategy

**24-Hour TTL Cache:**
- Address validation results cached for 1 day
- Reduces GIS API load for repeated queries
- Cache key: Standardized address hash

**Benefits:**
- Faster responses for repeated addresses
- Lower API costs
- Consistent results within cache window

---

## Key vs. ServiceFulfillmentAgent

| Aspect | ServiceabilityAgent (PRE-SALE) | ServiceFulfillmentAgent (POST-SALE) |
|--------|--------------------------------|--------------------------------------|
| **Timing** | Before quote generation | After order confirmation |
| **Purpose** | "Can we serve this address?" | "When can we install?" |
| **Input** | Customer address | Confirmed order + Customer availability |
| **Output** | Boolean + Infrastructure details + Speed ranges | Installation date + Technician assignment |
| **Data Source** | GIS/Coverage Map API | Scheduler/Workforce Management API |
| **Decision** | Technical feasibility | Logistics scheduling |

---

## Development

### Standalone Testing

```bash
cd ServiceabilityAgent
pip install -e .

# Set environment variables
export GEMINI_MODEL="gemini-3-flash-preview"
export AGENT_NAME="serviceability_agent"

# Run agent
python main.py  # FastAPI server
# OR
adk web  # ADK web UI
```

### Running Tests

```bash
pytest tests/ -v

# Specific test
pytest tests/test_gis_tools.py::test_check_service_availability
```

### Adding New Coverage

Update mock GIS data in `tools/gis_tools.py`:

```python
COVERAGE_MAP = {
    "new_city_state_zip": {
        "serviceable": True,
        "infrastructure_type": "FTTP",
        "max_speed_mbps": 10000,
        # ...
    }
}
```

---

## Common Issues

### Issue: Always returning "Not Serviceable"

**Debug:**
1. Check address format (must be standardized)
2. Verify GIS API mock data includes address
3. Check logs for validation errors

### Issue: Wrong infrastructure type returned

**Fix:** Update `COVERAGE_MAP` in `gis_tools.py`

### Issue: ProductAgent recommending unavailable products

**Cause:** ServiceabilityAgent not providing infrastructure context

**Fix:** Ensure `check_service_availability` returns full infrastructure details

---

## Related Documentation

- **Root Architecture:** [/AGENTS.md](/AGENTS.md)
- **SuperAgent Integration:** [/SuperAgent/super_agent/sub_agents/AGENTS.md](/SuperAgent/super_agent/sub_agents/AGENTS.md)
- **ProductAgent (downstream):** [/ProductAgent/AGENTS.md](/ProductAgent/AGENTS.md)
- **ServiceFulfillmentAgent (POST-SALE):** [/ServiceFulfillmentAgent/AGENTS.md](/ServiceFulfillmentAgent/AGENTS.md)
- **GIS Tools Implementation:** `serviceability_agent/tools/gis_tools.py`
