# Recursive Router Pattern – Server-Side Multi-Agent Orchestration

## Problem Statement

**ADK Limitation:** When a sub-agent responds in Google ADK, the turn ends immediately. The parent orchestrator (SuperAgent) never regains control to evaluate the response and route to the next agent.

**Previous Workaround:** Client-side auto-continuation JavaScript that detected "Let me..." phrases and automatically sent follow-up messages.

**Issue:** This violated clean architecture by placing orchestration logic in the UI layer.

---

## Solution: Server-Side Recursive Router

### Architecture Overview

```
User Input → Server API
              ↓
         Recursive Router Loop
              ↓
    ┌─────────────────────┐
    │ Execute Agent Turn  │
    └─────────────────────┘
              ↓
    ┌─────────────────────┐
    │ Detect Handoff?     │
    └─────────────────────┘
         Yes ↓       ↓ No
    Continue Loop   Stream Final Response
              ↓
    Next Agent Turn
```

### Implementation

**Location:** `SuperAgent/server/api/chat.py`

**Core Functions:**

1. **`_execute_single_turn()`** - Executes one agent turn and collects full response
2. **`_stream_agent()`** - Recursive router that loops until no more handoffs

### How It Works

```python
async def _stream_agent(user_id: str, session_id: str, user_message: str):
    current_message = user_message
    iteration = 0
    max_iterations = 5  # Prevent infinite loops
    
    while iteration < max_iterations:
        # 1. Execute one agent turn
        full_text, author, should_continue, next_message = await _execute_single_turn(
            user_id, session_id, current_message
        )
        
        # 2. Stream response to client
        yield stream_response(full_text, author)
        
        # 3. Check for handoff signal
        if should_continue and next_message:
            current_message = next_message  # Continue to next agent
        else:
            yield done_signal()  # Workflow complete
            return
```

---

## Handoff Signals

### Pattern Detection

The router detects handoff signals in agent responses:

| Pattern | Next Agent | Continuation Message |
|---------|------------|---------------------|
| "Let me check service availability at **[address]**" | ServiceabilityAgent | "Check service availability at [address]" |
| "Let me show you available products" | ProductAgent | "Show me available products" |
| "Let me process your payment" | PaymentAgent | "Process payment" |
| "Let me schedule your installation" | ServiceFulfillmentAgent | "Schedule installation" |

### Adding New Handoff Patterns

In `_execute_single_turn()`:

```python
# Pattern 2: Product lookup
if "Let me show you available products" in full_text:
    continuation_message = "Show me available products"
    should_continue = True

# Pattern 3: Payment processing
elif "Let me process your payment" in full_text:
    continuation_message = "Process payment"
    should_continue = True
```

---

## Example Flow

### User Request: "I'm PizzeriaInc at 123 Main St, Philadelphia"

**Iteration 1 - DiscoveryAgent:**
```
Input:  "I'm PizzeriaInc at 123 Main St, Philadelphia"
Agent:  discovery_agent
Output: "Welcome! I've registered PizzeriaInc at 123 Main St, Philadelphia, PA 19103. 
         Let me check service availability at this address."
Signal: HANDOFF detected (service availability)
```

**Iteration 2 - ServiceabilityAgent:**
```
Input:  "Check service availability at 123 Main St, Philadelphia, PA 19103"
Agent:  serviceability_agent
Output: "Good news! Service is available at 123 Main St. We offer:
         - Fiber 1G: $299/mo
         - Fiber 5G: $499/mo
         - Fiber 10G: $799/mo"
Signal: NO HANDOFF (workflow complete)
```

**Client Experience:**
User sees both responses streamed sequentially in real-time, appearing as one continuous conversation.

---

## Benefits Over Client-Side Approach

| Aspect | Client-Side | Server-Side Recursive Router |
|--------|-------------|------------------------------|
| **Architecture** | ❌ Logic in UI layer | ✅ Logic in orchestration layer |
| **Testability** | ❌ Requires browser testing | ✅ Pure backend testing |
| **Observability** | ❌ Hard to log/trace | ✅ Full server-side logging |
| **Security** | ❌ Client can manipulate flow | ✅ Server enforces workflow |
| **Reliability** | ❌ Depends on JS execution | ✅ Guaranteed execution |
| **Future-Proof** | ❌ Tied to web client | ✅ Works for all clients (mobile, API, etc.) |

