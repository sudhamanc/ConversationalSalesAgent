# ADK Bootstrap Agent Template

**Purpose:** Reference template for creating ADK-compliant agents
**Framework:** Google ADK 1.20.0
**Status:** 📋 Template (Reference Implementation)

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [Root CLAUDE.md](/CLAUDE.md)
   - [Root AGENTS.md](/AGENTS.md)
   - This file (BootStrapAgent/AGENTS.md)

2. **Common tasks → Required reading:**
   - Creating new agents → This file (see Required Files & Structure)
   - ADK standards → [Root AGENTS.md - Golden Rule](/AGENTS.md#the-golden-rule)
   - Integration → [Root AGENTS.md - Agent Integration](/AGENTS.md#agent-integration)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Overview

This directory contains the **canonical ADK Bootstrap Template** for creating standalone agents that can be:

1. Tested independently (via `adk web`)
2. Integrated into SuperAgent as sub-agents (via importlib wrappers)

**All new agents MUST follow this structure.**

---

## Directory Structure

```
BootStrapAgent/                      # Or: [YourAgent]Name/
├── pyproject.toml                   # Python package definition (REQUIRED)
├── README.md                        # Agent documentation
├── bootstrap_agent/                 # Main package (rename for your agent)
│   ├── __init__.py                  # Exports root agent
│   ├── agent.py                     # Agent instance + logic
│   ├── prompts.py                   # Instruction templates (optional but recommended)
│   ├── config.py                    # Settings (pydantic, optional)
│   ├── sub_agents/                  # If this agent has sub-agents (optional)
│   │   ├── sub_agent_1/
│   │   │   ├── __init__.py
│   │   │   └── agent.py
│   └── tools/                       # Function tools (REQUIRED if agent uses tools)
│       ├── __init__.py
│       └── tool_functions.py
├── tests/                           # Test suite (REQUIRED)
│   ├── __init__.py
│   ├── test_agent.py
│   └── test_tools.py
├── data/                            # Data files (DB, CSV, etc.) (optional)
│   └── database.db
└── .env.example                     # Environment variable template
```

---

## Required Files

### pyproject.toml

Defines Python package for `pip install -e .` installation.

**Template:**
```toml
[project]
name = "your-agent-name"
version = "0.1.0"
description = "Brief agent description"
requires-python = ">=3.12"
dependencies = [
    "google-adk>=1.20.0",
    "google-genai>=1.0.0",
    "pydantic>=2.10.0",
    "python-dotenv>=1.1.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["your_agent_package", "your_agent_package.*"]
```

### agent.py

Defines the Agent instance and exports `get_agent()` function.

**Key Elements:**
- Agent instance as module-level variable (e.g., `discovery_agent`)
- `get_agent()` function for consistent access
- Model configurable via `GEMINI_MODEL` env var
- Tools imported and wrapped with `FunctionTool`

### tools/tool_functions.py

Define deterministic functions that the agent can call.

**Best Practices:**
- Clear docstrings (LLM reads these)
- Type hints for all parameters
- Structured error handling
- Consistent return format: `{"status": "success/error", "data": {...}}`

### tests/

Pytest test suite with:
- Agent initialization tests
- Tool execution tests
- Integration tests (if applicable)

---

## Integration with SuperAgent

### Step 1: Create Wrapper

**Location:** `SuperAgent/super_agent/sub_agents/your_agent/`

**Files:**
- `__init__.py` - Exports agent
- `agent.py` - Importlib loader (see `discovery/agent.py` as reference)

### Step 2: Register in SuperAgent

**File:** `SuperAgent/super_agent/agent.py`

Add to `_build_sub_agents()` list

### Step 3: Add Routing Rule

**File:** `SuperAgent/super_agent/prompts.py`

Add routing priority and trigger examples

---

## ADK Bootstrap Checklist

Before considering an agent "complete":

**Structure:**
- [ ] `pyproject.toml` exists with correct package name
- [ ] Package directory matches `include` in `pyproject.toml`
- [ ] `agent.py` defines agent instance and `get_agent()` function
- [ ] `__init__.py` exports agent
- [ ] `tools/` directory if agent uses tools

**Code Quality:**
- [ ] Instruction is clear and specific (with examples)
- [ ] All tools have docstrings (used by LLM)
- [ ] Type hints for parameters and return values
- [ ] Error handling with structured logging
- [ ] Environment variables in `.env.example`

**Testing:**
- [ ] `tests/` directory exists
- [ ] Agent initialization test passes
- [ ] Tool execution tests pass

**Documentation:**
- [ ] README.md explains agent purpose
- [ ] AGENTS.md documents architecture, tools, integration

---

## Reference Implementations

**Study these as examples:**

1. **DiscoveryAgent** - Complex tools, intelligent slot-filling, multi-tool orchestration
2. **ServiceabilityAgent** - GIS API integration, address validation, deterministic
3. **ProductAgent** - RAG/ChromaDB, infrastructure-aware filtering

---

**Related Documentation:** [/AGENTS.md](/AGENTS.md) | [/SuperAgent/super_agent/sub_agents/AGENTS.md](/SuperAgent/super_agent/sub_agents/AGENTS.md)
