# Service Fulfillment Agent

**Type:** Transactional Agent - POST-SALE (Transaction Phase)
**Framework:** Google ADK 1.20.0
**Package:** `service_fulfillment_agent`
**Status:** ⏳ Standalone (Not Yet Integrated into SuperAgent)

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [Root CLAUDE.md](/CLAUDE.md)
   - [Root AGENTS.md](/AGENTS.md)
   - This file (ServiceFulfillmentAgent/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Agent development → [Root AGENTS.md - Golden Rule](/AGENTS.md#the-golden-rule)
   - Scheduling/provisioning → This file (see Tools section)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Purpose

The Service Fulfillment Agent manages the **service delivery lifecycle POST-SALE**, handling installation scheduling, provisioning, and service activation AFTER order confirmation.

**Key Responsibilities:**

1. **Installation Scheduling** - Technician allocation, slot availability
2. **Service Provisioning** - OSS/BSS integration, network configuration
3. **Order Tracking** - Status monitoring
4. **Credential Generation** - Service credentials (IP addresses, passwords)

---

## Architecture

| Attribute | Value |
|-----------|-------|
| **Type** | Transactional |
| **Phase** | Transaction (Phase 3 - POST-SALE) |
| **Source of Truth** | Scheduler API, OSS/BSS |
| **Temperature** | 0.0 (deterministic) |
| **Invocation** | After payment authorization and order confirmation |

---

## Tools

6 specialized tools:

1. **`check_installation_slot_availability(address: dict, date_range: tuple)`**
   - Queries technician schedules
   - Returns available time slots

2. **`schedule_installation(address: dict, date: str, time_slot: str)`**
   - Reserves technician slot
   - Creates work order

3. **`provision_service(order_id: str, service_type: str, speed_tier: str)`**
   - Configures network equipment (OLT, router)
   - Allocates resources (VLAN, IP address)
   - Generates service credentials

4. **`get_installation_status(work_order_id: str)`**
   - Tracks installation progress
   - Returns status: Scheduled/In Progress/Completed

5. **`verify_network_capacity(address: dict, bandwidth_required: int)`**
   - Checks available capacity
   - Ensures no oversubscription

6. **`generate_service_credentials(customer_id: str, service_id: str)`**
   - Creates login credentials
   - Assigns static IP (if Business class)

---

## Key Distinction: PRE-SALE vs POST-SALE

| Aspect | ServiceabilityAgent (PRE-SALE) | ServiceFulfillmentAgent (POST-SALE) |
|--------|--------------------------------|--------------------------------------|
| **Timing** | Before quote | After order confirmation |
| **Purpose** | "Can we serve?" | "When can we install?" |
| **Input** | Address | Confirmed order + availability |
| **Output** | Infrastructure details | Installation date + technician |
| **Data Source** | GIS/Coverage Map | Scheduler/Workforce Management |

---

## Integration Points (Production)

**Scheduler/Workforce Management:**
- Field service management system
- Technician dispatch
- Route optimization

**OSS/BSS:**
- Network provisioning
- Service activation
- Billing integration

**Current Implementation:** Mock APIs with simulated scheduling

---

## Development

```bash
cd ServiceFulfillmentAgent
pip install -e .
python main.py
```

**Related Documentation:** [/AGENTS.md](/AGENTS.md) | [/ServiceabilityAgent/AGENTS.md](/ServiceabilityAgent/AGENTS.md)
