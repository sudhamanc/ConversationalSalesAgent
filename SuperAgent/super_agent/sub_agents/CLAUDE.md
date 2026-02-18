# Claude Code Instructions - Sub-Agent Development

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

All sub-agent development patterns (inline vs external, importlib wrappers, registration) are in AGENTS.md.

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Inline sub-agent → [AGENTS.md - Inline Sub-Agents](AGENTS.md#inline-sub-agents)
   - External wrapper → [AGENTS.md - External Sub-Agents](AGENTS.md#external-sub-agents)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

1. **Read AGENTS.md** for complete sub-agent development guide
2. **Inline sub-agents** - greeting/, faq/ (simple, defined here)
3. **External sub-agents** - discovery/, serviceability/ (importlib wrappers)
4. **Importlib isolation** - Mandatory for external agents (see discovery/agent.py)
5. **Registration** - Add to `../agent.py` _build_sub_agents()
6. **Routing** - Add rule to `../prompts.py`

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
**Bootstrap Template:** [/BootStrapAgent/AGENTS.md](/BootStrapAgent/AGENTS.md)
