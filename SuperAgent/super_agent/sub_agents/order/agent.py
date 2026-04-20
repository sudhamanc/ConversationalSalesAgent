"""
Order sub-agent wrapper.

Loads the order agent's tool functions from the OrderAgent
project (located at ../../OrderAgent relative to the SuperAgent root)
without triggering any parent agent initialization.

Why this is needed:
    Similar to DiscoveryAgent and ServiceabilityAgent, we use importlib
    to load the order agent in isolation to avoid ADK parent binding conflicts.
    The OrderAgent is loaded independently and integrated as a fresh
    Agent instance into SuperAgent's orchestration.
"""

# Logging setup for module entry
import logging
_logger = logging.getLogger("superagent.order.agent")
if not _logger.hasHandlers():
    import sys as _sys
    _handler = logging.StreamHandler(_sys.stdout)
    _formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.info("SuperAgent Order sub-agent module loaded.")

import importlib.util
import os
import sys
import types as pytypes

# ---------------------------------------------------------------------------
# Locate the OrderAgent project
# ---------------------------------------------------------------------------
_ORDER_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "OrderAgent")
)
_ORDER_PKG = os.path.join(_ORDER_BASE, "order_agent")

# ---------------------------------------------------------------------------
# Stub parent package so relative imports resolve without running __init__.py
# ---------------------------------------------------------------------------
if "order_agent" not in sys.modules:
    _stub = pytypes.ModuleType("order_agent")
    _stub.__path__ = [_ORDER_PKG]
    sys.modules["order_agent"] = _stub

# ---------------------------------------------------------------------------
# Load models package (needed by tools)
# ---------------------------------------------------------------------------
if "order_agent.models" not in sys.modules:
    _models_stub = pytypes.ModuleType("order_agent.models")
    _models_stub.__path__ = [os.path.join(_ORDER_PKG, "models")]
    sys.modules["order_agent.models"] = _models_stub

_models_init_spec = importlib.util.spec_from_file_location(
    "order_agent.models",
    os.path.join(_ORDER_PKG, "models", "__init__.py"),
)
if _models_init_spec is None or _models_init_spec.loader is None:
    raise ImportError("Failed to load order_agent.models module spec")
_models_init_mod = importlib.util.module_from_spec(_models_init_spec)
sys.modules[_models_init_spec.name] = _models_init_mod
_models_init_spec.loader.exec_module(_models_init_mod)

# ---------------------------------------------------------------------------
# Load utils/logger.py (needed by agent.py and tools)
# ---------------------------------------------------------------------------
if "order_agent.utils" not in sys.modules:
    _utils_stub = pytypes.ModuleType("order_agent.utils")
    _utils_stub.__path__ = [os.path.join(_ORDER_PKG, "utils")]
    sys.modules["order_agent.utils"] = _utils_stub

_logger_spec = importlib.util.spec_from_file_location(
    "order_agent.utils.logger",
    os.path.join(_ORDER_PKG, "utils", "logger.py"),
)
if _logger_spec is None or _logger_spec.loader is None:
    raise ImportError("Failed to load order_agent.utils.logger module spec")
_logger_mod = importlib.util.module_from_spec(_logger_spec)
sys.modules[_logger_spec.name] = _logger_mod
_logger_spec.loader.exec_module(_logger_mod)

# ---------------------------------------------------------------------------
# Load prompts.py (needed by agent.py)
# ---------------------------------------------------------------------------
_prompts_spec = importlib.util.spec_from_file_location(
    "order_agent.prompts",
    os.path.join(_ORDER_PKG, "prompts.py"),
)
if _prompts_spec is None or _prompts_spec.loader is None:
    raise ImportError("Failed to load order_agent.prompts module spec")
_prompts_mod = importlib.util.module_from_spec(_prompts_spec)
sys.modules[_prompts_spec.name] = _prompts_mod
_prompts_spec.loader.exec_module(_prompts_mod)

# ---------------------------------------------------------------------------
# Load tools package (needed by agent.py)
# ---------------------------------------------------------------------------
if "order_agent.tools" not in sys.modules:
    _tools_stub = pytypes.ModuleType("order_agent.tools")
    _tools_stub.__path__ = [os.path.join(_ORDER_PKG, "tools")]
    sys.modules["order_agent.tools"] = _tools_stub

# Load cart_tools.py
_cart_tools_spec = importlib.util.spec_from_file_location(
    "order_agent.tools.cart_tools",
    os.path.join(_ORDER_PKG, "tools", "cart_tools.py"),
)
if _cart_tools_spec is None or _cart_tools_spec.loader is None:
    raise ImportError("Failed to load order_agent.tools.cart_tools module spec")
_cart_tools_mod = importlib.util.module_from_spec(_cart_tools_spec)
sys.modules[_cart_tools_spec.name] = _cart_tools_mod
_cart_tools_spec.loader.exec_module(_cart_tools_mod)

# Load order_tools.py
_order_tools_spec = importlib.util.spec_from_file_location(
    "order_agent.tools.order_tools",
    os.path.join(_ORDER_PKG, "tools", "order_tools.py"),
)
if _order_tools_spec is None or _order_tools_spec.loader is None:
    raise ImportError("Failed to load order_agent.tools.order_tools module spec")
_order_tools_mod = importlib.util.module_from_spec(_order_tools_spec)
sys.modules[_order_tools_spec.name] = _order_tools_mod
_order_tools_spec.loader.exec_module(_order_tools_mod)

# ---------------------------------------------------------------------------
# Load the main agent module - this must come last after all dependencies
# ---------------------------------------------------------------------------
_agent_spec = importlib.util.spec_from_file_location(
    "order_agent.agent",
    os.path.join(_ORDER_PKG, "agent.py"),
)
if _agent_spec is None or _agent_spec.loader is None:
    raise ImportError("Failed to load order_agent.agent module spec")
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

# ---------------------------------------------------------------------------
# Export the fresh Agent instance
# ---------------------------------------------------------------------------
order_agent = _agent_mod.order_agent

_logger.info(f"Order sub-agent loaded: {order_agent.name} with {len(order_agent.tools)} tools")
