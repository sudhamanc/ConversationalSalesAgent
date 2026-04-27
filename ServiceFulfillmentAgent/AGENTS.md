# Service Fulfillment Agent

**Type:** Transactional Agent — POST-SALE (Transaction Phase)
**Framework:** Google ADK 1.20.0+
**Package:** `service_fulfillment_agent`
**Status:** ✅ Deployed in SuperAgent

---

## Purpose

The Service Fulfillment Agent manages the **post-sale lifecycle**: installation scheduling, technician dispatch, installation completion, and service activation. It is the final agent in the sales pipeline and performs the critical "prospect → customer" transition.

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `service_fulfillment_agent` (hardcoded) |
| **Model** | `os.getenv("GEMINI_MODEL")` — no default |
| **Temperature** | 0.0 (deterministic) |
| **Max Tokens** | 2048 |
| **Database** | Unified `sales_agent.db` → `fulfillments`, `customer_master`, `accounts`, `orders` |

### Component Structure

```
ServiceFulfillmentAgent/
├── service_fulfillment_agent/
│   ├── __init__.py
│   ├── agent.py                    # Agent definition
│   ├── prompts.py                  # System instructions
│   ├── tools/
│   │   ├── scheduling_tools.py     # Appointment scheduling
│   │   ├── installation_tools.py   # Technician dispatch & install
│   │   └── activation_tools.py     # Service activation (lifecycle capstone)
│   └── utils/
│       └── logger.py
└── tests/
```

### Database Tables

| Table | Access | Purpose |
|-------|--------|---------|
| `fulfillments` | R/W (primary) | Fulfillment lifecycle records |
| `customer_master` | W (on activation) | Post-fulfillment customer record |
| `accounts` | R/W (on activation) | Update Existing Customer → Y |
| `orders` | R/W (on activation) | Update status → fulfilled |
| `order_items` | R (on activation) | Read ordered products |

---

## Tools (3 Tool Modules, 10 Functions)

### Scheduling Tools (scheduling_tools.py)

| Tool | Signature | Tables | Purpose |
|------|-----------|--------|---------|
| `check_availability` | `(service_address, service_type, start_date, num_days)` | None (simulated) | Check available installation slots |
| `schedule_installation` | `(service_address, scheduled_date, window, order_id, customer_id, ...)` | `fulfillments` INSERT | Book installation appointment |
| `reschedule_appointment` | `(appointment_id, new_date, new_window, reason)` | None (simulated) | Reschedule existing appointment |
| `cancel_appointment` | `(appointment_id, reason)` | None (simulated) | Cancel appointment |

### Installation Tools (installation_tools.py)

| Tool | Signature | Tables | Purpose |
|------|-----------|--------|---------|
| `dispatch_technician` | `(appointment_id, order_id, scheduled_date)` | `fulfillments` UPDATE | Assign technician + dispatch_id |
| `update_installation_status` | `(appointment_id, status, notes, issues)` | None (simulated) | Update install progress |
| `complete_installation` | `(appointment_id, order_id, equipment_installed, tests_passed, ...)` | `fulfillments` UPDATE→installed | Mark installation complete |

### Activation Tools (activation_tools.py) — LIFECYCLE CAPSTONE

| Tool | Signature | Tables | Purpose |
|------|-----------|--------|---------|
| `activate_service` | `(order_id, service_type, circuit_id)` | `fulfillments`, `customer_master`, `accounts`, `orders` | **Full lifecycle completion** |
| `run_service_tests` | `(circuit_id, test_types)` | None (simulated) | Run service quality tests |
| `get_service_details` | `(circuit_id, account_id)` | None (simulated) | Get active service details |

### The Activation Capstone (`_update_fulfillment_activation`)

This is the most important cross-table operation in the system. When `activate_service` is called:

1. **Updates `fulfillments`** — sets activation_id, circuit_id, account_id, status → `activated`
2. **Inserts `customer_master`** — creates the official customer record
3. **Updates `accounts`** — sets `Existing Customer` → `Y`
4. **Updates `orders`** — sets status → `fulfilled`

This is the only point where a prospect becomes a customer.

### Fulfillment State Machine

```
scheduled → dispatched → installed → activated
```

### Cross-Agent Notifications
- `INSTALL_SCHEDULED` — on schedule_installation
- `INSTALL_DISPATCHED` — on dispatch_technician
- `INSTALL_COMPLETE` — on complete_installation
- `SERVICE_ACTIVATED` — on activate_service

---

## Conversation Behavior

### When Invoked
SuperAgent routes to ServiceFulfillmentAgent for: "Schedule installation", "Activate service", "When can you install?"

### Response Pattern
> "✅ Installation scheduled for Feb 20, 9:00 AM - 12:00 PM. Appointment ID: APT-12345."

---

## Integration with SuperAgent

Loaded via **importlib isolation** in `SuperAgent/super_agent/sub_agents/service_fulfillment/agent.py`. Agent name `service_fulfillment_agent` is hardcoded.
