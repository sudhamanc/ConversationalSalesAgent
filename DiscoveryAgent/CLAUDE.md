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

1. **Read AGENTS.md** for complete documentation
2. **Follow ADK Bootstrap Template** structure (`bootstrap_agent/`)
3. **Database operations** use SQLite at `data/discover_prospecting_clean.db`
4. **Intelligent inference** - minimize questions by inferring industry, address, region
5. **Test changes** with `pytest tests/test_discovery_agent.py`

---

## Quick Reference

**Tools:** 8 database functions (search, add, update)
**Temperature:** 0.7 (conversational)
**Invocation:** Once per conversation when company mentioned
**Database:** SQLite - `data/discover_prospecting_clean.db`

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
**SuperAgent Integration:** [/SuperAgent/super_agent/sub_agents/discovery/agent.py](/SuperAgent/super_agent/sub_agents/discovery/agent.py)
