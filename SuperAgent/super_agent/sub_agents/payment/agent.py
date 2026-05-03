
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


# ---------------------------------------------------------------------------
# Programmatic Order/Install -> Payment auto-kickoff
# ---------------------------------------------------------------------------
# In the order flow, ADK sometimes successfully transfers control to
# payment_agent after installation scheduling, but Gemini returns an empty
# payment turn. When that happens, the backend emits a warning and falls back
# with generic text, which breaks the checkout flow. We detect that silent
# handoff and inject the payment kickoff prompt deterministically.

_PAYMENT_HANDOFF_PHRASES = (
    "installation scheduled",
    "appointment confirmed",
    "now let's proceed with payment",
    "now let's set up your payment",
    "payment processing",
)


def _last_agent_text(events, agent_name: str) -> str:
    for event in reversed(events or []):
        if getattr(event, "author", None) != agent_name or not getattr(event, "content", None):
            continue
        parts = getattr(event.content, "parts", None) or []
        texts = [getattr(part, "text", "") for part in parts if getattr(part, "text", "")]
        if texts:
            return "\n".join(texts).lower()
    return ""


def _recent_agent_text(events, authors: tuple[str, ...], limit: int = 6) -> str:
    texts: list[str] = []
    for event in reversed(events or []):
        if getattr(event, "author", None) not in authors or not getattr(event, "content", None):
            continue
        parts = getattr(event.content, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", "")
            if text:
                texts.append(text.lower())
                break
        if len(texts) >= limit:
            break
    return "\n".join(reversed(texts))


def _payment_after_agent(callback_context):
    """Inject a payment opener when payment_agent was reached but stayed silent."""
    try:
        events = getattr(callback_context._invocation_context.session, "events", [])
        payment_text = _last_agent_text(events, "payment_agent")
        if payment_text.strip():
            return None

        recent_flow_text = _recent_agent_text(
            events,
            ("service_fulfillment_agent", "order_agent"),
        )
        if not any(phrase in recent_flow_text for phrase in _PAYMENT_HANDOFF_PHRASES):
            return None

        state = callback_context.state
        order_ctx = state.get("order_context") or {}
        payment_ctx = state.get("payment_context") or {}

        # If payment already succeeded, don't inject the kickoff prompt.
        if payment_ctx.get("status") == "approved":
            return None

        order_id = order_ctx.get("order_id")
        amount = order_ctx.get("total_amount") or order_ctx.get("price")
        amount_text = ""
        if isinstance(amount, (int, float)):
            amount_text = f" for ${float(amount):.2f}"
        order_text = f" for order {order_id}" if isinstance(order_id, str) and order_id else ""

        from google.genai import types as _types

        callback_text = (
            f"Great, your installation is scheduled{order_text}. "
            f"Let's take care of payment{amount_text} next. "
            "Please provide your preferred payment method details for either a credit card or ACH transfer."
        )
        _logger.info(
            "[AUTO-KICKOFF] payment_agent injected opener "
            f"(order_id={order_id!r}, amount={amount!r})"
        )
        return _types.Content(parts=[_types.Part(text=callback_text)])
    except Exception as exc:
        _logger.warning(f"payment after_agent_callback failed (non-fatal): {exc}")
        return None


payment_agent.after_agent_callback = _payment_after_agent

_logger.info(f"Payment agent loaded: {payment_agent.name} with {len(payment_agent.tools)} tools")
