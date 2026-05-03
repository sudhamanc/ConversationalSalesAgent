# ADK Session State Implementation Plan

**Goal:** Use ADK's session-scoped state (accessed via `ToolContext`) to pass structured data between agents deterministically — eliminating LLM-mediated data transfer for critical values (IDs, addresses, amounts) while leaving all existing DB reads, writes, and lookups completely unchanged.

---

## Design Principles

- **Additive only** — no existing code removed or modified
- **DB layer untouched** — all existing DB reads/writes stay exactly as-is; session state is a new layer on top
- **No breaking changes** — `tool_context` parameter is optional (`= None`); all fallbacks preserved
- **No context bloat** — state lives in Python memory, never injected into the conversation or LLM context window
- **No cost increase** — state read/write is pure Python dictionary operations, no LLM calls

---

## Terminology Clarification

| ADK Concept | What It Is | Scope |
| --- | --- | --- |
| **`ToolContext`** | Object auto-injected into tool functions by ADK | Per-tool-invocation |
| **`tool_context.state`** | Shared dict across ALL agents in the session | Per-session (survives agent transfers) |
| **No prefix** | Session-scoped keys — isolated per user, cleared when session ends | Per-session ✅ |
| **`app:` prefix** | Application-scoped — shared across ALL sessions on the same server | App-level ⚠️ DO NOT USE |
| **`user:` prefix** | User-scoped state keys | User-level |
| **`temp:` prefix** | Temporary state keys (cleared between turns) | Turn-level |

> **⚠️ Do NOT use `app:` prefix.** In `InMemorySessionService`, `app:`-scoped state is shared across all concurrent users on the same server instance — a multi-user data corruption bug. Use unprefixed keys (session-scoped).

**Key insight:** `tool_context.state` is actually `invocation_context.session.state`. The `ToolContext` is just the delivery mechanism — the state itself is session-scoped and shared across all agents within that session.

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

- Add `tool_context: ToolContext = None` to any tool function signature
- ADK automatically provides it at runtime — the LLM never sees it
- No changes to agent registration, tool lists, or prompts needed

---

## Architecture: Three-Tier Data Resolution

For every consumer tool, data resolution follows this priority:

```
Priority 1: Session state (tool_context.state)   ← fast, no DB hit, no hallucination
Priority 2: Existing DB lookup code              ← UNCHANGED — already in the codebase
Priority 3: LLM-provided parameter               ← UNCHANGED — already in the codebase
```

Priority 2 and 3 are not new fallbacks to write — they are the existing code that already runs today. Session state simply adds Priority 1 in front of them.

---

## Session State Schema

```python
# Written by DiscoveryAgent
tool_context.state["customer_context"] = {
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
    "bant_score": 75
}

# Written by ServiceabilityAgent
tool_context.state["serviceability_context"] = {
    "is_serviceable": True,
    "infrastructure_type": "FTTP",
    "max_speed": "10 Gbps",
    "available_products": ["FIB-1G", "FIB-5G", "FIB-10G"],
    "service_address": "123 Main St, Philadelphia, PA 19103"
}

# Written by OfferManagement
tool_context.state["offer_context"] = {
    "offer_id": "OFF-1234567890",
    "items": [
        {"product_id": "FIB-5G", "name": "Business Fiber 5 Gbps", "price": 599.00}
    ],
    "term_months": 36,
    "total_price": 599.00,
    "total_discount": 50.00
}

# Written by OrderAgent
tool_context.state["order_context"] = {
    "order_id": "ORD-20260426-001",
    "cart_id": "CART-...",
    "customer_id": "CUST-20260426-001",
    "service_type": "Business Fiber 5 Gbps",
    "service_address": "123 Main St, Philadelphia, PA 19103",
    "price": 599.00,
    "offer_id": "OFF-1234567890",
    "status": "pending_payment"
}

# Written by ServiceFulfillmentAgent
tool_context.state["fulfillment_context"] = {
    "appointment_id": "APT-20260428-001",
    "scheduled_date": "2026-04-28",
    "window": "AM",
    "dispatch_id": "DSP-...",
    "circuit_id": "CKT-...",
    "account_id": "ACC-..."
}

# Written by PaymentAgent
tool_context.state["payment_context"] = {
    "transaction_id": "TXN-1234-599",
    "amount": 599.00,
    "status": "completed",
    "payment_method": "tok_visa_4242"
}
```

---

## Implementation Phases

### Phase 1 — Critical ID Chain (High Value, ~80 lines, 5-6 files)

These are the IDs that currently pass through the LLM across agent transfers and carry the highest hallucination risk. This phase delivers the most value.

