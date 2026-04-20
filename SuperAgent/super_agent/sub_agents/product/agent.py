
"""
Product sub-agent wrapper.

Loads the product agent from the ProductAgent project
(located at ../../ProductAgent relative to the SuperAgent root)
without triggering any parent agent initialization.

Why this is needed:
    We use importlib to load the product agent in isolation to avoid ADK
    parent binding conflicts. The ProductAgent is loaded independently and
    integrated as a fresh Agent instance into SuperAgent's orchestration.
"""

# Logging setup for module entry
import logging
_logger = logging.getLogger("superagent.product.agent")
if not _logger.hasHandlers():
    import sys as _sys
    _handler = logging.StreamHandler(_sys.stdout)
    _formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.info("SuperAgent Product sub-agent module loaded.")

import importlib.util
import os
import sys
import types as pytypes

# ---------------------------------------------------------------------------
# Locate the ProductAgent project
# ---------------------------------------------------------------------------
_PRODUCT_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "ProductAgent")
)
_PRODUCT_PKG = os.path.join(_PRODUCT_BASE, "product_agent")

# ---------------------------------------------------------------------------
# Stub parent package so relative imports resolve without running __init__.py
# ---------------------------------------------------------------------------
if "product_agent" not in sys.modules:
    _stub = pytypes.ModuleType("product_agent")
    _stub.__path__ = [_PRODUCT_PKG]
    sys.modules["product_agent"] = _stub

# ---------------------------------------------------------------------------
# Load prompts.py (needed by agent.py)
# ---------------------------------------------------------------------------
_prompts_spec = importlib.util.spec_from_file_location(
    "product_agent.prompts",
    os.path.join(_PRODUCT_PKG, "prompts.py"),
)
if _prompts_spec is None or _prompts_spec.loader is None:
    raise ImportError("Failed to load product_agent.prompts module spec")
_prompts_mod = importlib.util.module_from_spec(_prompts_spec)
sys.modules[_prompts_spec.name] = _prompts_mod
_prompts_spec.loader.exec_module(_prompts_mod)

# ---------------------------------------------------------------------------
# Load utils package (needed by agent.py)
# ---------------------------------------------------------------------------
if "product_agent.utils" not in sys.modules:
    _utils_stub = pytypes.ModuleType("product_agent.utils")
    _utils_stub.__path__ = [os.path.join(_PRODUCT_PKG, "utils")]
    sys.modules["product_agent.utils"] = _utils_stub

# Load logger.py
_logger_spec = importlib.util.spec_from_file_location(
    "product_agent.utils.logger",
    os.path.join(_PRODUCT_PKG, "utils", "logger.py"),
)
if _logger_spec is None or _logger_spec.loader is None:
    raise ImportError("Failed to load product_agent.utils.logger module spec")
_logger_mod = importlib.util.module_from_spec(_logger_spec)
sys.modules[_logger_spec.name] = _logger_mod
_logger_spec.loader.exec_module(_logger_mod)

# Load cache.py (may be needed by tools)
_cache_spec = importlib.util.spec_from_file_location(
    "product_agent.utils.cache",
    os.path.join(_PRODUCT_PKG, "utils", "cache.py"),
)
if _cache_spec is None or _cache_spec.loader is None:
    raise ImportError("Failed to load product_agent.utils.cache module spec")
_cache_mod = importlib.util.module_from_spec(_cache_spec)
sys.modules[_cache_spec.name] = _cache_mod
_cache_spec.loader.exec_module(_cache_mod)

# ---------------------------------------------------------------------------
# Load models package (needed by tools)
# ---------------------------------------------------------------------------
if "product_agent.models" not in sys.modules:
    _models_stub = pytypes.ModuleType("product_agent.models")
    _models_stub.__path__ = [os.path.join(_PRODUCT_PKG, "models")]
    sys.modules["product_agent.models"] = _models_stub

# Load schemas.py
_schemas_spec = importlib.util.spec_from_file_location(
    "product_agent.models.schemas",
    os.path.join(_PRODUCT_PKG, "models", "schemas.py"),
)
if _schemas_spec is None or _schemas_spec.loader is None:
    raise ImportError("Failed to load product_agent.models.schemas module spec")
_schemas_mod = importlib.util.module_from_spec(_schemas_spec)
sys.modules[_schemas_spec.name] = _schemas_mod
_schemas_spec.loader.exec_module(_schemas_mod)

# ---------------------------------------------------------------------------
# Load tools package (needed by agent.py)
# ---------------------------------------------------------------------------
if "product_agent.tools" not in sys.modules:
    _tools_stub = pytypes.ModuleType("product_agent.tools")
    _tools_stub.__path__ = [os.path.join(_PRODUCT_PKG, "tools")]
    sys.modules["product_agent.tools"] = _tools_stub

# Load product_tools.py
_product_tools_spec = importlib.util.spec_from_file_location(
    "product_agent.tools.product_tools",
    os.path.join(_PRODUCT_PKG, "tools", "product_tools.py"),
)
if _product_tools_spec is None or _product_tools_spec.loader is None:
    raise ImportError("Failed to load product_agent.tools.product_tools module spec")
_product_tools_mod = importlib.util.module_from_spec(_product_tools_spec)
sys.modules[_product_tools_spec.name] = _product_tools_mod
_product_tools_spec.loader.exec_module(_product_tools_mod)

# Load comparison_tools.py
_comparison_tools_spec = importlib.util.spec_from_file_location(
    "product_agent.tools.comparison_tools",
    os.path.join(_PRODUCT_PKG, "tools", "comparison_tools.py"),
)
if _comparison_tools_spec is None or _comparison_tools_spec.loader is None:
    raise ImportError("Failed to load product_agent.tools.comparison_tools module spec")
_comparison_tools_mod = importlib.util.module_from_spec(_comparison_tools_spec)
sys.modules[_comparison_tools_spec.name] = _comparison_tools_mod
_comparison_tools_spec.loader.exec_module(_comparison_tools_mod)

# ---------------------------------------------------------------------------
# Load agent.py (contains the product_agent Agent instance)
# ---------------------------------------------------------------------------
_agent_spec = importlib.util.spec_from_file_location(
    "product_agent.agent",
    os.path.join(_PRODUCT_PKG, "agent.py"),
)
if _agent_spec is None or _agent_spec.loader is None:
    raise ImportError("Failed to load product_agent.agent module spec")
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

# ---------------------------------------------------------------------------
# Export the fresh, unbound Agent instance
# ---------------------------------------------------------------------------
product_agent = _agent_mod.product_agent

_logger.info(f"Product agent loaded: {product_agent.name} with {len(product_agent.tools)} tools")
