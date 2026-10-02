# Claude Code Instructions - Payment Agent

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
   - Payment integration → [AGENTS.md - Tools](AGENTS.md#tools)
   - Security requirements → [AGENTS.md - Security](AGENTS.md#security)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

1. **Deterministic** - Temperature = 0.0
2. **Transactional** - engaged by the gateway after installation scheduling
3. **Security-critical** - PCI DSS awareness (production)
4. **A2A service** - follow [README: Agent Service Guide](../README.md#agent-service-guide); PostgreSQL via `sales_common.db`, notifications via the outbox
5. **Status:** A2A service `payment_agent` (port 8206)

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
