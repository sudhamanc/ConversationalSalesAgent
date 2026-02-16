# Claude Code Instructions

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

All system architecture, agent development patterns, and technical guidelines are documented in AGENTS.md.

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - Component-specific docs (e.g., `DiscoveryAgent/AGENTS.md`)
   - [README.md](README.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](SuperAgent/README.md) (`.env` variables)
   - Agent development → Component's AGENTS.md
   - Sub-agent work → [super_agent/sub_agents/CLAUDE.md](SuperAgent/super_agent/sub_agents/CLAUDE.md)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## 🎯 The Golden Rule

**ALL AGENTS MUST STRICTLY FOLLOW ADK STANDARDS**

See [AGENTS.md - The Golden Rule](AGENTS.md#the-golden-rule) for complete details.

**Critical Requirements:**
1. ADK Bootstrap Template structure
2. Importlib isolation for external sub-agents
3. Tools use `@FunctionTool` decorator
4. No inline styles in React (Tailwind CSS only)
5. Test before committing

---

## 🚨 Before Any Code Changes

1. Read relevant section in [AGENTS.md](AGENTS.md)
2. Check subdirectory AGENTS.md if working in specific agent/component
3. Follow established patterns (reference implementations in AGENTS.md)
4. Run tests after changes
5. Update documentation if architecture changes

---

## 📂 Context-Specific Documentation

When working in specific directories, also read:

- **Agent Development:** `[AgentName]/AGENTS.md` (e.g., `DiscoveryAgent/AGENTS.md`)
- **Sub-agent Development:** `SuperAgent/super_agent/sub_agents/AGENTS.md`
- **UI Development:** `SuperAgent/client/AGENTS.md`
- **Bootstrap Template:** `BootStrapAgent/AGENTS.md`

---

## ✅ Quick Checks

- [ ] Read AGENTS.md relevant section
- [ ] Follow ADK Bootstrap Template pattern
- [ ] Use importlib for external agents
- [ ] No LLM hallucination for deterministic data (use tools)
- [ ] Tests pass
- [ ] Documentation updated

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Project Overview:** [README.md](README.md)
**Test Scenarios:** [Scenarios.md](Scenarios.md)
