# Serviceability Agent

**Type:** Deterministic Configuration Agent (PRE-SALE)
**Framework:** Google ADK 1.20.0+
**Package:** `serviceability_agent`
**Status:** ✅ Deployed in SuperAgent

---

## Purpose

The Serviceability Agent performs **pre-sale address validation and infrastructure assessment**. It determines whether a given business address can receive telecom services and what technologies are available.

This agent is **completely stateless** — it performs no database reads or writes. All lookups use an in-memory mock coverage map keyed by ZIP code.

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `serviceability_agent` (hardcoded) |
| **Model** | `os.getenv("GEMINI_MODEL")` — no default |
| **Temperature** | 0.0 (deterministic) |
| **Max Tokens** | 2048 |
| **Database** | None (stateless) |
| **Data Source** | In-memory `MOCK_COVERAGE_DATA` dict (ZIP → infrastructure) |

### Component Structure

```
ServiceabilityAgent/
├── serviceability_agent/
│   ├── __init__.py
│   ├── agent.py                    # Agent definition
│   ├── prompts.py                  # System instructions
│   ├── tools/
│   │   ├── address_tools.py        # Address parsing/validation
│   │   └── gis_tools.py            # Coverage lookup (mock GIS)
│   └── utils/
│       ├── logger.py
│       └── cache.py                # Result caching
└── tests/
```

---

## Tools (6 Functions)

### Address Tools (address_tools.py)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `validate_and_parse_address` | `(address_string) → Dict` | Parse free-text address into structured components |
| `normalize_address` | `(street, city, state, zip_code) → str` | Standardize address format |
| `extract_zip_code` | `(address_string) → str` | Extract ZIP code from any address string |

### GIS Tools (gis_tools.py)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `check_service_availability` | `(street, city, state, zip_code) → Dict` | Check if address is serviceable + available technologies |
| `get_infrastructure_by_technology` | `(technology, zone) → List[Dict]` | Get infrastructure details for a technology type |
| `get_coverage_zones` | `() → List[str]` | List all available coverage zones |

### Mock Coverage Data

The `MOCK_COVERAGE_DATA` dictionary maps ZIP codes to available infrastructure:
- **Fiber (FTTP)** — 1G/5G/10G speeds
- **Coax (HFC)** — up to 1G speeds
- **Fixed Wireless (5G)** — 100M-1G speeds

ZIPs not in the map return `"not_serviceable"`.

---

## Conversation Behavior

### When Invoked
SuperAgent routes to ServiceabilityAgent when:
- User asks "Is service available at [address]?"
- User confirms serviceability check after DiscoveryAgent registers a company
- User says "yes" after being asked about coverage

### Response Pattern
Returns infrastructure details:
> "✅ Your location at **[Address]** is serviceable! Available technologies: Fiber (FTTP) up to 10Gbps, Coax (HFC) up to 1Gbps..."

---

## Integration with SuperAgent

Loaded via **importlib isolation** in `SuperAgent/super_agent/sub_agents/serviceability/agent.py`. Agent name `serviceability_agent` is hardcoded.
