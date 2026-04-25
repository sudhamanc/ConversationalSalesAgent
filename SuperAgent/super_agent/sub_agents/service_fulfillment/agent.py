
"""
Service Fulfillment sub-agent wrapper.

Loads the service fulfillment agent from the ServiceFulfillmentAgent project
(located at ../../ServiceFulfillmentAgent relative to the SuperAgent root)
without triggering any parent agent initialization.

Why this is needed:
    Similar to other sub-agents, we use importlib to load the service
    fulfillment agent in isolation to avoid ADK parent binding conflicts.
    The ServiceFulfillmentAgent is loaded independently and integrated as a
    fresh Agent instance into SuperAgent's orchestration.
"""

# Logging setup for module entry
import logging
_logger = logging.getLogger("superagent.service_fulfillment.agent")
if not _logger.hasHandlers():
    import sys as _sys
    _handler = logging.StreamHandler(_sys.stdout)
    _formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.info("SuperAgent Service Fulfillment sub-agent module loaded.")

import importlib.util
import os
import sys
import types as pytypes

# ---------------------------------------------------------------------------
# Locate the ServiceFulfillmentAgent project
# ---------------------------------------------------------------------------
_SERVICE_FULFILLMENT_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "ServiceFulfillmentAgent")
)
_SERVICE_FULFILLMENT_PKG = os.path.join(_SERVICE_FULFILLMENT_BASE, "service_fulfillment_agent")

# ---------------------------------------------------------------------------
# Stub parent package so relative imports resolve without running __init__.py
# ---------------------------------------------------------------------------
if "service_fulfillment_agent" not in sys.modules:
    _stub = pytypes.ModuleType("service_fulfillment_agent")
    _stub.__path__ = [_SERVICE_FULFILLMENT_PKG]
    sys.modules["service_fulfillment_agent"] = _stub

# ---------------------------------------------------------------------------
# Load prompts.py (needed by agent.py)
# ---------------------------------------------------------------------------
_prompts_spec = importlib.util.spec_from_file_location(
    "service_fulfillment_agent.prompts",
    os.path.join(_SERVICE_FULFILLMENT_PKG, "prompts.py"),
)
if _prompts_spec is None or _prompts_spec.loader is None:
    raise ImportError("Failed to load service_fulfillment_agent.prompts module spec")
_prompts_mod = importlib.util.module_from_spec(_prompts_spec)
sys.modules[_prompts_spec.name] = _prompts_mod
_prompts_spec.loader.exec_module(_prompts_mod)

# ---------------------------------------------------------------------------
# Load utils/logger.py (needed by agent.py)
# ---------------------------------------------------------------------------
if "service_fulfillment_agent.utils" not in sys.modules:
    _utils_stub = pytypes.ModuleType("service_fulfillment_agent.utils")
    _utils_stub.__path__ = [os.path.join(_SERVICE_FULFILLMENT_PKG, "utils")]
    sys.modules["service_fulfillment_agent.utils"] = _utils_stub

_logger_spec = importlib.util.spec_from_file_location(
    "service_fulfillment_agent.utils.logger",
    os.path.join(_SERVICE_FULFILLMENT_PKG, "utils", "logger.py"),
)
if _logger_spec is None or _logger_spec.loader is None:
    raise ImportError("Failed to load service_fulfillment_agent.utils.logger module spec")
_logger_mod = importlib.util.module_from_spec(_logger_spec)
sys.modules[_logger_spec.name] = _logger_mod
_logger_spec.loader.exec_module(_logger_mod)

# ---------------------------------------------------------------------------
# Load models package (needed by tools)
# ---------------------------------------------------------------------------
if "service_fulfillment_agent.models" not in sys.modules:
    _models_stub = pytypes.ModuleType("service_fulfillment_agent.models")
    _models_stub.__path__ = [os.path.join(_SERVICE_FULFILLMENT_PKG, "models")]
    sys.modules["service_fulfillment_agent.models"] = _models_stub

# Load schemas.py if it exists
_schemas_path = os.path.join(_SERVICE_FULFILLMENT_PKG, "models", "schemas.py")
if os.path.exists(_schemas_path):
    _schemas_spec = importlib.util.spec_from_file_location(
        "service_fulfillment_agent.models.schemas",
        _schemas_path,
    )
    if _schemas_spec is None or _schemas_spec.loader is None:
        raise ImportError("Failed to load service_fulfillment_agent.models.schemas module spec")
    _schemas_mod = importlib.util.module_from_spec(_schemas_spec)
    sys.modules[_schemas_spec.name] = _schemas_mod
    _schemas_spec.loader.exec_module(_schemas_mod)

