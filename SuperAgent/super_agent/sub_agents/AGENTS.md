# SuperAgent Sub-Agent Wrappers

This directory contains **importlib isolation wrappers** that load external agent packages into the SuperAgent's agent tree without triggering `__init__.py` parent-binding conflicts.

---

## Why Importlib Wrappers?

ADK enforces **one parent per agent**. If an external agent's `__init__.py` runs, it binds the agent to its own root. Importlib loads a fresh Agent instance for SuperAgent's hierarchy.

## Wrapper Pattern

Each sub-directory follows the same pattern:

```python
import importlib.util, sys, types as pytypes

# Stub parent package
if "package_name" not in sys.modules:
    _stub = pytypes.ModuleType("package_name")
    _stub.__path__ = [_PKG_DIR]
    sys.modules["package_name"] = _stub

# Load agent module in isolation
_spec = importlib.util.spec_from_file_location(...)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

# Export fresh Agent instance
agent = _mod.agent_name
```

---

## Sub-Agent Registry

| Wrapper Directory | External Package | Agent Name | DB Tables | Callback |
|------------------|-----------------|------------|-----------|----------|
| `discovery/` | `DiscoveryAgent/bootstrap_agent` | `discovery_agent` | accounts, contacts, spend, opportunities, insights, actions | `_discovery_after_agent` → serviceability |
| `serviceability/` | `ServiceabilityAgent/serviceability_agent` | `serviceability_agent` | None (stateless) | — |
| `product/` | `ProductAgent/product_agent` | `product_agent` | None (catalog + RAG) | — |
| `offer_management/` | `OfferManagement/offer_management` | `offer_management_agent` | quotes | — |
| `order/` | `OrderAgent/order_agent` | `order_agent` | carts, cart_items, orders, order_items | — |
| `payment/` | `PaymentAgent/payment_agent` | `payment_agent` | payments | `_payment_after_agent` (self-inject) |
| `service_fulfillment/` | `ServiceFulfillmentAgent/service_fulfillment_agent` | `service_fulfillment_agent` | fulfillments, customer_master | `_fulfillment_after_agent` → payment |
| `customer_communication/` | `CustomerCommunicationAgent/customer_communication_agent` | `customer_communication_agent` | notifications, dedup_cache | — |
| `greeting/` | (inline) | `greeting_agent` | None | — |
| `faq/` | (inline) | `faq_agent` | None | — |

---

## Critical Rules

1. **Never call `load_dotenv()` in sub-agent code** — environment is set by SuperAgent
2. **Hardcode agent names** — never read from `AGENT_NAME` env var
3. **No default model values** — use `os.getenv("GEMINI_MODEL")` without fallback
4. **All agents share unified DB** — `SALES_AGENT_DB_PATH` env var points to `sales_agent.db`

---

## Programmatic Handoffs (`after_agent_callback`)

Some wrappers attach `after_agent_callback` to enable **deterministic, same-turn agent transfers** without requiring a user message:

| Wrapper | Callback | Target | Trigger |
|---------|----------|--------|--------|
| `discovery/agent.py` | `_discovery_after_agent` | `serviceability_agent` | Agent registers company with address and promises serviceability check |
| `service_fulfillment/agent.py` | `_fulfillment_after_agent` | `payment_agent` | Agent confirms installation scheduling (phrases: "installation is confirmed", "appointment confirmed", etc.) |
| `payment/agent.py` | `_payment_after_agent` | (self-inject) | PaymentAgent produces empty output after receiving handoff — injects opener text |

**Pattern:**
```python
def _example_after_agent(callback_context):
    events = callback_context._invocation_context.session.events
    agent_text = _get_last_text(events, "agent_name")
    if trigger_detected(agent_text):
        callback_context.actions.transfer_to_agent = "target_agent"
        return types.Content(parts=[types.Part(text="")])
    return None

agent.after_agent_callback = _example_after_agent
```

These are ADK-native, deterministic, and execute within the same invocation turn.

---

## Database Configuration

All database-backed agents resolve their DB path via:
```
SALES_AGENT_DB_PATH (env) → agent-specific fallback → local default
```

When `SALES_AGENT_DB_PATH` is set (always in production), all agents read/write the same `sales_agent.db` file containing 17 tables across 7 domains.
