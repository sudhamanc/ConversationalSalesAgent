"""Scheduling tools: availability, booking, rescheduling and cancelling installations.

``schedule_installation`` persists a ``fulfillments`` row (status ``scheduled``)
and enqueues an ``installation_scheduled`` notification in the same PostgreSQL
transaction. The gateway hands off to ``payment_agent`` when this tool returns
``success == True``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

import psycopg
from google.adk.tools.tool_context import ToolContext

from sales_common import db, notifications

from ._common import find_fulfillment, get_order, state_dict, state_order_id, update_order_context

logger = logging.getLogger(__name__)

WINDOWS = {
    "AM": ("08:00", "12:00"),
    "PM": ("13:00", "17:00"),
    "all_day": ("08:00", "17:00"),
}


def _validate_date(value: str) -> tuple[Optional[datetime], Optional[str]]:
    try:
        appt_date = datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None, "Date must be in YYYY-MM-DD format"
    if appt_date < datetime.now():
        return None, "Cannot schedule installation in the past"
    if appt_date.weekday() >= 5:
        return None, "Installations are only available Monday-Friday"
    return appt_date, None


def check_availability(
    service_address: str,
    service_type: str,
    start_date: Optional[str] = None,
    num_days: int = 7,
) -> dict[str, Any]:
    """Checks available installation time slots (simulated business rules).

    Args:
        service_address: Installation address
        service_type: Type of service to be installed
        start_date: Start date to check (ISO format, tomorrow or later), defaults to tomorrow
        num_days: Number of days to check for availability

    Returns:
        Available time slots
    """
    logger.info("Checking availability for %s", service_address)
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        start = datetime.fromisoformat(start_date) if start_date else tomorrow
    except ValueError:
        return {"success": False, "error": "start_date must be an ISO date (YYYY-MM-DD)"}
    if start < tomorrow:
        return {
            "success": False,
            "error": f"start_date {start_date} is not in the future; today is {datetime.now().date().isoformat()}. "
            f"The earliest bookable date is {tomorrow.date().isoformat()} (omit start_date to start there).",
        }

    available_slots = []
    current_date = start
    for _ in range(max(0, min(int(num_days), 60))):
        if current_date.weekday() < 5:  # Monday-Friday
            if current_date.weekday() != 2:  # no Wednesday AM
                available_slots.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "window": "AM",
                    "start_time": "08:00",
                    "end_time": "12:00",
                    "available_technicians": 3,
                })
            if current_date.weekday() not in (1, 3):  # no Tuesday/Thursday PM
                available_slots.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "window": "PM",
                    "start_time": "13:00",
                    "end_time": "17:00",
                    "available_technicians": 2,
                })
        current_date += timedelta(days=1)

    return {
        "success": True,
        "service_address": service_address,
        "service_type": service_type,
        "available_slots": available_slots,
        "total_slots": len(available_slots),
        "message": f"Found {len(available_slots)} available installation windows",
    }


def schedule_installation(
    scheduled_date: str,
    window: str,
    service_address: Optional[str] = None,
    order_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_contact: Optional[str] = None,
    customer_phone: Optional[str] = None,
    special_instructions: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Schedules an installation appointment for an existing order.

    order_id, service_address, customer_id and customer_name default to the
    values in the journey order_context when not passed.

    Args:
        scheduled_date: Date for installation (YYYY-MM-DD) (REQUIRED)
        window: Time window ('AM', 'PM' or 'all_day') (REQUIRED)
        service_address: Installation address
        order_id: Order identifier (e.g. ORD-XXXXXXXX-XXX)
        customer_id: Customer identifier
        customer_name: Customer/company name
        customer_contact: On-site contact name (optional, defaults to customer_name)
        customer_phone: Contact phone number (optional)
        special_instructions: Special notes for technician (optional)

    Returns:
        Appointment details with success, appointment_id, scheduled_date, window.
    """
    order_ctx = state_dict(tool_context, "order_context")
    order_id = (order_id or "").strip() or state_order_id(tool_context)
    if not order_id:
        return {
            "success": False,
            "error": "No order found to schedule. An order must be created before installation can be scheduled.",
        }
    if window not in WINDOWS:
        return {"success": False, "error": "Window must be 'AM', 'PM', or 'all_day'"}
    _, date_error = _validate_date(scheduled_date)
    if date_error:
        return {"success": False, "error": date_error}
    start_time, end_time = WINDOWS[window]

    try:
        with db.transaction() as conn:
            order = get_order(conn, order_id)
            if order is None:
                return {"success": False, "error": f"Order {order_id} not found"}
            if order["status"] in ("cancelled", "fulfilled"):
                return {
                    "success": False,
                    "error": f"Order {order_id} is {order['status']}; installation cannot be scheduled",
                }

            service_address = (
                service_address or order_ctx.get("service_address") or order["service_address"]
            )
            customer_id = customer_id or order["customer_id"]
            customer_name = customer_name or order_ctx.get("customer_name") or order["customer_name"]
            now = db.now_iso()

            existing = find_fulfillment(conn, order_id=order_id, for_update=True)
            if existing and existing["status"] in ("scheduled", "dispatched"):
                # Idempotent re-booking for the same order: move the open appointment.
                appointment_id = existing["fulfillment_id"]
                conn.execute(
                    "UPDATE fulfillments SET appointment_date = %s, updated_at = %s "
                    "WHERE fulfillment_id = %s",
                    (scheduled_date, now, appointment_id),
                )
            else:
                appointment_id = (
                    f"APT-{scheduled_date.replace('-', '')}-{uuid.uuid4().hex[:6].upper()}"
                )
                conn.execute(
                    "INSERT INTO fulfillments (fulfillment_id, order_id, customer_id, "
                    "appointment_date, status, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, 'scheduled', %s, %s)",
                    (appointment_id, order_id, customer_id, scheduled_date, now, now),
                )

            notification_id = notifications.enqueue(
                "installation_scheduled",
                recipient_email=order["contact_email"],
                customer_id=customer_id,
                order_id=order_id,
                args={
                    "order_id": order_id,
                    "appointment_id": appointment_id,
                    "customer_name": customer_name,
                    "appointment_date": scheduled_date,
                    "window": window,
                    "start_time": start_time,
                    "end_time": end_time,
                    "service_address": service_address,
                },
                conn=conn,
            )
    except psycopg.Error as exc:
        logger.error("Scheduling failed for order %s: %s", order_id, exc)
        return {"success": False, "error": f"Scheduling error: {type(exc).__name__}"}

    installation = {
        "appointment_id": appointment_id,
        "scheduled_date": scheduled_date,
        "window": window,
        "start_time": start_time,
        "end_time": end_time,
        "status": "scheduled",
    }
    update_order_context(tool_context, order_id, installation=installation)
    logger.info("Appointment %s scheduled for order %s on %s %s", appointment_id, order_id, scheduled_date, window)

    return {
        "success": True,
        "appointment_id": appointment_id,
        "fulfillment_id": appointment_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "service_address": service_address,
        "scheduled_date": scheduled_date,
        "window": window,
        "start_time": start_time,
        "end_time": end_time,
        "customer_contact": customer_contact or customer_name or "On-site representative",
        "customer_phone": customer_phone or "To be confirmed",
        "special_instructions": special_instructions,
        "status": "scheduled",
        "notification_queued": notification_id is not None,
        "message": f"Installation scheduled for {scheduled_date} {window} ({start_time}-{end_time})",
    }


