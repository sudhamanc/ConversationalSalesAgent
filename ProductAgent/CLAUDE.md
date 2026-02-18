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
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - RAG/ChromaDB setup → [AGENTS.md - Tools](AGENTS.md#tools)
   - Product catalog → [AGENTS.md - Data Sources](AGENTS.md#data-sources)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

1. **RAG-powered** - All product data from ChromaDB vector database
2. **Infrastructure-aware** - Filter products by Fiber/Coax constraints
3. **Temperature = 0.1** - Low for factual accuracy
4. **11 tools** - RAG, catalog, comparison
5. **Status:** ⏳ Standalone (not yet integrated into SuperAgent)

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
