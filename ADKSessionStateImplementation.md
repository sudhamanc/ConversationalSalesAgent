# ADK Session State Implementation Plan

**Goal:** Use ADK's session-scoped state (accessed via `ToolContext`) to pass structured data between agents deterministically — eliminating LLM-mediated data transfer for critical values (IDs, addresses, amounts) while retaining existing DB lookups as a fallback.

---

## Terminology Clarification

| ADK Concept | What It Is | Scope |
|-------------|-----------|-------|
| **`ToolContext`** | Object auto-injected into tool functions by ADK | Per-tool-invocation |
| **`tool_context.state`** | **Session state** — shared dict across ALL agents in the session | Per-session (survives agent transfers) |
| **`app:` prefix** | Application-scoped state keys (persist across sessions) | App-level |
| **`user:` prefix** | User-scoped state keys | User-level |
| **`temp:` prefix** | Temporary state keys (cleared between turns) | Turn-level |

**Key insight:** `tool_context.state` is actually `invocation_context.session.state`. The `ToolContext` is just the delivery mechanism — the **state itself is session-scoped** and shared across all agents.

---

## How ADK Auto-Injects ToolContext

From ADK source (`google/adk/flows/llm_flows/functions.py`):

```python
# ADK checks if the tool function accepts tool_context
if 'tool_context' in valid_params:
    args_to_call['tool_context'] = tool_context

# Then strips it from the schema sent to the LLM
args_to_call = {k: v for k, v in args_to_call.items() if k in valid_params}
```

**This means:**
- Add `tool_context: ToolContext` to any tool function signature
- ADK automatically provides it — the LLM never sees it
- No changes to agent registration, tool lists, or prompts needed

---

## Architecture: Three-Tier Data Resolution

For every consumer tool, data resolution follows this priority:

```
Priority 1: Session state (via tool_context.state)  ← fast, no DB hit, no hallucination
Priority 2: Deterministic DB lookup                  ← safety net for edge cases
Priority 3: LLM-provided parameter                  ← last resort fallback
```

This is **additive** — no existing deterministic code is removed.

---

## Session State Schema

### State Keys (using `app:` prefix for persistence)

```python
# Written by DiscoveryAgent tools
tool_context.state["app:customer_context"] = {
    "customer_id": "CUST-20260426-001",
    "company_name": "Crane.io",
    "contact_name": "John Smith",
    "contact_email": "john@crane.io",
    "contact_phone": "215-555-0100",
    "address": {
        "street": "123 Main St",
        "city": "Philadelphia",
        "state": "PA",
        "zip_code": "19103"
    },
    "bant_score": 75,
    "account_id": "ACC-..."
}

# Written by ServiceabilityAgent tools
tool_context.state["app:serviceability_context"] = {
    "is_serviceable": True,
    "infrastructure_type": "FTTP",
    "max_speed": "10 Gbps",
    "available_products": ["FIB-1G", "FIB-5G", "FIB-10G"],
    "service_address": "123 Main St, Philadelphia, PA 19103"
}

# Written by OfferManagement tools
tool_context.state["app:offer_context"] = {
    "offer_id": "OFF-1234567890",
    "items": [
        {"product_id": "FIB-5G", "name": "Business Fiber 5 Gbps", "price": 599.00}
    ],
    "term_months": 36,
    "total_price": 599.00,
    "total_discount": 50.00
}

# Written by OrderAgent tools
tool_context.state["app:order_context"] = {
    "order_id": "ORD-20260426-001",
    "cart_id": "CART-...",
    "customer_id": "CUST-20260426-001",
    "service_type": "Business Fiber 5 Gbps",
    "service_address": "123 Main St, Philadelphia, PA 19103",
    "price": 599.00,
    "offer_id": "OFF-1234567890",
    "status": "pending_payment"
}

# Written by ServiceFulfillmentAgent tools
tool_context.state["app:fulfillment_context"] = {
    "appointment_id": "APT-20260428-001",
    "scheduled_date": "2026-04-28",
    "window": "AM",
    "dispatch_id": "DSP-...",
    "circuit_id": "CKT-...",
    "account_id": "ACC-..."
}

# Written by PaymentAgent tools
tool_context.state["app:payment_context"] = {
    "transaction_id": "TXN-1234-599",
    "amount": 599.00,
    "status": "completed",
    "payment_method": "tok_visa_4242"
}
```

---

## Tools to Modify (12-15 total)

### Phase 1: Producers (write to session state)

| Agent | Tool Function | State Key Written | File |
|-------|--------------|-------------------|------|
| DiscoveryAgent | `add_company` | `app:customer_context` | `DiscoveryAgent/bootstrap_agent/tools/tools.py` |
| DiscoveryAgent | `get_company_profile` | `app:customer_context` | `DiscoveryAgent/bootstrap_agent/tools/tools.py` |
| ServiceabilityAgent | `check_service_availability` | `app:serviceability_context` | `ServiceabilityAgent/serviceability_agent/tools/serviceability_tools.py` |
| OfferManagement | `calculate_pricing` / `save_quote` | `app:offer_context` | `OfferManagement/offer_management/tools/pricing_tools.py` |
| OrderAgent | `create_order` | `app:order_context` | `OrderAgent/order_agent/tools/order_tools.py` |
| OrderAgent | `create_cart` / `add_to_cart` | `app:order_context` (cart_id) | `OrderAgent/order_agent/tools/cart_tools.py` |
| ServiceFulfillment | `schedule_installation` | `app:fulfillment_context` | `ServiceFulfillmentAgent/.../tools/scheduling_tools.py` |
| ServiceFulfillment | `activate_service` | `app:fulfillment_context` (circuit_id) | `ServiceFulfillmentAgent/.../tools/activation_tools.py` |

