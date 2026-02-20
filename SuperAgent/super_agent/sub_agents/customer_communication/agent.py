"""
CustomerCommunicationAgent integration wrapper for SuperAgent.

CRITICAL: Uses importlib isolation to prevent parent-binding conflicts with ADK.
This module loads CustomerCommunicationAgent without executing its __init__.py,
ensuring the agent can be properly integrated into SuperAgent's hierarchy.
"""

import os
import sys
import importlib.util
import types as pytypes

# Get absolute path to CustomerCommunicationAgent project
_COMM_AGENT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "CustomerCommunicationAgent")
)
_COMM_PKG = os.path.join(_COMM_AGENT_ROOT, "customer_communication_agent")

if not os.path.exists(_COMM_PKG):
    raise FileNotFoundError(
        f"CustomerCommunicationAgent package not found at {_COMM_PKG}. "
        "Ensure CustomerCommunicationAgent/ is at workspace root."
    )

# === STEP 1: Stub parent package to prevent __init__.py execution ===
if "customer_communication_agent" not in sys.modules:
    _stub = pytypes.ModuleType("customer_communication_agent")
    _stub.__path__ = [_COMM_PKG]
    sys.modules["customer_communication_agent"] = _stub

# === STEP 2: Load dependencies in isolation ===

# Load models
_models_spec = importlib.util.spec_from_file_location(
    "customer_communication_agent.models",
    os.path.join(_COMM_PKG, "models", "__init__.py"),
)
_models_mod = importlib.util.module_from_spec(_models_spec)
sys.modules[_models_spec.name] = _models_mod
_models_spec.loader.exec_module(_models_mod)

# Load utils
_utils_logger_spec = importlib.util.spec_from_file_location(
    "customer_communication_agent.utils.logger",
    os.path.join(_COMM_PKG, "utils", "logger.py"),
)
_utils_logger_mod = importlib.util.module_from_spec(_utils_logger_spec)
sys.modules[_utils_logger_spec.name] = _utils_logger_mod
_utils_logger_spec.loader.exec_module(_utils_logger_mod)

# Load tools
_tools_spec = importlib.util.spec_from_file_location(
    "customer_communication_agent.tools",
    os.path.join(_COMM_PKG, "tools", "__init__.py"),
)
_tools_mod = importlib.util.module_from_spec(_tools_spec)
sys.modules[_tools_spec.name] = _tools_mod
_tools_spec.loader.exec_module(_tools_mod)

# Load prompts
_prompts_spec = importlib.util.spec_from_file_location(
    "customer_communication_agent.prompts",
    os.path.join(_COMM_PKG, "prompts.py"),
)
_prompts_mod = importlib.util.module_from_spec(_prompts_spec)
sys.modules[_prompts_spec.name] = _prompts_mod
_prompts_spec.loader.exec_module(_prompts_mod)

# === STEP 3: Load agent module (creates fresh Agent instance) ===
_agent_spec = importlib.util.spec_from_file_location(
    "customer_communication_agent.agent",
    os.path.join(_COMM_PKG, "agent.py"),
)
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

# Export fresh Agent instance for SuperAgent orchestration
customer_communication_agent = _agent_mod.customer_communication_agent

__all__ = ["customer_communication_agent"]
