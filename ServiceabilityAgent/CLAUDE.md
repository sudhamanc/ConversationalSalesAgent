# Claude Code Instructions - Serviceability Agent

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

All Serviceability Agent documentation is in AGENTS.md. Tools and coverage data live in the serviceability service: [services/serviceability/README.md](/services/serviceability/README.md).

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Tool contracts → [AGENTS.md](AGENTS.md) and [services/serviceability/README.md](/services/serviceability/README.md)
   - Coverage data updates → `coverage_zones` table (`db/seed/003_coverage.sql`)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

When working on Serviceability Agent:

1. **Read AGENTS.md** for complete documentation
2. **Deterministic only** - Temperature = 0.0, no LLM creativity
3. **PRE-SALE agent** - Returns infrastructure, NOT products/pricing
4. **No local tools** - tools come from the serviceability MCP server (`SERVICEABILITY_MCP_URL`)
5. **Keep the UI-parsed output format** in `prompts.py`
6. **Test changes** with `pytest ServiceabilityAgent/tests services/serviceability/tests`

---

## Quick Reference

**Tools:** 6 MCP tools (3 address, 3 coverage) from services/serviceability
**Temperature:** 0.0 (fully deterministic)
**Invocation:** After address extraction, before product recommendations
**Data Source:** PostgreSQL `coverage_zones` via the serviceability service (or upstream GIS API)

---

## Critical Distinction

**ServiceabilityAgent (PRE-SALE):** "Can we serve this address?"
**ServiceFulfillmentAgent (POST-SALE):** "When can we install?"

DO NOT confuse the two.

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
**Service guide:** [/docs/agent-service-guide.md](/docs/agent-service-guide.md)
