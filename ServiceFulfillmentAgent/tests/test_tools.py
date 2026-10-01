"""Tool tests. DB-backed tests run against TEST_DATABASE_URL after migrate.run(seed=True)."""

import json
from datetime import date, timedelta
from types import SimpleNamespace

from sales_common import db

from service_fulfillment_agent.tools.activation_tools import activate_service, get_service_details, run_service_tests
from service_fulfillment_agent.tools.equipment_tools import provision_equipment, track_equipment
from service_fulfillment_agent.tools.installation_tools import (
    complete_installation,
    dispatch_technician,
    update_installation_status,
)
from service_fulfillment_agent.tools.order_tools import get_fulfillment_status
from service_fulfillment_agent.tools.scheduling_tools import (
    cancel_appointment,
    check_availability,
    reschedule_appointment,
    schedule_installation,
)


def _notifications(order_id, notification_type):
    return db.fetch_all(
        "SELECT * FROM notifications WHERE order_id = %s AND notification_type = %s",
        (order_id, notification_type),
    )


# ---------------------------------------------------------------------------
# Simulated tools (no database)
# ---------------------------------------------------------------------------


def test_check_availability_rejects_past_start_date():
    past = check_availability("123 Main St, Philadelphia, PA 19107", "FIB-1G", start_date="2026-05-04")
    if date.today() > date(2026, 5, 4):
        assert past["success"] is False and "today is" in past["error"]
    today = check_availability("123 Main St, Philadelphia, PA 19107", "FIB-1G", start_date=date.today().isoformat())
    assert today["success"] is False
    ok = check_availability("123 Main St, Philadelphia, PA 19107", "FIB-1G",
                            start_date=(date.today() + timedelta(days=1)).isoformat())
    assert ok["success"] is True
    assert all(slot["date"] > date.today().isoformat() for slot in ok["available_slots"])


def test_check_availability_weekdays_only():
    result = check_availability("123 Main St, Philadelphia, PA 19107", "Business Fiber 1 Gbps")
    assert result["success"] is True
    assert result["available_slots"]
    for slot in result["available_slots"]:
        assert date.fromisoformat(slot["date"]).weekday() < 5


def test_schedule_validation_errors_do_not_touch_db():
    assert schedule_installation(scheduled_date="2026-01-01", window="AM", order_id="ORD-X")["success"] is False
    assert schedule_installation(scheduled_date="2099-01-05", window="EVENING", order_id="ORD-X")["success"] is False
    saturday = date.today() + timedelta(days=(5 - date.today().weekday()) % 7 or 7)
    result = schedule_installation(scheduled_date=saturday.isoformat(), window="AM", order_id="ORD-X")
    assert result == {"success": False, "error": "Installations are only available Monday-Friday"}


def test_schedule_requires_an_order():
    result = schedule_installation(scheduled_date="2099-01-05", window="AM",
                                   tool_context=SimpleNamespace(state={}))
    assert result["success"] is False
    assert "order" in result["error"].lower()


def test_provision_equipment_is_deterministic():
    first = provision_equipment(order_id="ORD-TEST-001", service_type="Business Fiber 1 Gbps")
    second = provision_equipment(order_id="ORD-TEST-001", service_type="Business Fiber 1 Gbps")
    assert first["success"] is True and len(first["equipment_items"]) == 2
    assert [i["tracking_number"] for i in first["equipment_items"]] == [
        i["tracking_number"] for i in second["equipment_items"]
    ]
    assert track_equipment(order_id="ORD-TEST-001")["success"] is True


def test_update_installation_status_and_service_tests():
    assert update_installation_status(appointment_id="APT-1", status="in_progress")["success"] is True
    assert update_installation_status(appointment_id="APT-1", status="bogus")["success"] is False
    tests = run_service_tests(circuit_id="CKT-TEST-001")
    assert tests["success"] is True and tests["all_tests_passed"] is True


# ---------------------------------------------------------------------------
# PostgreSQL-backed tools
# ---------------------------------------------------------------------------


def test_schedule_installation_persists_and_enqueues(order, tool_context, next_weekday):
    result = schedule_installation(scheduled_date=next_weekday, window="AM", tool_context=tool_context)

    assert result["success"] is True
    assert result["appointment_id"].startswith(f"APT-{next_weekday.replace('-', '')}-")
    assert result["fulfillment_id"] == result["appointment_id"]
    assert result["order_id"] == order["order_id"]
    assert result["customer_id"] == order["customer_id"]
    assert result["service_address"] == order["service_address"]
    assert (result["scheduled_date"], result["window"]) == (next_weekday, "AM")
    assert (result["start_time"], result["end_time"]) == ("08:00", "12:00")
    assert result["status"] == "scheduled"
    assert result["notification_queued"] is True
    json.dumps(result)  # JSON-serializable

    row = db.fetch_one("SELECT * FROM fulfillments WHERE fulfillment_id = %s", (result["appointment_id"],))
    assert row["order_id"] == order["order_id"]
    assert row["customer_id"] == order["customer_id"]
    assert row["appointment_date"] == next_weekday
    assert row["status"] == "scheduled"

    notes = _notifications(order["order_id"], "installation_scheduled")
    assert len(notes) == 1
    assert notes[0]["status"] == "pending"
    assert notes[0]["recipient_email"] == "buyer@example.com"
    args = json.loads(notes[0]["metadata_json"])["args"]
    assert args["appointment_id"] == result["appointment_id"]
    assert args["appointment_date"] == next_weekday and args["window"] == "AM"

    # order_context gains the installation; status stays pending_payment for the payment handoff.
    ctx = tool_context.state["order_context"]
    assert ctx["status"] == "pending_payment"
    assert ctx["installation"]["appointment_id"] == result["appointment_id"]

    # Order row itself is not changed by scheduling.
    assert db.fetch_one("SELECT status FROM orders WHERE order_id = %s", (order["order_id"],))["status"] == "pending_payment"