| Step | Agent | Action | State Key | File |
| --- | --- | --- | --- | --- |
| 1 | DiscoveryAgent | Write on `add_new_company` / `get_company_profile` | `customer_context` | `DiscoveryAgent/bootstrap_agent/sub_agents/discovery/discovery_agent.py` |
| 2 | OfferManagement | Write on `save_quote` | `offer_context` | `OfferManagement/offer_management/tools/pricing_tools.py` |
| 3 | OrderAgent | Read `customer_context` + `offer_context`; write on `create_order` | `order_context` | `OrderAgent/order_agent/tools/order_tools.py`, `cart_tools.py` |
| 4 | PaymentAgent | Read `order_context`; write on `process_payment` | `payment_context` | `PaymentAgent/payment_agent/tools/payment_tools.py` |
| 5 | ServiceFulfillmentAgent | Read `order_context` + `payment_context` | — | `ServiceFulfillmentAgent/service_fulfillment_agent/tools/activation_tools.py` |

### Phase 2 — Serviceability + Comms (Lower Priority)

Less critical because serviceability data is already persisted in the DB and agents query it directly. CustomerComms already receives IDs via tool call parameters.

| Step | Agent | Action | State Key | File |
| --- | --- | --- | --- | --- |
| 6 | ServiceabilityAgent | Write on address validation | `serviceability_context` | `ServiceabilityAgent/serviceability_agent/tools/address_tools.py` |
| 7 | CustomerCommunicationAgent | Read `customer_context` + `order_context` | — | `CustomerCommunicationAgent/customer_communication_agent/tools/notification_tools.py` |

---

## Per-Tool Change Pattern

### Producer (append ~5-8 lines to existing function)

```python
from google.adk.tools.tool_context import ToolContext

def add_new_company(..., tool_context: ToolContext = None) -> dict:
    # ... existing logic UNCHANGED ...

    # NEW: write to session state after successful operation
    if tool_context and result.get("success"):
        tool_context.state["customer_context"] = {
            "customer_id": result["customer_id"],
            "company_name": result["company_name"],
            "address": result.get("address", {}),
        }

    return result  # existing return unchanged
```

### Consumer (add ~3-5 lines before existing logic)

```python
from google.adk.tools.tool_context import ToolContext

def process_payment(amount: float, order_id: str = None,
                    tool_context: ToolContext = None) -> dict:
    # NEW: Priority 1 — read from session state
    order_ctx = tool_context.state.get("order_context", {}) if tool_context else {}
    resolved_order_id = order_id or order_ctx.get("order_id")
    resolved_customer_id = order_ctx.get("customer_id", "")

    # EXISTING: Priority 2 — DB lookup (code already here, unchanged)
    if not resolved_customer_id and resolved_order_id:
        # ... existing DB lookup code ...

    # EXISTING: Priority 3 — LLM param already used as fallback above

    # ... rest of existing logic uses resolved_* variables ...
```

---

## Change Size Estimate

| Metric | Count |
| --- | --- |
| Tool functions to modify | 12-15 |
| Lines added per producer | ~5-8 |
| Lines added per consumer | ~3-5 |
| Total new lines | ~100-120 |
| Lines removed | 0 |
| Files touched | ~8-10 |
| Prompt changes needed | 0 |
| Agent registration changes | 0 |
| DB schema changes | 0 |
| Risk level | Low — additive, backward-compatible |

---

## Verification

1. **Unit test** — mock `ToolContext` with a dict-backed state; verify producers write expected keys after successful operations
2. **Integration test** — run a full sales flow; inspect `session.state` after each agent turn to confirm keys are populated
3. **Fallback test** — clear session state mid-flow; verify existing DB lookups and LLM params still resolve data correctly (existing behavior unchanged)
4. **Multi-user test** — run two concurrent sessions; confirm `customer_context` in session A is not visible in session B
5. **E2E test** — `SuperAgent/e2e_test.py` should pass without modification

---

## What This Eliminates

| Current Problem | How Session State Fixes It |
| --- | --- |
| LLM extracts `order_id` from conversation history (may hallucinate) | Tool reads `state["order_context"]["order_id"]` directly |
| `customer_id` carried across 3 agent transfers via LLM (may drop it) | Every consumer tool reads `state["customer_context"]["customer_id"]` |
| Address zip codes modified by LLM rephrasing | Structured dict in state — LLM never touches it |
| Long sessions: IDs from early turns get summarized out of history | State persists for the full session regardless of history length |

## What This Preserves

- All existing DB reads, writes, and lookups — completely unchanged
- All existing LLM parameter passing — unchanged, still works as final fallback
- All existing tool signatures — `ToolContext` is additive, replaces nothing
- All existing prompt instructions — can be simplified later, not required now
- All existing agent registration and orchestration logic