# ---------------------------------------------------------------------------
# Load tools package (needed by agent.py)
# ---------------------------------------------------------------------------
if "service_fulfillment_agent.tools" not in sys.modules:
    _tools_stub = pytypes.ModuleType("service_fulfillment_agent.tools")
    _tools_stub.__path__ = [os.path.join(_SERVICE_FULFILLMENT_PKG, "tools")]
    sys.modules["service_fulfillment_agent.tools"] = _tools_stub

# Load scheduling_tools.py
_scheduling_tools_spec = importlib.util.spec_from_file_location(
    "service_fulfillment_agent.tools.scheduling_tools",
    os.path.join(_SERVICE_FULFILLMENT_PKG, "tools", "scheduling_tools.py"),
)
if _scheduling_tools_spec is None or _scheduling_tools_spec.loader is None:
    raise ImportError("Failed to load service_fulfillment_agent.tools.scheduling_tools module spec")
_scheduling_tools_mod = importlib.util.module_from_spec(_scheduling_tools_spec)
sys.modules[_scheduling_tools_spec.name] = _scheduling_tools_mod
_scheduling_tools_spec.loader.exec_module(_scheduling_tools_mod)

# Load equipment_tools.py
_equipment_tools_spec = importlib.util.spec_from_file_location(
    "service_fulfillment_agent.tools.equipment_tools",
    os.path.join(_SERVICE_FULFILLMENT_PKG, "tools", "equipment_tools.py"),
)
if _equipment_tools_spec is None or _equipment_tools_spec.loader is None:
    raise ImportError("Failed to load service_fulfillment_agent.tools.equipment_tools module spec")
_equipment_tools_mod = importlib.util.module_from_spec(_equipment_tools_spec)
sys.modules[_equipment_tools_spec.name] = _equipment_tools_mod
_equipment_tools_spec.loader.exec_module(_equipment_tools_mod)

# Load installation_tools.py
_installation_tools_spec = importlib.util.spec_from_file_location(
    "service_fulfillment_agent.tools.installation_tools",
    os.path.join(_SERVICE_FULFILLMENT_PKG, "tools", "installation_tools.py"),
)
if _installation_tools_spec is None or _installation_tools_spec.loader is None:
    raise ImportError("Failed to load service_fulfillment_agent.tools.installation_tools module spec")
_installation_tools_mod = importlib.util.module_from_spec(_installation_tools_spec)
sys.modules[_installation_tools_spec.name] = _installation_tools_mod
_installation_tools_spec.loader.exec_module(_installation_tools_mod)

# Load activation_tools.py
_activation_tools_spec = importlib.util.spec_from_file_location(
    "service_fulfillment_agent.tools.activation_tools",
    os.path.join(_SERVICE_FULFILLMENT_PKG, "tools", "activation_tools.py"),
)
if _activation_tools_spec is None or _activation_tools_spec.loader is None:
    raise ImportError("Failed to load service_fulfillment_agent.tools.activation_tools module spec")
_activation_tools_mod = importlib.util.module_from_spec(_activation_tools_spec)
sys.modules[_activation_tools_spec.name] = _activation_tools_mod
_activation_tools_spec.loader.exec_module(_activation_tools_mod)

# Load order_tools.py
_order_tools_spec = importlib.util.spec_from_file_location(
    "service_fulfillment_agent.tools.order_tools",
    os.path.join(_SERVICE_FULFILLMENT_PKG, "tools", "order_tools.py"),
)
if _order_tools_spec is None or _order_tools_spec.loader is None:
    raise ImportError("Failed to load service_fulfillment_agent.tools.order_tools module spec")
_order_tools_mod = importlib.util.module_from_spec(_order_tools_spec)
sys.modules[_order_tools_spec.name] = _order_tools_mod
_order_tools_spec.loader.exec_module(_order_tools_mod)

# ---------------------------------------------------------------------------
# Load agent.py (contains the service_fulfillment_agent Agent instance)
# ---------------------------------------------------------------------------
_agent_spec = importlib.util.spec_from_file_location(
    "service_fulfillment_agent.agent",
    os.path.join(_SERVICE_FULFILLMENT_PKG, "agent.py"),
)
if _agent_spec is None or _agent_spec.loader is None:
    raise ImportError("Failed to load service_fulfillment_agent.agent module spec")
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

# ---------------------------------------------------------------------------
# Export the fresh, unbound Agent instance
# ---------------------------------------------------------------------------
service_fulfillment_agent = _agent_mod.service_fulfillment_agent

_logger.info(f"Service Fulfillment agent loaded: {service_fulfillment_agent.name} with {len(service_fulfillment_agent.tools)} tools")
