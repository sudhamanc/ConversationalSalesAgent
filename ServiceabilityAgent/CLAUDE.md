# Claude Code Instructions - Serviceability Agent

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

All Serviceability Agent documentation (tools, GIS integration, coverage maps) is in AGENTS.md.

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - GIS/Coverage tools → [AGENTS.md - Tools](AGENTS.md#tools)
   - Mock data updates → [AGENTS.md - GIS Coverage Map](AGENTS.md#gis-coverage-map)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

When working on Serviceability Agent:

1. **Read AGENTS.md** for complete documentation
2. **Deterministic only** - Temperature = 0.0, no LLM creativity
3. **PRE-SALE agent** - Returns infrastructure, NOT products/pricing
4. **GIS data** in `tools/gis_tools.py` (update mock coverage there)
5. **24-hour cache** for address lookups
6. **Test changes** with `pytest tests/`

---

## Quick Reference

**Tools:** 6 functions (3 address, 3 GIS)
**Temperature:** 0.0 (fully deterministic)
**Invocation:** After address extraction, before product recommendations
**Data Source:** GIS/Coverage Map API (mocked in `gis_tools.py`)

---

## Critical Distinction

**ServiceabilityAgent (PRE-SALE):** "Can we serve this address?"
**ServiceFulfillmentAgent (POST-SALE):** "When can we install?"

DO NOT confuse the two.

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
**SuperAgent Integration:** [/SuperAgent/super_agent/sub_agents/serviceability/agent.py](/SuperAgent/super_agent/sub_agents/serviceability/agent.py)
