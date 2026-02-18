# Claude Code Instructions - Bootstrap Template

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

All ADK Bootstrap Template documentation (structure, required files, integration steps) is in AGENTS.md.

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Creating new agents → [AGENTS.md - Required Files](AGENTS.md#required-files-and-structure)
   - ADK standards → [Root AGENTS.md - Golden Rule](/AGENTS.md#the-golden-rule)
   - Integration → [Root AGENTS.md - Agent Integration](/AGENTS.md#agent-integration)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

1. **This is a TEMPLATE** - Reference implementation, not a working agent
2. **Follow this structure** for all new agents
3. **ADK Bootstrap Pattern** - pyproject.toml, agent.py, tools/, tests/
4. **Integration via importlib** - See reference implementations

---

## Reference Implementations

Study these for real-world patterns:

- [DiscoveryAgent/AGENTS.md](/DiscoveryAgent/AGENTS.md)
- [ServiceabilityAgent/AGENTS.md](/ServiceabilityAgent/AGENTS.md)
- [ProductAgent/AGENTS.md](/ProductAgent/AGENTS.md)

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
