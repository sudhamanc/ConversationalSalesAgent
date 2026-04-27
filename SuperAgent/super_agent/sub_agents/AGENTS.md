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

| Wrapper Directory | External Package | Agent Name | DB Tables |
|------------------|-----------------|------------|-----------|
| `discovery/` | `DiscoveryAgent/bootstrap_agent` | `discovery_agent` | accounts, contacts, spend, opportunities, insights, actions |
| `serviceability/` | `ServiceabilityAgent/serviceability_agent` | `serviceability_agent` | None (stateless) |
| `product/` | `ProductAgent/product_agent` | `product_agent` | None (catalog + RAG) |
| `offer_management/` | `OfferManagement/offer_management` | `offer_management_agent` | quotes |
| `order/` | `OrderAgent/order_agent` | `order_agent` | carts, cart_items, orders, order_items |
| `payment/` | `PaymentAgent/payment_agent` | `payment_agent` | payments |
| `service_fulfillment/` | `ServiceFulfillmentAgent/service_fulfillment_agent` | `service_fulfillment_agent` | fulfillments, customer_master |
| `customer_communication/` | `CustomerCommunicationAgent/customer_communication_agent` | `customer_communication_agent` | notifications, dedup_cache |
| `greeting/` | (inline) | `greeting_agent` | None |
| `faq/` | (inline) | `faq_agent` | None |

---

## Critical Rules

1. **Never call `load_dotenv()` in sub-agent code** — environment is set by SuperAgent
2. **Hardcode agent names** — never read from `AGENT_NAME` env var
3. **No default model values** — use `os.getenv("GEMINI_MODEL")` without fallback
4. **All agents share unified DB** — `SALES_AGENT_DB_PATH` env var points to `sales_agent.db`

---

## Database Configuration

All database-backed agents resolve their DB path via:
```
SALES_AGENT_DB_PATH (env) → agent-specific fallback → local default
```

When `SALES_AGENT_DB_PATH` is set (always in production), all agents read/write the same `sales_agent.db` file containing 17 tables across 7 domains.