def reschedule_appointment(
    appointment_id: str,
    new_date: str,
    new_window: str,
    reason: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Reschedules an existing installation appointment.

    Args:
        appointment_id: Existing appointment ID (APT-...)
        new_date: New date (YYYY-MM-DD)
        new_window: New time window ('AM', 'PM' or 'all_day')
        reason: Reason for rescheduling

    Returns:
        Updated appointment details
    """
    if new_window not in WINDOWS:
        return {"success": False, "error": "Window must be 'AM', 'PM', or 'all_day'"}
    _, date_error = _validate_date(new_date)
    if date_error:
        return {"success": False, "error": date_error.replace("schedule", "reschedule")}
    try:
        with db.transaction() as conn:
            row = find_fulfillment(conn, appointment_id, state_order_id(tool_context), for_update=True)
            if row is None:
                return {"success": False, "error": f"Appointment {appointment_id} not found"}
            if row["status"] not in ("scheduled", "dispatched"):
                return {
                    "success": False,
                    "error": f"Appointment {row['fulfillment_id']} is {row['status']} and cannot be rescheduled",
                }
            conn.execute(
                "UPDATE fulfillments SET appointment_date = %s, updated_at = %s WHERE fulfillment_id = %s",
                (new_date, db.now_iso(), row["fulfillment_id"]),
            )
    except psycopg.Error as exc:
        logger.error("Reschedule failed for %s: %s", appointment_id, exc)
        return {"success": False, "error": f"Rescheduling error: {type(exc).__name__}"}

    start_time, end_time = WINDOWS[new_window]
    update_order_context(
        tool_context,
        row["order_id"],
        installation={
            "appointment_id": row["fulfillment_id"],
            "scheduled_date": new_date,
            "window": new_window,
            "start_time": start_time,
            "end_time": end_time,
            "status": row["status"],
        },
    )
    return {
        "success": True,
        "appointment_id": row["fulfillment_id"],
        "order_id": row["order_id"],
        "previous_date": row["appointment_date"],
        "new_date": new_date,
        "new_window": new_window,
        "start_time": start_time,
        "end_time": end_time,
        "reason": reason,
        "status": "rescheduled",
        "message": f"Appointment rescheduled to {new_date} {new_window}",
    }


def cancel_appointment(
    appointment_id: str,
    reason: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Cancels an installation appointment.

    Args:
        appointment_id: Appointment to cancel (APT-...)
        reason: Cancellation reason

    Returns:
        Cancellation confirmation
    """
    now = db.now_iso()
    try:
        with db.transaction() as conn:
            row = find_fulfillment(conn, appointment_id, state_order_id(tool_context), for_update=True)
            if row is None:
                return {"success": False, "error": f"Appointment {appointment_id} not found"}
            if row["status"] not in ("scheduled", "dispatched"):
                return {
                    "success": False,
                    "error": f"Appointment {row['fulfillment_id']} is {row['status']} and cannot be cancelled",
                }
            conn.execute(
                "UPDATE fulfillments SET status = 'cancelled', updated_at = %s WHERE fulfillment_id = %s",
                (now, row["fulfillment_id"]),
            )
    except psycopg.Error as exc:
        logger.error("Cancel failed for %s: %s", appointment_id, exc)
        return {"success": False, "error": f"Cancellation error: {type(exc).__name__}"}

    update_order_context(
        tool_context,
        row["order_id"],
        installation={"appointment_id": row["fulfillment_id"], "status": "cancelled"},
    )
    return {
        "success": True,
        "appointment_id": row["fulfillment_id"],
        "order_id": row["order_id"],
        "status": "cancelled",
        "reason": reason,
        "cancelled_at": now,
        "message": f"Appointment {row['fulfillment_id']} has been cancelled",
    }
