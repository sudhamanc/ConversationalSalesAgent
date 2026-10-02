# Claude Code Instructions - Discovery Agent

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

All Discovery Agent documentation (tools, database schema, intelligent inference) is in AGENTS.md.

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Database schema → [AGENTS.md - Database Schema](AGENTS.md#database-schema)
   - Tool modifications → [AGENTS.md - Tools](AGENTS.md#tools)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

When working on Discovery Agent:

1. **Read AGENTS.md** and [README: Agent Service Guide](../README.md#agent-service-guide)
2. **Package:** `discovery_agent/` (agent.py, prompts.py, tools/, server.py)
3. **Database:** PostgreSQL via `sales_common.db` (quoted columns such as `"Company Name"`)
4. **Intelligent inference** - minimize questions by inferring industry, address, region
5. **Test changes** with `TEST_DATABASE_URL=... pytest DiscoveryAgent/tests -q`

---

## Quick Reference

**Tools:** 13 deterministic database functions (search, add, update, BANT, customer state)
**Temperature:** 0.0
**Hand-off:** none in the agent; the gateway runs Discovery -> Serviceability
**Serving:** A2A service `discovery_agent.server:app`

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
**Service guide:** [README: Agent Service Guide](../README.md#agent-service-guide)