### Phase 2: Consumers (read from session state with DB fallback)

| Agent | Tool Function | State Key Read | Fallback | File |
|-------|--------------|----------------|----------|------|
| OrderAgent | `create_order` | `app:customer_context`, `app:offer_context` | LLM params | `OrderAgent/.../order_tools.py` |
| PaymentAgent | `process_payment` | `app:order_context` | DB lookup (already exists) | `PaymentAgent/.../payment_tools.py` |
| ServiceFulfillment | `schedule_installation` | `app:order_context` | LLM params | `ServiceFulfillmentAgent/.../scheduling_tools.py` |
| ServiceFulfillment | `activate_service` | `app:order_context` | LLM params | `ServiceFulfillmentAgent/.../activation_tools.py` |
| ServiceFulfillment | `dispatch_technician` | `app:fulfillment_context` | LLM params | `ServiceFulfillmentAgent/.../installation_tools.py` |
| CustomerComms | `send_notification` | `app:customer_context`, `app:order_context` | LLM params | `CustomerCommunicationAgent/.../tools/notification_tools.py` |

---

## Per-Tool Change Pattern

### Producer (additive — append to existing function)

```python
from google.adk.tools.tool_context import ToolContext

def create_order(customer_name: str, service_address: str, ..., tool_context: ToolContext) -> dict:
    # ... existing order creation logic (UNCHANGED) ...
    
    # NEW: Publish to session state for downstream agents
    tool_context.state["app:order_context"] = {
        "order_id": order_id,
        "customer_id": customer_id,
        "service_type": service_type,
        "price": price,
        "service_address": service_address,
    }
    
    return result  # existing return unchanged
```

### Consumer (wrap existing code with state-first check)

```python
from google.adk.tools.tool_context import ToolContext

def process_payment(amount: float, ..., order_id: str, tool_context: ToolContext) -> dict:
    # NEW: Try session state first
    order_ctx = tool_context.state.get("app:order_context", {})
    resolved_customer_id = order_ctx.get("customer_id", "")
    
    # EXISTING: DB fallback (unchanged)
    if not resolved_customer_id and order_id:
        try:
            conn = _get_db_connection()
            if conn:
                row = conn.execute(
                    "SELECT customer_id FROM orders WHERE order_id = ?", (order_id,)
                ).fetchone()
                if row:
                    resolved_customer_id = row["customer_id"] or ""
                conn.close()
        except Exception:
            pass
    
    # ... rest of existing logic uses resolved_customer_id ...
```

---

## Change Size Estimate

| Metric | Count |
|--------|-------|
| Tool functions to modify | 12-15 |
| Lines added per producer | ~5-8 (import + state write) |
| Lines added per consumer | ~3-5 (import + state read + fallback guard) |
| Total new lines | ~100-120 |
| Lines removed | 0 |
| Files touched | ~8-10 tool files |
| Prompt changes needed | 0 |
| Agent registration changes | 0 |
| Risk level | Low (additive, backward-compatible) |

---

## Implementation Order

### Step 1: OrderAgent `create_order` (Producer + Consumer)
Most impactful — produces `app:order_context` consumed by 3 downstream agents.

### Step 2: PaymentAgent `process_payment` (Consumer)
Already has DB fallback. Add session state as Priority 1.

### Step 3: DiscoveryAgent tools (Producer)
Writes `app:customer_context` — consumed by OrderAgent, PaymentAgent, ServiceFulfillment.

### Step 4: ServiceFulfillmentAgent tools (Producer + Consumer)
Scheduling reads `app:order_context`, writes `app:fulfillment_context`.
Activation reads both, writes circuit/account IDs.

### Step 5: OfferManagement tools (Producer)
Writes `app:offer_context` — consumed by OrderAgent for offer_id linkage.

### Step 6: ServiceabilityAgent (Producer)
Writes `app:serviceability_context` — less critical but completes the chain.

---

## Verification

1. **Unit test**: Mock `ToolContext` with a dict-backed state, verify producers write expected keys
2. **Integration test**: Run full sales flow, inspect `session.state` after each agent turn
3. **Fallback test**: Clear session state mid-flow, verify DB lookups still resolve data
4. **E2E test**: Full conversation flow — verify all DB tables (orders, payments, fulfillments, customer_master) have correct foreign keys populated

---

## What This Eliminates

| Current Problem | How Session State Fixes It |
|----------------|---------------------------|
| LLM extracts order_id from conversation history (may hallucinate) | Tool reads `state["app:order_context"]["order_id"]` directly |
| LLM carries customer_id across 3 agent transfers (may drop it) | Every tool reads `state["app:customer_context"]["customer_id"]` |
| Address zip codes modified during LLM rephrasing | Structured JSON in state — never touched by LLM |
| Prompt instructions needed for "extract X from conversation" | State access is code-level — prompts simplified |

## What This Preserves

- All existing deterministic DB lookups (demoted to Priority 2 fallback)
- All existing LLM parameter passing (demoted to Priority 3 fallback)
- All existing tool signatures (ToolContext is additive, not replacing any param)
- All existing prompt instructions (can be simplified later, not required now)
