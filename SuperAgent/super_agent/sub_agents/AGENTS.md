# Sub-Agent Development Guidelines

**Location:** `SuperAgent/super_agent/sub_agents/`

**Parent Context:** [/AGENTS.md](/AGENTS.md) | [/CLAUDE.md](/CLAUDE.md)

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [Root CLAUDE.md](/CLAUDE.md)
   - [Root AGENTS.md](/AGENTS.md)
   - This file (sub_agents/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Inline sub-agent → This file (see Inline Sub-Agents section)
   - External sub-agent wrapper → This file (see External Sub-Agents section)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## 📋 Sub-Agent Types

### Inline Sub-Agents (Defined Here)

Located directly in `super_agent/sub_agents/[agent_name]/`:

- **GreetingAgent** (`greeting/`) - Phone script generation
- **FAQAgent** (`faq/`) - Product questions, policies

**Pattern:**
```
greeting/
├── __init__.py          # Exports greeting_agent
└── greeting_agent.py    # Agent instance + instruction
```

### External Sub-Agents (Importlib Wrappers)

Located in separate projects, wrapped here:

- **DiscoveryAgent** (`discovery/`) - Wraps `DiscoveryAgent/bootstrap_agent/`
- **ServiceabilityAgent** (`serviceability/`) - Wraps `ServiceabilityAgent/serviceability_agent/`

**Pattern:**
```
discovery/
├── __init__.py          # Exports discovery_agent
└── agent.py             # Importlib loader + package stubbing
```

---

## 🛠️ Creating an Inline Sub-Agent

### 1. Directory Structure

```bash
mkdir super_agent/sub_agents/new_agent
touch super_agent/sub_agents/new_agent/__init__.py
touch super_agent/sub_agents/new_agent/new_agent.py
```

### 2. Agent Definition (`new_agent.py`)

```python
"""
NewAgent sub-agent – handles [specific task].
"""

import os
from google.adk.agents import Agent
from google.genai import types

new_agent = Agent(
    name="new_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    instruction=(
        "You are a specialized agent that [clear task description]. "
        "\n\n**IMPORTANT GUIDELINES:**\n"
        "- [Key requirement 1]\n"
        "- [Key requirement 2]\n"
        "\nExample: [concrete example of desired behavior]\n\n"
        "Keep responses [length/tone guidance]."
    ),
    description="Handles [brief description for routing]",
    tools=[],  # Add FunctionTools if needed
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,      # Adjust: 0.3 for deterministic, 0.7 for creative
        max_output_tokens=2048,
    ),
)
```

### 3. Package Export (`__init__.py`)

```python
from .new_agent import new_agent

__all__ = ["new_agent"]
```

### 4. Register in SuperAgent

**File:** `super_agent/agent.py`

```python
from .sub_agents.new_agent import new_agent

def _build_sub_agents() -> list[Agent]:
    agents: list[Agent] = []
    if settings.agent.enable_sub_agents:
        agents.extend([
            discovery_agent,
            serviceability_agent,
            greeting_agent,
            faq_agent,
            new_agent,  # ← Add here
        ])
    return agents
```

### 5. Add Routing Rule

**File:** `super_agent/prompts.py`

```python
ORCHESTRATOR_INSTRUCTION = f"""
...

N. **New Agent Use Case**
   Transfer to **new_agent** for [when to trigger]
   Examples: "[user input example 1]", "[user input example 2]"

   Note: [Any special handling instructions]
...
"""
```

### 6. Test

```bash
cd SuperAgent/server
uvicorn main:app --reload

# In chat UI:
# Send trigger message and verify routing to new_agent
```

---

## 🔌 Creating an External Sub-Agent Wrapper

### Use Case

When sub-agent is a **separate ADK Bootstrap Template project** (like DiscoveryAgent, ServiceabilityAgent).

### 1. Directory Structure

```bash
mkdir super_agent/sub_agents/external_agent
touch super_agent/sub_agents/external_agent/__init__.py
touch super_agent/sub_agents/external_agent/agent.py
```

### 2. Importlib Wrapper (`agent.py`)

**Reference:** `discovery/agent.py` or `serviceability/agent.py`

**Key Components:**

```python
import importlib.util
import os
import sys
import types as pytypes
import logging

# 1. Logging setup
_logger = logging.getLogger("superagent.external_agent.agent")
_logger.setLevel(logging.INFO)
_logger.info("SuperAgent ExternalAgent sub-agent module loaded.")

# 2. Locate external project
_EXTERNAL_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "ExternalAgentProject")
)
_EXTERNAL_PKG = os.path.join(_EXTERNAL_BASE, "external_agent_package")

# 3. Stub parent package (prevents __init__.py execution)
if "external_agent_package" not in sys.modules:
    _stub = pytypes.ModuleType("external_agent_package")
    _stub.__path__ = [_EXTERNAL_PKG]
    sys.modules["external_agent_package"] = _stub

# 4. Load dependencies (prompts, tools, etc.) using importlib
_prompts_spec = importlib.util.spec_from_file_location(
    "external_agent_package.prompts",
    os.path.join(_EXTERNAL_PKG, "prompts.py"),
)
_prompts_mod = importlib.util.module_from_spec(_prompts_spec)
sys.modules[_prompts_spec.name] = _prompts_mod
_prompts_spec.loader.exec_module(_prompts_mod)

# 5. Load agent.py
_agent_spec = importlib.util.spec_from_file_location(
    "external_agent_package.agent",
    os.path.join(_EXTERNAL_PKG, "agent.py"),
)
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

# 6. Export fresh Agent instance
external_agent = _agent_mod.external_agent

_logger.info(f"External agent loaded: {external_agent.name} with {len(external_agent.tools)} tools")
```

### 3. Package Export (`__init__.py`)

```python
from .agent import external_agent

__all__ = ["external_agent"]
```

### 4. Register & Route

Same as inline sub-agents (steps 4-6 above).

---

## ⚙️ Sub-Agent Configuration

### Temperature Guidelines

| Agent Type | Temperature | Use Case |
|------------|-------------|----------|
| Deterministic (Serviceability, Payment) | 0.1-0.3 | Factual lookups, calculations |
| Conversational (Greeting, FAQ) | 0.6-0.8 | Natural dialogue |
| Creative (Product descriptions) | 0.8-1.0 | Marketing copy, narratives |

### Token Limits

| Response Type | max_output_tokens | Rationale |
|---------------|-------------------|-----------|
| Short answers (FAQ) | 512-1024 | Quick lookups |
| Phone scripts (Greeting) | 2048 | 2-3 sentences + product list |
| Detailed analysis (Discovery) | 4096-8192 | Full BANT scoring + insights |

### Safety Settings

**Inherited from SuperAgent:** All sub-agents use root agent's safety settings by default.

**Override (if needed):**
```python
generate_content_config=types.GenerateContentConfig(
    temperature=0.7,
    max_output_tokens=2048,
    safety_settings=[
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
    ],
)
```

---

## 🧪 Testing Sub-Agents

### Standalone Testing (ADK Web)

**Inline agents (not directly testable standalone):**
- Must test via SuperAgent routing

**External agents:**
```bash
cd DiscoveryAgent
adk web  # Launch ADK web UI for DiscoveryAgent
```

### Integration Testing (via SuperAgent)

```python
# tests/test_sub_agents.py

async def test_greeting_agent_routing():
    """Test that greeting triggers GreetingAgent"""
    response = await super_agent.process({"message": "Hi there"})
    assert "Internet" in response  # Must list all products
    assert "Ethernet" in response
    assert "TV" in response
    # ...

async def test_discovery_agent_invocation():
    """Test company identification triggers DiscoveryAgent"""
    response = await super_agent.process({
        "message": "We're VoiceStream Networks"
    })
    assert "company" in response.lower()
    # Check DB for prospect record
```

### E2E Scenario Testing

**See:** [/Scenarios.md](/Scenarios.md)

**Example:**
```bash
pytest tests/test_scenarios.py::test_scenario_1_address_lookup_new
```

---

## 📋 Sub-Agent Checklist

Before merging a new sub-agent:

- [ ] **ADK Pattern:** Agent uses `google.adk.agents.Agent`
- [ ] **Naming:** Agent name matches directory (`new_agent/new_agent.py`)
- [ ] **Instruction:** Clear, specific, with examples
- [ ] **Description:** Brief (for routing decision)
- [ ] **Tools:** All tools use `@FunctionTool` decorator
- [ ] **Temperature:** Set appropriately for task
- [ ] **Token Limit:** Set based on expected response length
- [ ] **Registration:** Added to `_build_sub_agents()` in `agent.py`
- [ ] **Routing:** Rule added to `prompts.py` with priority order
- [ ] **Logging:** Agent loading logged (for external wrappers)
- [ ] **Tests:** Integration tests added
- [ ] **Documentation:** Purpose documented in [/AGENTS.md](/AGENTS.md)

---

## 🚨 Common Issues

### Issue: Agent Not Routing

**Symptom:** SuperAgent not delegating to new sub-agent

**Debug:**
1. Check `prompts.py` routing rule is clear and has correct priority
2. Verify agent is in `_build_sub_agents()` list
3. Check SuperAgent logs for routing decision
4. Test with explicit trigger phrase from routing rule

**Fix:** Refine routing rule examples, adjust priority order

### Issue: Importlib Errors

**Symptom:** `ModuleNotFoundError` or `Agent already has parent`

**Debug:**
1. Verify package stub is created before imports
2. Check all dependencies are loaded via importlib (not regular import)
3. Ensure external project path is correct

**Fix:** Follow `discovery/agent.py` pattern exactly

### Issue: Agent Produces Wrong Output

**Symptom:** Responses don't match instruction

**Debug:**
1. Review instruction for clarity and specificity
2. Check temperature (too high = creative, too low = repetitive)
3. Add concrete examples in instruction
4. Test agent in isolation (ADK web if external)

**Fix:** Refine instruction with explicit requirements and examples

---

## 📖 Reference Implementations

**Best Examples:**

1. **Inline Agent:** `greeting/greeting_agent.py`
   - Clear instruction with product list requirement
   - Explicit examples
   - Phone script context

2. **External Wrapper:** `discovery/agent.py`
   - Complete importlib isolation
   - Logging on module entry
   - Package stubbing for dependencies

3. **Tool Integration:** `DiscoveryAgent/bootstrap_agent/sub_agents/discovery/discovery_agent.py`
   - Multiple FunctionTools
   - Database integration
   - Intelligent inference logic

---

**Parent Documentation:** [/AGENTS.md](/AGENTS.md) - Full system architecture
