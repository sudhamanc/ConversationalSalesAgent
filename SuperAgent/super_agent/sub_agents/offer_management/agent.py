"""
OfferManagement sub-agent wrapper.

Loads the OfferManagement agent project in isolation to avoid ADK parent binding conflicts.
"""

import importlib.util
import logging
import os
import sys
import types as pytypes

_logger = logging.getLogger("superagent.offer_management.agent")
if not _logger.hasHandlers():
    import sys as _sys

    _handler = logging.StreamHandler(_sys.stdout)
    _formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] %(message)s")
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
_logger.setLevel(logging.INFO)

_OFFER_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "OfferManagement")
)
_OFFER_PKG = os.path.join(_OFFER_BASE, "offer_management")

if "offer_management" not in sys.modules:
    _stub = pytypes.ModuleType("offer_management")
    _stub.__path__ = [_OFFER_PKG]
    sys.modules["offer_management"] = _stub

_prompts_spec = importlib.util.spec_from_file_location(
    "offer_management.prompts",
    os.path.join(_OFFER_PKG, "prompts.py"),
)
_prompts_mod = importlib.util.module_from_spec(_prompts_spec)
sys.modules[_prompts_spec.name] = _prompts_mod
_prompts_spec.loader.exec_module(_prompts_mod)

if "offer_management.utils" not in sys.modules:
    _utils_stub = pytypes.ModuleType("offer_management.utils")
    _utils_stub.__path__ = [os.path.join(_OFFER_PKG, "utils")]
    sys.modules["offer_management.utils"] = _utils_stub

_logger_spec = importlib.util.spec_from_file_location(
    "offer_management.utils.logger",
    os.path.join(_OFFER_PKG, "utils", "logger.py"),
)
_logger_mod = importlib.util.module_from_spec(_logger_spec)
sys.modules[_logger_spec.name] = _logger_mod
_logger_spec.loader.exec_module(_logger_mod)

_cache_spec = importlib.util.spec_from_file_location(
    "offer_management.utils.cache",
    os.path.join(_OFFER_PKG, "utils", "cache.py"),
)
_cache_mod = importlib.util.module_from_spec(_cache_spec)
sys.modules[_cache_spec.name] = _cache_mod
_cache_spec.loader.exec_module(_cache_mod)

if "offer_management.tools" not in sys.modules:
    _tools_stub = pytypes.ModuleType("offer_management.tools")
    _tools_stub.__path__ = [os.path.join(_OFFER_PKG, "tools")]
    sys.modules["offer_management.tools"] = _tools_stub

_pricing_tools_spec = importlib.util.spec_from_file_location(
    "offer_management.tools.pricing_tools",
    os.path.join(_OFFER_PKG, "tools", "pricing_tools.py"),
)
_pricing_tools_mod = importlib.util.module_from_spec(_pricing_tools_spec)
sys.modules[_pricing_tools_spec.name] = _pricing_tools_mod
_pricing_tools_spec.loader.exec_module(_pricing_tools_mod)

_agent_spec = importlib.util.spec_from_file_location(
    "offer_management.agent",
    os.path.join(_OFFER_PKG, "agent.py"),
)
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

offer_management_agent = _agent_mod.offer_management_agent

_logger.info(
    "Offer management agent loaded: %s with %d tools",
    offer_management_agent.name,
    len(offer_management_agent.tools),
)
