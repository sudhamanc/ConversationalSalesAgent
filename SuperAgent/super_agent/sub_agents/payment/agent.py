
"""
Payment sub-agent wrapper.

Loads the payment agent from the PaymentAgent project
(located at ../../PaymentAgent relative to the SuperAgent root)
without triggering any parent agent initialization.

Why this is needed:
    Similar to other sub-agents, we use importlib to load the payment
    agent in isolation to avoid ADK parent binding conflicts. The
    PaymentAgent is loaded independently and integrated as a fresh
    Agent instance into SuperAgent's orchestration.
"""

# Logging setup for module entry
import logging
_logger = logging.getLogger("superagent.payment.agent")
if not _logger.hasHandlers():
    import sys as _sys
    _handler = logging.StreamHandler(_sys.stdout)
    _formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.info("SuperAgent Payment sub-agent module loaded.")

import importlib.util
import os
import sys
import types as pytypes

# ---------------------------------------------------------------------------
# Locate the PaymentAgent project
# ---------------------------------------------------------------------------
_PAYMENT_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "PaymentAgent")
)
_PAYMENT_PKG = os.path.join(_PAYMENT_BASE, "payment_agent")

# ---------------------------------------------------------------------------
# Stub parent package so relative imports resolve without running __init__.py
# ---------------------------------------------------------------------------
if "payment_agent" not in sys.modules:
    _stub = pytypes.ModuleType("payment_agent")
    _stub.__path__ = [_PAYMENT_PKG]
    sys.modules["payment_agent"] = _stub

# ---------------------------------------------------------------------------
# Load prompts.py (needed by agent.py)
# ---------------------------------------------------------------------------
_prompts_spec = importlib.util.spec_from_file_location(
    "payment_agent.prompts",
    os.path.join(_PAYMENT_PKG, "prompts.py"),
)
if _prompts_spec is None or _prompts_spec.loader is None:
    raise ImportError("Failed to load payment_agent.prompts module spec")
_prompts_mod = importlib.util.module_from_spec(_prompts_spec)
sys.modules[_prompts_spec.name] = _prompts_mod
_prompts_spec.loader.exec_module(_prompts_mod)

# ---------------------------------------------------------------------------
# Load utils/logger.py (needed by agent.py)
# ---------------------------------------------------------------------------
if "payment_agent.utils" not in sys.modules:
    _utils_stub = pytypes.ModuleType("payment_agent.utils")
    _utils_stub.__path__ = [os.path.join(_PAYMENT_PKG, "utils")]
    sys.modules["payment_agent.utils"] = _utils_stub

_logger_spec = importlib.util.spec_from_file_location(
    "payment_agent.utils.logger",
    os.path.join(_PAYMENT_PKG, "utils", "logger.py"),
)
if _logger_spec is None or _logger_spec.loader is None:
    raise ImportError("Failed to load payment_agent.utils.logger module spec")
_logger_mod = importlib.util.module_from_spec(_logger_spec)
sys.modules[_logger_spec.name] = _logger_mod
_logger_spec.loader.exec_module(_logger_mod)

# ---------------------------------------------------------------------------
# Load models package (needed by tools)
# ---------------------------------------------------------------------------
if "payment_agent.models" not in sys.modules:
    _models_stub = pytypes.ModuleType("payment_agent.models")
    _models_stub.__path__ = [os.path.join(_PAYMENT_PKG, "models")]
    sys.modules["payment_agent.models"] = _models_stub

# Load schemas.py if it exists
_schemas_path = os.path.join(_PAYMENT_PKG, "models", "schemas.py")
if os.path.exists(_schemas_path):
    _schemas_spec = importlib.util.spec_from_file_location(
        "payment_agent.models.schemas",
        _schemas_path,
    )
    if _schemas_spec is None or _schemas_spec.loader is None:
        raise ImportError("Failed to load payment_agent.models.schemas module spec")
    _schemas_mod = importlib.util.module_from_spec(_schemas_spec)
    sys.modules[_schemas_spec.name] = _schemas_mod
    _schemas_spec.loader.exec_module(_schemas_mod)

# ---------------------------------------------------------------------------
# Load tools package (needed by agent.py)
# ---------------------------------------------------------------------------
if "payment_agent.tools" not in sys.modules:
    _tools_stub = pytypes.ModuleType("payment_agent.tools")
    _tools_stub.__path__ = [os.path.join(_PAYMENT_PKG, "tools")]
    sys.modules["payment_agent.tools"] = _tools_stub

# Load payment_tools.py
_payment_tools_spec = importlib.util.spec_from_file_location(
    "payment_agent.tools.payment_tools",
    os.path.join(_PAYMENT_PKG, "tools", "payment_tools.py"),
)
if _payment_tools_spec is None or _payment_tools_spec.loader is None:
    raise ImportError("Failed to load payment_agent.tools.payment_tools module spec")
_payment_tools_mod = importlib.util.module_from_spec(_payment_tools_spec)
sys.modules[_payment_tools_spec.name] = _payment_tools_mod
_payment_tools_spec.loader.exec_module(_payment_tools_mod)

# Load credit_tools.py
_credit_tools_spec = importlib.util.spec_from_file_location(
    "payment_agent.tools.credit_tools",
    os.path.join(_PAYMENT_PKG, "tools", "credit_tools.py"),
)
if _credit_tools_spec is None or _credit_tools_spec.loader is None:
    raise ImportError("Failed to load payment_agent.tools.credit_tools module spec")
_credit_tools_mod = importlib.util.module_from_spec(_credit_tools_spec)
sys.modules[_credit_tools_spec.name] = _credit_tools_mod
_credit_tools_spec.loader.exec_module(_credit_tools_mod)

# Load billing_tools.py
_billing_tools_spec = importlib.util.spec_from_file_location(
    "payment_agent.tools.billing_tools",
    os.path.join(_PAYMENT_PKG, "tools", "billing_tools.py"),
)
if _billing_tools_spec is None or _billing_tools_spec.loader is None:
    raise ImportError("Failed to load payment_agent.tools.billing_tools module spec")
_billing_tools_mod = importlib.util.module_from_spec(_billing_tools_spec)
sys.modules[_billing_tools_spec.name] = _billing_tools_mod
_billing_tools_spec.loader.exec_module(_billing_tools_mod)

# ---------------------------------------------------------------------------
# Load agent.py (contains the payment_agent Agent instance)
# ---------------------------------------------------------------------------
_agent_spec = importlib.util.spec_from_file_location(
    "payment_agent.agent",
    os.path.join(_PAYMENT_PKG, "agent.py"),
)
if _agent_spec is None or _agent_spec.loader is None:
    raise ImportError("Failed to load payment_agent.agent module spec")
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

# ---------------------------------------------------------------------------
# Export the fresh, unbound Agent instance
# ---------------------------------------------------------------------------
payment_agent = _agent_mod.payment_agent

_logger.info(f"Payment agent loaded: {payment_agent.name} with {len(payment_agent.tools)} tools")