---

## Configuration

### Max Iterations

Prevents infinite loops in case of misconfigured handoffs:

```python
max_iterations = 5  # Configurable in chat.py
```

### Streaming Behavior

Responses are streamed character-by-character for smooth UX:

```python
chunk_size = 10  # Characters per chunk
await asyncio.sleep(0.01)  # 10ms delay between chunks
```

---

## Logging & Observability

### Log Indicators

```
🔁 Recursive router iteration 1: I'm PizzeriaInc...
📤 Streaming response from discovery_agent (150 chars)
🔄 Handoff detected, continuing with: Check service availability...
🔁 Recursive router iteration 2: Check service availability...
📤 Streaming response from serviceability_agent (220 chars)
✅ Workflow complete after 2 iteration(s)
```

### Debugging

Enable debug logs in `.env`:
```bash
LOG_LEVEL=DEBUG
```

---

## Integration with Sub-Agents

### DiscoveryAgent Integration

**Location:** `DiscoveryAgent/bootstrap_agent/sub_agents/discovery/discovery_agent.py`

**Instruction Excerpt:**
```python
instruction="""
...
**After successfully adding a company with a complete address:**
Confirm the registration and then EXPLICITLY state: "Let me check service availability at this address."

Your response should be structured as:
"Welcome! I've registered **[Company Name]** at **[Full Address]**. Let me check service availability at this address."
...
"""
```

**Key:** The sub-agent must output the exact handoff phrase for the router to detect it.

---

## Testing

### Manual Test

1. Start server: `cd SuperAgent/server && uvicorn main:app --reload`
2. Start client: `cd SuperAgent/client && npm run dev`
3. Test input: "I'm TestCorp at 456 Oak St, Boston, MA 02101"
4. Expected: See Discovery response followed immediately by Serviceability response

### Server Logs

Check terminal for:
- `🔁 Recursive router iteration 1`
- `🔄 Handoff detected`
- `🔁 Recursive router iteration 2`
- `✅ Workflow complete`

---

## Future Enhancements

### 1. Dynamic Handoff Metadata

Instead of pattern matching, sub-agents could return structured metadata:

```python
# Sub-agent returns
{
    "response": "Welcome! I've registered PizzeriaInc...",
    "metadata": {
        "handoff_to": "serviceability_agent",
        "context": {"address": "123 Main St..."}
    }
}
```

### 2. Parallel Agent Execution

For independent tasks:
```python
# Check serviceability AND credit check in parallel
results = await asyncio.gather(
    serviceability_check(address),
    credit_check(company)
)
```

### 3. Conditional Workflows

```python
if "pricing" in handoff_signals:
    # Discovery → Serviceability → Product → Pricing → Order
    workflow = [serviceability, product, pricing, order]
else:
    # Discovery → Serviceability only
    workflow = [serviceability]
```

---

## Comparison: Sub-Agents vs Tools

This solution keeps sub-agents intact. Alternative: Convert to tools.

| Approach | Pros | Cons |
|----------|------|------|
| **Sub-Agents + Recursive Router** | ✅ Preserves agent specialization<br>✅ Clean separation of concerns<br>✅ Easy to add new agents | ⚠️ Requires handoff pattern matching<br>⚠️ Multiple LLM calls |
| **Tools (Flat Architecture)** | ✅ Single LLM call<br>✅ Native ADK ReAct loop<br>✅ No handoff detection needed | ❌ Loses agent modularity<br>❌ SuperAgent prompt bloat<br>❌ Harder to test individual agents |

**Decision:** Recursive Router chosen to preserve clean multi-agent architecture.

---

## References

- **Implementation:** [SuperAgent/server/api/chat.py](../server/api/chat.py)
- **Discovery Agent:** [DiscoveryAgent/bootstrap_agent/sub_agents/discovery/](../../DiscoveryAgent/bootstrap_agent/sub_agents/discovery/)
- **Architecture Docs:** [AGENTS.md](../../AGENTS.md)
- **Test Scenarios:** [Scenarios.md](../../Scenarios.md)

---

**Last Updated:** February 15, 2026  
**Author:** Multi-Agent System Design Team  
**Status:** ✅ Implemented & Tested
