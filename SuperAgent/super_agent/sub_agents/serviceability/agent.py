
"""
Serviceability sub-agent wrapper.

Loads the serviceability agent's tool functions from the ServiceabilityAgent
project (located at ../../ServiceabilityAgent relative to the SuperAgent root)
without triggering any parent agent initialization.

Why this is needed:
    Similar to DiscoveryAgent, we use importlib to load the serviceability
    agent in isolation to avoid ADK parent binding conflicts. The
    ServiceabilityAgent is loaded independently and integrated as a fresh
    Agent instance into SuperAgent's orchestration.
"""

# Logging setup for module entry
import logging
_logger = logging.getLogger("superagent.serviceability.agent")
if not _logger.hasHandlers():
    import sys as _sys
    _handler = logging.StreamHandler(_sys.stdout)
    _formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.info("SuperAgent Serviceability sub-agent module loaded.")

import importlib.util
import os
import sys
import types as pytypes

# ---------------------------------------------------------------------------
# Locate the ServiceabilityAgent project
# ---------------------------------------------------------------------------
_SERVICEABILITY_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "ServiceabilityAgent")
)
_SERVICEABILITY_PKG = os.path.join(_SERVICEABILITY_BASE, "serviceability_agent")

# ---------------------------------------------------------------------------
# Stub parent package so relative imports resolve without running __init__.py
# ---------------------------------------------------------------------------
if "serviceability_agent" not in sys.modules:
    _stub = pytypes.ModuleType("serviceability_agent")
    _stub.__path__ = [_SERVICEABILITY_PKG]
    sys.modules["serviceability_agent"] = _stub

# ---------------------------------------------------------------------------
# Load prompts.py (needed by agent.py)
# ---------------------------------------------------------------------------
_prompts_spec = importlib.util.spec_from_file_location(
    "serviceability_agent.prompts",
    os.path.join(_SERVICEABILITY_PKG, "prompts.py"),
)
if _prompts_spec is None or _prompts_spec.loader is None:
    raise ImportError("Failed to load serviceability_agent.prompts module spec")
_prompts_mod = importlib.util.module_from_spec(_prompts_spec)
sys.modules[_prompts_spec.name] = _prompts_mod
_prompts_spec.loader.exec_module(_prompts_mod)

# ---------------------------------------------------------------------------
# Load utils/logger.py (needed by agent.py)
# ---------------------------------------------------------------------------
if "serviceability_agent.utils" not in sys.modules:
    _utils_stub = pytypes.ModuleType("serviceability_agent.utils")
    _utils_stub.__path__ = [os.path.join(_SERVICEABILITY_PKG, "utils")]
    sys.modules["serviceability_agent.utils"] = _utils_stub

_logger_spec = importlib.util.spec_from_file_location(
    "serviceability_agent.utils.logger",
    os.path.join(_SERVICEABILITY_PKG, "utils", "logger.py"),
)
if _logger_spec is None or _logger_spec.loader is None:
    raise ImportError("Failed to load serviceability_agent.utils.logger module spec")
_logger_mod = importlib.util.module_from_spec(_logger_spec)
sys.modules[_logger_spec.name] = _logger_mod
_logger_spec.loader.exec_module(_logger_mod)

# ---------------------------------------------------------------------------
# Load tools package (needed by agent.py)
# ---------------------------------------------------------------------------
if "serviceability_agent.tools" not in sys.modules:
    _tools_stub = pytypes.ModuleType("serviceability_agent.tools")
    _tools_stub.__path__ = [os.path.join(_SERVICEABILITY_PKG, "tools")]
    sys.modules["serviceability_agent.tools"] = _tools_stub

# Load address_tools.py
_address_tools_spec = importlib.util.spec_from_file_location(
    "serviceability_agent.tools.address_tools",
    os.path.join(_SERVICEABILITY_PKG, "tools", "address_tools.py"),
)
if _address_tools_spec is None or _address_tools_spec.loader is None:
    raise ImportError("Failed to load serviceability_agent.tools.address_tools module spec")
_address_tools_mod = importlib.util.module_from_spec(_address_tools_spec)
sys.modules[_address_tools_spec.name] = _address_tools_mod
_address_tools_spec.loader.exec_module(_address_tools_mod)

# Load gis_tools.py
_gis_tools_spec = importlib.util.spec_from_file_location(
    "serviceability_agent.tools.gis_tools",
    os.path.join(_SERVICEABILITY_PKG, "tools", "gis_tools.py"),
)
if _gis_tools_spec is None or _gis_tools_spec.loader is None:
    raise ImportError("Failed to load serviceability_agent.tools.gis_tools module spec")
_gis_tools_mod = importlib.util.module_from_spec(_gis_tools_spec)
sys.modules[_gis_tools_spec.name] = _gis_tools_mod
_gis_tools_spec.loader.exec_module(_gis_tools_mod)

# ---------------------------------------------------------------------------
# Load agent.py (contains the serviceability_agent Agent instance)
# ---------------------------------------------------------------------------
_agent_spec = importlib.util.spec_from_file_location(
    "serviceability_agent.agent",
    os.path.join(_SERVICEABILITY_PKG, "agent.py"),
)
if _agent_spec is None or _agent_spec.loader is None:
    raise ImportError("Failed to load serviceability_agent.agent module spec")
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

# ---------------------------------------------------------------------------
# Export the fresh, unbound Agent instance
# ---------------------------------------------------------------------------
serviceability_agent = _agent_mod.serviceability_agent

_logger.info(f"Serviceability agent loaded: {serviceability_agent.name} with {len(serviceability_agent.tools)} tools")