def test_schedule_installation_rebooking_reuses_appointment(order, tool_context, next_weekday):
    first = schedule_installation(scheduled_date=next_weekday, window="AM", tool_context=tool_context)
    later = date.fromisoformat(next_weekday) + timedelta(days=7)
    second = schedule_installation(scheduled_date=later.isoformat(), window="PM",
                                   order_id=order["order_id"])
    assert second["success"] is True
    assert second["appointment_id"] == first["appointment_id"]
    rows = db.fetch_all("SELECT * FROM fulfillments WHERE order_id = %s", (order["order_id"],))
    assert len(rows) == 1 and rows[0]["appointment_date"] == later.isoformat()


def test_schedule_installation_unknown_order(migrated_db, next_weekday):
    result = schedule_installation(scheduled_date=next_weekday, window="PM", order_id="ORD-DOES-NOT-EXIST")
    assert result == {"success": False, "error": "Order ORD-DOES-NOT-EXIST not found"}


def test_reschedule_and_cancel(order, tool_context, next_weekday):
    appt = schedule_installation(scheduled_date=next_weekday, window="AM", tool_context=tool_context)
    later = (date.fromisoformat(next_weekday) + timedelta(days=7)).isoformat()
    moved = reschedule_appointment(appointment_id=appt["appointment_id"], new_date=later, new_window="PM",
                                   tool_context=tool_context)
    assert moved["success"] is True and moved["previous_date"] == next_weekday
    assert tool_context.state["order_context"]["installation"]["window"] == "PM"
    cancelled = cancel_appointment(appointment_id=appt["appointment_id"], reason="customer request")
    assert cancelled["success"] is True
    row = db.fetch_one("SELECT status FROM fulfillments WHERE fulfillment_id = %s", (appt["appointment_id"],))
    assert row["status"] == "cancelled"
    assert cancel_appointment(appointment_id="APT-NOPE")["success"] is False


def test_dispatch_and_complete_installation(order, tool_context, next_weekday):
    appt = schedule_installation(scheduled_date=next_weekday, window="AM", tool_context=tool_context)
    # appointment_id/order_id default from order_context.installation
    dispatch = dispatch_technician(tool_context=tool_context)
    assert dispatch["success"] is True
    assert dispatch["appointment_id"] == appt["appointment_id"]
    assert dispatch["scheduled_date"] == next_weekday
    row = db.fetch_one("SELECT status, dispatch_id FROM fulfillments WHERE fulfillment_id = %s",
                       (appt["appointment_id"],))
    assert row["status"] == "dispatched" and row["dispatch_id"] == dispatch["dispatch_id"]

    done = complete_installation(equipment_installed=["EQ-1", "EQ-2"], appointment_id=appt["appointment_id"],
                                 order_id=order["order_id"])
    assert done["success"] is True and done["notification_queued"] is True
    row = db.fetch_one("SELECT status FROM fulfillments WHERE fulfillment_id = %s", (appt["appointment_id"],))
    assert row["status"] == "installed"
    assert len(_notifications(order["order_id"], "installation_complete")) == 1
    assert dispatch_technician(appointment_id="APT-NOPE", order_id="ORD-NOPE")["success"] is False


def test_dispatch_technician_enqueues_install_dispatched(order, tool_context, next_weekday):
    schedule_installation(scheduled_date=next_weekday, window="AM", tool_context=tool_context)
    dispatch = dispatch_technician(tool_context=tool_context)
    assert dispatch["success"] is True and dispatch["notification_queued"] is True
    rows = _notifications(order["order_id"], "install_dispatched")
    assert len(rows) == 1
    row = rows[0]
    assert row["recipient_email"] == "buyer@example.com"
    assert row["customer_id"] == order["customer_id"] and row["status"] == "pending"
    meta = json.loads(row["metadata_json"])
    assert meta["template"] == "install_dispatched"
    assert meta["args"] == {
        "order_id": order["order_id"],
        "customer_name": order["customer_name"],
        "technician_name": dispatch["technician_name"],
        "technician_phone": dispatch["technician_phone"],
    }
    # Re-dispatching the same appointment does not notify again.
    again = dispatch_technician(tool_context=tool_context)
    assert again["success"] is True and again["notification_queued"] is False
    assert len(_notifications(order["order_id"], "install_dispatched")) == 1


