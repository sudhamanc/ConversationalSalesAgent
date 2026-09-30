# Claude Code Instructions - Service Fulfillment Agent

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Scheduling/provisioning → [AGENTS.md - Tools](AGENTS.md#tools)
   - POST-SALE vs PRE-SALE → [AGENTS.md - Purpose](AGENTS.md#purpose)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

1. **Post-sale agent** - books the installation for a created order (before payment), then
   handles provisioning, technician dispatch, installation completion and activation
2. **Different from ServiceabilityAgent** - this is scheduling/fulfillment, not coverage
3. **Temperature = 0.3** (`generate_config(temperature=0.3, max_output_tokens=2048)`; 0.0 produced
   empty replies after tool calls)
4. **13 registered tools** (`agent.py`): `check_availability`, `schedule_installation`,
   `reschedule_appointment`, `cancel_appointment`, `provision_equipment`, `track_equipment`,
   `verify_equipment_delivery`, `dispatch_technician`, `update_installation_status`,
   `complete_installation`, `activate_service`, `run_service_tests`, `get_fulfillment_status`
   (`get_service_details` exists but is not registered)
5. **Status:** integrated A2A service (`uvicorn service_fulfillment_agent.server:app`, port 8207
   locally); the gateway workflow routes to it and hands off to `payment_agent` after booking
6. **Notifications** go through the `sales_common.notifications` outbox in the tool's transaction
   (`installation_scheduled`, `install_dispatched`, `installation_complete`, `service_activated`)

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
**ServiceabilityAgent (PRE-SALE):** [/ServiceabilityAgent/AGENTS.md](/ServiceabilityAgent/AGENTS.md)
