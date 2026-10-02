# Claude Code Instructions - Product Agent

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [AGENTS.md - Environment](AGENTS.md#environment)
   - Product tool / catalog changes → [services/catalog/README.md](/services/catalog/README.md)
   - Agent wiring → [AGENTS.md](AGENTS.md)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

1. **Catalog via MCP** - All product data comes from the catalog service (`services/catalog`) through `McpToolset` (`CATALOG_MCP_URL`); no local tools or data
2. **Infrastructure-aware** - Filter products by Fiber/Coax constraints
3. **Temperature = 0.0** - Deterministic for factual accuracy
4. **8 MCP tools** - Catalog, comparison and knowledge search (names unchanged)
5. **Build pattern:** [README: Agent Service Guide](../README.md#agent-service-guide) (A2A service, `server.py`)

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