def test_dispatch_technician_email_fallback_and_no_recipient(order, tool_context, next_weekday):
    schedule_installation(scheduled_date=next_weekday, window="PM", tool_context=tool_context)
    db.execute("UPDATE orders SET contact_email = NULL WHERE order_id = %s", (order["order_id"],))

    # No order email and no customer_master row: dispatch succeeds without a notification.
    no_recipient = dispatch_technician(order_id=order["order_id"])
    assert no_recipient["success"] is True and no_recipient["notification_queued"] is False
    assert _notifications(order["order_id"], "install_dispatched") == []

    # With a customer_master contact email, the next first-time dispatch uses it.
    db.execute("UPDATE fulfillments SET status = 'scheduled' WHERE order_id = %s", (order["order_id"],))
    now = db.now_iso()
    db.execute(
        "INSERT INTO customer_master (customer_id, company_name, street, city, state, zip_code, "
        "contact_email, activated_at, created_at, updated_at) "
        "VALUES (%s, %s, '8265 Broadway', 'Portland', 'OR', '97201', 'master@example.com', %s, %s, %s)",
        (order["customer_id"], order["customer_name"], now, now, now),
    )
    dispatch = dispatch_technician(order_id=order["order_id"])
    assert dispatch["notification_queued"] is True
    rows = _notifications(order["order_id"], "install_dispatched")
    assert [r["recipient_email"] for r in rows] == ["master@example.com"]


def test_activate_service_converts_prospect_to_customer(order, tool_context, next_weekday):
    appt = schedule_installation(scheduled_date=next_weekday, window="AM", tool_context=tool_context)
    result = activate_service(tool_context=tool_context)  # order_id/service_type from order_context

    assert result["success"] is True
    assert result["order_id"] == order["order_id"]
    assert result["service_type"] == "Business Fiber 1 Gbps"
    assert result["customer_master_created"] is True
    assert result["technology"] == "FTTP"

    f = db.fetch_one("SELECT * FROM fulfillments WHERE fulfillment_id = %s", (appt["appointment_id"],))
    assert f["status"] == "activated"
    assert (f["circuit_id"], f["account_id"], f["activation_id"]) == (
        result["circuit_id"], result["account_id"], result["activation_id"])

    cm = db.fetch_one("SELECT * FROM customer_master WHERE customer_id = %s", (order["customer_id"],))
    assert cm["company_name"] == order["customer_name"]
    assert (cm["street"], cm["city"], cm["state"], cm["zip_code"]) == ("8265 Broadway", "Portland", "OR", "97201")
    assert cm["first_order_id"] == order["order_id"]
    assert cm["circuit_id"] == result["circuit_id"]
    assert json.loads(cm["contracted_products"]) == ["Business Fiber 1 Gbps"]
    assert cm["monthly_revenue"] == 249.99
    assert cm["contact_email"] == "buyer@example.com"

    acct = db.fetch_one('SELECT "Existing Customer", "Current Products" FROM accounts WHERE customer_id = %s',
                        (order["customer_id"],))
    assert acct["Existing Customer"] == "Y"
    assert acct["Current Products"] == "Voice, Business Fiber 1 Gbps"
    assert db.fetch_one("SELECT status FROM orders WHERE order_id = %s", (order["order_id"],))["status"] == "fulfilled"

    notes = _notifications(order["order_id"], "service_activated")
    assert len(notes) == 1
    assert json.loads(notes[0]["metadata_json"])["args"]["circuit_id"] == result["circuit_id"]

    ctx = tool_context.state["order_context"]
    assert ctx["status"] == "fulfilled"
    assert ctx["activation"]["circuit_id"] == result["circuit_id"]
    assert ctx["installation"]["status"] == "activated"

    # Idempotent: a second activation returns the same ids and does not re-notify.
    again = activate_service(order_id=order["order_id"], service_type="Business Fiber 1 Gbps")
    assert again["already_active"] is True and again["circuit_id"] == result["circuit_id"]
    assert len(_notifications(order["order_id"], "service_activated")) == 1

    details = get_service_details(circuit_id=result["circuit_id"])
    assert details["success"] is True and details["order_id"] == order["order_id"]

    status = get_fulfillment_status(order_id=order["order_id"])
    assert status["fulfillment_status"] == "activated" and status["order_status"] == "fulfilled"
    assert all(stage["completed"] for stage in status["status_stages"])


def test_activate_service_without_appointment_records_fulfillment(order):
    result = activate_service(order_id=order["order_id"], service_type="Business Fiber 1 Gbps")
    assert result["success"] is True
    rows = db.fetch_all("SELECT * FROM fulfillments WHERE order_id = %s", (order["order_id"],))
    assert len(rows) == 1 and rows[0]["status"] == "activated"
    assert activate_service(order_id="ORD-DOES-NOT-EXIST", service_type="x")["success"] is False
