# Claude Code Instructions

**📖 READ FIRST:** [openspec/BASELINE.md](openspec/BASELINE.md): the maintained system map (every service, port, agent, tool, context key, handoff rule, knowledge corpus, command and change recipe; it describes the system as it is, never a bug list). Start every session there instead of re-discovering the codebase; then [AGENTS.md](AGENTS.md) for standards.

All system architecture, agent development patterns, and technical guidelines are documented in AGENTS.md.

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [openspec/BASELINE.md](openspec/BASELINE.md) (system map; behavioral specs in `openspec/specs/`)
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - Component-specific docs (e.g., `DiscoveryAgent/AGENTS.md`, `services/catalog/README.md`)
   - [README.md](README.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [.env.example](.env.example) (shared variables) and [SuperAgent/README.md](SuperAgent/README.md) (gateway variables)
   - Agent development → [README: Agent Service Guide](README.md#agent-service-guide) + the component's AGENTS.md
   - Orchestration / routing / handoffs → [SuperAgent/README.md](SuperAgent/README.md) + [openspec/changes/archive/2026-10-01-adk2-workflow-orchestration/design.md](openspec/changes/archive/2026-10-01-adk2-workflow-orchestration/design.md)
   - Tool services (catalog, serviceability) → `services/<name>/README.md`
   - Database schema → [db/README.md](db/README.md) (migrations and seed files, table ownership)
   - Running or deploying → [README.md](README.md#getting-started-local) (`scripts/setup_local.sh`, `scripts/db.sh up`, `scripts/start_local.sh`) and [GCP_DEPLOY.md](GCP_DEPLOY.md)
   - Any change → an OpenSpec change first (see below) + [openspec/config.yaml](openspec/config.yaml)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## 🟣 MANDATORY: OpenSpec-First Changes

**Every new change starts with an OpenSpec change, before any code, config, script or doc is edited.** This applies to features, bug fixes, script changes and doc restructures alike.

1. Create `openspec/changes/<change-name>/` with `proposal.md` (Why, What Changes, Capabilities, Non-goals, Impact), `design.md`, `specs/<capability>/spec.md` (delta: ADDED/MODIFIED/REMOVED requirements with scenarios) and `tasks.md`. Use `/opsx:propose` (or the `openspec-propose` skill); project rules are in [openspec/config.yaml](openspec/config.yaml).
2. Validate: `openspec validate <change-name>` must pass.
3. Implement against `tasks.md` (`/opsx:apply`), ticking each task only with its verification (test, command or observable behavior).
4. Update [openspec/BASELINE.md](openspec/BASELINE.md) in the same change whenever a service, port, tool, context key, handoff rule, knowledge corpus or command changes. Defects are fixed through OpenSpec changes, not recorded in the baseline (`pytest tests/test_baseline_doc.py` checks services, ports and tools).
5. Commit the OpenSpec change together with the code it describes; archive it (`openspec archive <name> -y`) once complete so `openspec/specs/` stays the source of truth.

---

## 🎯 The Golden Rule

**ALL AGENTS MUST STRICTLY FOLLOW ADK STANDARDS**

See [AGENTS.md - The Golden Rule](AGENTS.md#the-golden-rule) for complete details.

**Critical Requirements:**

1. Agent service structure (`build_agent()` + `root_agent` + `server.py`; see README "Agent Service Guide")
2. Each agent is an A2A service: see [README: Agent Service Guide](README.md#agent-service-guide). No `importlib` isolation, no `sys.modules` lookups, no imports of another agent's package
3. Deterministic tools via MCP services (`services/*`, consumed with `McpToolset`) or in-process `FunctionTool`s that return JSON dicts. No LLM calls inside tools
4. No inline styles in React (Tailwind CSS only)
5. Test before committing (per-service `pytest`, gateway tests, `tests/integration`); after prompt, model, tool or routing changes also run the golden evals (`scripts/eval.sh`, see [evals/README.md](evals/README.md))

---

## 🚨 Before Any Code Changes

0. Create and validate the OpenSpec change (`openspec/changes/<name>/`, `openspec validate <name>`)
1. Read relevant section in [AGENTS.md](AGENTS.md)
2. Check subdirectory AGENTS.md / README.md if working in a specific agent, service or the UI
3. Follow established patterns (reference implementations in AGENTS.md and the agent service guide)
4. Run tests after changes
5. Update documentation if architecture changes (and the matching `openspec/changes/*` design when relevant)

---

## 📂 Context-Specific Documentation

When working in specific directories, also read:

- **Agent Development:** [README: Agent Service Guide](README.md#agent-service-guide) and `[AgentName]/AGENTS.md` (e.g., `DiscoveryAgent/AGENTS.md`)
- **Gateway / Orchestration:** [SuperAgent/README.md](SuperAgent/README.md)
- **Tool services (REST + MCP):** [services/catalog/README.md](services/catalog/README.md), [services/serviceability/README.md](services/serviceability/README.md)
- **Shared library:** `libs/sales_common/sales_common/` (module docstrings; overview in `__init__.py`)
- **Database:** [db/README.md](db/README.md)
- **UI Development:** `SuperAgent/client/AGENTS.md`
- **System map:** [openspec/BASELINE.md](openspec/BASELINE.md)
- **Behavioral specs (source of truth):** `openspec/specs/<capability>/spec.md`; history in `openspec/changes/archive/`; open changes in `openspec/changes/` (`mcp-remaining-domains` is planned, not implemented)
- **Operations scripts:** `scripts/` (service list in `scripts/services.conf`)

---

## ✅ Quick Checks

- [ ] Read openspec/BASELINE.md before exploring code
- [ ] OpenSpec change created first and `openspec validate <name>` passes
- [ ] Read AGENTS.md relevant section
- [ ] Follow the agent service pattern (README "Agent Service Guide") (`build_agent()`, `root_agent`, `server.py` with `create_a2a_app`)
- [ ] Agent talks to other agents only through the gateway workflow (A2A), never by import
- [ ] No LLM hallucination for deterministic data (use tools; tools return JSON)
- [ ] New service registered in `scripts/services.conf` (+ `docker-compose.yml`, + gateway registry for agents)
- [ ] Tests pass
- [ ] Golden evals run for prompt/model/tool/routing changes (`scripts/eval.sh`); changed goldens re-recorded and reviewed (`python -m evals.review`)
- [ ] Documentation updated
- [ ] OpenSpec `tasks.md` ticked with verification and committed with the code
- [ ] openspec/BASELINE.md updated if anything it lists changed; `pytest tests/test_baseline_doc.py` passes

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Project Overview:** [README.md](README.md)
**Agent Service Guide:** [README: Agent Service Guide](README.md#agent-service-guide)
**Test Scenarios:** [Scenarios.md](Scenarios.md)
