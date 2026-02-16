# Claude Code Instructions - Service Fulfillment Agent

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Scheduling/provisioning → [AGENTS.md - Tools](AGENTS.md#tools)
   - POST-SALE vs PRE-SALE → [AGENTS.md - Purpose](AGENTS.md#purpose)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

1. **POST-SALE agent** - Only invoked AFTER order confirmation
2. **Different from ServiceabilityAgent** - This is scheduling, not coverage
3. **Deterministic** - Temperature = 0.0
4. **6 tools** - Scheduling, provisioning, tracking
5. **Status:** ⏳ Standalone (not yet integrated)

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
**ServiceabilityAgent (PRE-SALE):** [/ServiceabilityAgent/AGENTS.md](/ServiceabilityAgent/AGENTS.md)
