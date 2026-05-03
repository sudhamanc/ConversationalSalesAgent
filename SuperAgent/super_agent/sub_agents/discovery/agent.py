
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
if _db_spec is None or _db_spec.loader is None:
    raise ImportError("Failed to load bootstrap_agent.sub_agents.discovery.db_tools module spec")
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
if _agent_spec is None or _agent_spec.loader is None:
    raise ImportError("Failed to load bootstrap_agent.sub_agents.discovery.discovery_agent module spec")
_agent_mod = importlib.util.module_from_spec(_agent_spec)
sys.modules[_agent_spec.name] = _agent_mod
_agent_spec.loader.exec_module(_agent_mod)

# ---------------------------------------------------------------------------
# Export the fresh, unbound Agent instance
# ---------------------------------------------------------------------------
discovery_agent = _agent_mod.discovery_agent


# ---------------------------------------------------------------------------
# Programmatic Discovery -> Serviceability auto-handoff
# ---------------------------------------------------------------------------
# After the LLM finishes a turn, inspect session state. If customer_context is
# populated (Discovery has registered the company / collected BANT) but
# serviceability_context isn't yet, and the user's most recent message asks for
# serviceability OR the agent's response promised one, programmatically set
# actions.transfer_to_agent so ADK routes the next turn to serviceability_agent.
#
# This bypasses Gemini's intermittent failure to combine text + transfer_to_agent
# tool calls in the same response.

_SERVICEABILITY_REQUEST_PHRASES = (
    "check serviceability",
    "check service availability",
    "is my address serviceable",
    "check if my location",
    "serviceability check",
    "check coverage",
    "is service available",
    "check address serviceability",
    "provide serviceability",
)
_SERVICEABILITY_PROMISE_PHRASES = (
    "let me check serviceability",
    "let me check if your address",
    "i'll check serviceability",
    "i'll check if your address",
    "checking serviceability",
)


def _last_user_text(events) -> str:
    for e in reversed(events or []):
        if getattr(e, "author", None) == "user" and getattr(e, "content", None):
            parts = getattr(e.content, "parts", None) or []
            for p in parts:
                txt = getattr(p, "text", None)
                if txt:
                    return txt.lower()
            return ""
    return ""


def _last_agent_text(events, agent_name) -> str:
    for e in reversed(events or []):
        if getattr(e, "author", None) == agent_name and getattr(e, "content", None):
            parts = getattr(e.content, "parts", None) or []
            for p in parts:
                txt = getattr(p, "text", None)
                if txt:
                    return txt.lower()
    return ""


def _discovery_after_agent(callback_context):
    """Force-transfer to serviceability_agent when the LLM forgot to."""
    try:
        state = callback_context.state
        cust = state.get("customer_context") or {}
        srv = state.get("serviceability_context") or {}

        # Only fire if discovery has identified a customer AND serviceability
        # hasn't already been checked this session.
        if not cust.get("customer_id") or srv.get("is_serviceable") is not None:
            return None

        events = getattr(callback_context._invocation_context.session, "events", [])
        user_text = _last_user_text(events)
        agent_text = _last_agent_text(events, "discovery_agent")

        wants = any(p in user_text for p in _SERVICEABILITY_REQUEST_PHRASES)
        promised = any(p in agent_text for p in _SERVICEABILITY_PROMISE_PHRASES)
        if not (wants or promised):
            return None

        callback_context.actions.transfer_to_agent = "serviceability_agent"
        _logger.info(
            "[AUTO-HANDOFF] discovery_agent -> serviceability_agent "
            f"(wants={wants} promised={promised} customer_id={cust.get('customer_id')})"
        )

        # Returning Content makes ADK emit the event with our actions attached.
        # Use an empty text part so nothing extra appears to the user.
        from google.genai import types as _types
        return _types.Content(parts=[_types.Part(text="")])
    except Exception as exc:
        _logger.warning(f"after_agent_callback failed (non-fatal): {exc}")
        return None


discovery_agent.after_agent_callback = _discovery_after_agent
_logger.info("Attached programmatic Discovery->Serviceability handoff callback.")
