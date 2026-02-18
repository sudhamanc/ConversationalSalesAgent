
"""
Discovery sub-agent wrapper.

Loads the discovery agent's tool functions and database class from the
DiscoveryAgent project (located at ../../DiscoveryAgent relative to the
SuperAgent root) without triggering the DiscoveryAgent's own root agent
initialization.

Why this is needed:
    Importing anything via ``bootstrap_agent.*`` triggers
    ``bootstrap_agent/__init__.py`` which creates the DiscoveryAgent's
    root agent and binds ``discovery_agent`` as its child.  ADK enforces
    one parent per agent, so SuperAgent can't re-use that instance.  We
    use importlib to load *only* the two files we need (db_tools.py and
    discovery_agent.py) with stub parent packages, then extract a fresh,
    unbound Agent instance.
"""

# Logging setup for module entry
import logging
_logger = logging.getLogger("superagent.discovery.agent")
if not _logger.hasHandlers():
    import sys as _sys
    _handler = logging.StreamHandler(_sys.stdout)
    _formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.info("SuperAgent Discovery sub-agent module loaded.")

import importlib.util
import os
import sys
import types as pytypes

# ---------------------------------------------------------------------------
# Locate the DiscoveryAgent project
# ---------------------------------------------------------------------------
_DISCOVERY_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "DiscoveryAgent")
)
_DISCOVERY_PKG = os.path.join(
    _DISCOVERY_BASE, "bootstrap_agent", "sub_agents", "discovery"
)

# ---------------------------------------------------------------------------
# Stub parent packages so relative imports inside the DiscoveryAgent files
# resolve correctly without running bootstrap_agent/__init__.py (which would
# bind the discovery_agent to the DiscoveryAgent's own root agent).
# ---------------------------------------------------------------------------
for _pkg_name in [
    "bootstrap_agent",
    "bootstrap_agent.sub_agents",
    "bootstrap_agent.sub_agents.discovery",
]:
    if _pkg_name not in sys.modules:
        _stub = pytypes.ModuleType(_pkg_name)
        _stub.__path__ = [os.path.join(_DISCOVERY_BASE, *_pkg_name.split("."))]
        sys.modules[_pkg_name] = _stub

# ---------------------------------------------------------------------------
# Load db_tools.py (dependency — has no further relative imports)
# ---------------------------------------------------------------------------
_db_spec = importlib.util.spec_from_file_location(
    "bootstrap_agent.sub_agents.discovery.db_tools",
    os.path.join(_DISCOVERY_PKG, "db_tools.py"),
)
_db_mod = importlib.util.module_from_spec(_db_spec)
sys.modules[_db_spec.name] = _db_mod
_db_spec.loader.exec_module(_db_mod)

# ---------------------------------------------------------------------------
# Load discovery_agent.py (its ``from .db_tools import ...`` resolves via
# the sys.modules entry we just created above)
# ---------------------------------------------------------------------------
_agent_spec = importlib.util.spec_from_file_location(
    "bootstrap_agent.sub_agents.discovery.discovery_agent",
    os.path.join(_DISCOVERY_PKG, "discovery_agent.py"),
)
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

# ---------------------------------------------------------------------------
# Export the fresh, unbound Agent instance
# ---------------------------------------------------------------------------
discovery_agent = _agent_mod.discovery_agent
