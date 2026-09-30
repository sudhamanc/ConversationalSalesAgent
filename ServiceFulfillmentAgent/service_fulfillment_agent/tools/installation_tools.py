"""Installation coordination tools: technician dispatch, progress and completion.

``dispatch_technician`` and ``complete_installation`` update the
``fulfillments`` row (``dispatched`` / ``installed``). ``complete_installation``
enqueues an ``installation_complete`` notification in the same transaction.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

import psycopg
from google.adk.tools.tool_context import ToolContext

from sales_common import db, notifications

from ._common import find_fulfillment, get_order, stable_number, state_dict, state_order_id, update_order_context

logger = logging.getLogger(__name__)

TECHNICIANS = [
    {"id": "TECH-101", "name": "Mike Johnson", "phone": "555-0101"},
    {"id": "TECH-102", "name": "Sarah Williams", "phone": "555-0102"},
    {"id": "TECH-103", "name": "David Brown", "phone": "555-0103"},
]

VALID_PROGRESS_STATUSES = [
    "scheduled",
    "technician_en_route",
    "on_site",
    "in_progress",
    "testing",
    "complete",
    "failed",
]


def _installation_from_state(tool_context) -> dict[str, Any]:
    installation = state_dict(tool_context, "order_context").get("installation")
    return installation if isinstance(installation, dict) else {}


def dispatch_technician(
    appointment_id: Optional[str] = None,
    order_id: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Dispatches a technician for a scheduled installation appointment.

    appointment_id, order_id and scheduled_date default to the journey
    order_context (installation booked earlier) when not passed.

    Args:
        appointment_id: Appointment identifier (APT-...)
        order_id: Order identifier
        scheduled_date: Scheduled installation date (YYYY-MM-DD)

    Returns:
        Dispatch details with technician information
    """
    installation = _installation_from_state(tool_context)
    appointment_id = appointment_id or installation.get("appointment_id")
    order_id = order_id or state_order_id(tool_context)
    if not appointment_id and not order_id:
        return {"success": False, "error": "appointment_id or order_id is required"}

    try:
        with db.transaction() as conn:
            row = find_fulfillment(conn, appointment_id, order_id, for_update=True)
            if row is None:
                return {
                    "success": False,
                    "error": f"No installation appointment found for {appointment_id or order_id}",
                }
            if row["status"] not in ("scheduled", "dispatched"):
                return {
                    "success": False,
                    "error": f"Appointment {row['fulfillment_id']} is {row['status']}; cannot dispatch",
                }
            appointment_id = row["fulfillment_id"]
            order_id = row["order_id"]
            scheduled_date = row["appointment_date"] or scheduled_date
            dispatch_id = row["dispatch_id"] or f"DISP-{appointment_id.split('-')[-1]}"
            conn.execute(
                "UPDATE fulfillments SET dispatch_id = %s, status = 'dispatched', updated_at = %s "
                "WHERE fulfillment_id = %s",
                (dispatch_id, db.now_iso(), appointment_id),
            )
    except psycopg.Error as exc:
        logger.error("Dispatch failed for %s: %s", appointment_id or order_id, exc)
        return {"success": False, "error": f"Technician dispatch error: {type(exc).__name__}"}

    tech = TECHNICIANS[stable_number(appointment_id, len(TECHNICIANS))]
    installation = {**installation, "appointment_id": appointment_id, "status": "dispatched",
                    "dispatch_id": dispatch_id, "technician_name": tech["name"]}
    if scheduled_date:
        installation["scheduled_date"] = scheduled_date
    update_order_context(tool_context, order_id, installation=installation)
    logger.info("Technician %s dispatched for %s", tech["name"], appointment_id)
    return {
        "success": True,
        "dispatch_id": dispatch_id,
        "appointment_id": appointment_id,
        "order_id": order_id,
        "technician_id": tech["id"],
        "technician_name": tech["name"],
        "technician_phone": tech["phone"],
        "vehicle_id": f"VEH-{tech['id'].split('-')[1]}",
        "scheduled_date": scheduled_date,
        "dispatched_at": db.now_iso(),
        "status": "dispatched",
        "message": f"Technician {tech['name']} assigned and dispatched",
    }


def update_installation_status(
    appointment_id: str,
    status: str,
    notes: Optional[str] = None,
    issues: Optional[List[str]] = None,
) -> dict[str, Any]:
    """Records progress of an ongoing installation (simulated field update).

    Args:
        appointment_id: Appointment identifier
        status: New status (technician_en_route, on_site, in_progress, testing, complete, failed)
        notes: Optional status notes
        issues: Optional list of issues encountered

    Returns:
        Updated installation status
    """
    if status not in VALID_PROGRESS_STATUSES:
        return {
            "success": False,
            "error": f"Invalid status. Must be one of: {', '.join(VALID_PROGRESS_STATUSES)}",
        }
    return {
        "success": True,
        "appointment_id": appointment_id,
        "status": status,
        "updated_at": db.now_iso(),
        "notes": notes,
        "issues": issues or [],
        "message": f"Installation status updated to: {status}",
    }


def complete_installation(
    equipment_installed: List[str],
    appointment_id: Optional[str] = None,
    order_id: Optional[str] = None,
    tests_passed: bool = True,
    customer_signature: Optional[str] = None,
    notes: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Completes an installation and marks it as installed.

    Args:
        equipment_installed: List of equipment IDs installed
        appointment_id: Appointment identifier (defaults to the booked appointment)
        order_id: Order identifier (defaults to the journey order)
        tests_passed: Whether all service tests passed
        customer_signature: Customer signature (name or digital signature)
        notes: Completion notes

    Returns:
        Installation completion record
    """
    if not tests_passed:
        return {
            "success": False,
            "error": "Cannot complete installation - service tests failed. Please resolve issues first.",
        }
    installation = _installation_from_state(tool_context)
    appointment_id = appointment_id or installation.get("appointment_id")
    order_id = order_id or state_order_id(tool_context)
    if not appointment_id and not order_id:
        return {"success": False, "error": "appointment_id or order_id is required"}

    completed_at = db.now_iso()
    try:
        with db.transaction() as conn:
            row = find_fulfillment(conn, appointment_id, order_id, for_update=True)
            if row is None:
                return {
                    "success": False,
                    "error": f"No installation appointment found for {appointment_id or order_id}",
                }
            if row["status"] not in ("scheduled", "dispatched", "installed"):
                return {
                    "success": False,
                    "error": f"Appointment {row['fulfillment_id']} is {row['status']}; cannot complete",
                }
            appointment_id = row["fulfillment_id"]
            order_id = row["order_id"]
            already_installed = row["status"] == "installed"
            notification_id = None
            if not already_installed:
                conn.execute(
                    "UPDATE fulfillments SET status = 'installed', updated_at = %s WHERE fulfillment_id = %s",
                    (completed_at, appointment_id),
                )
                order = get_order(conn, order_id) or {}
                notification_id = notifications.enqueue(
                    "installation_complete",
                    recipient_email=order.get("contact_email"),
                    customer_id=row["customer_id"],
                    order_id=order_id,
                    args={
                        "order_id": order_id,
                        "appointment_id": appointment_id,
                        "customer_name": order.get("customer_name") or "",
                        "equipment_installed": list(equipment_installed or []),
                        "completed_at": completed_at,
                    },
                    conn=conn,
                )
    except psycopg.Error as exc:
        logger.error("Completion failed for %s: %s", appointment_id or order_id, exc)
        return {"success": False, "error": f"Installation completion error: {type(exc).__name__}"}

    update_order_context(
        tool_context, order_id,
        installation={**installation, "appointment_id": appointment_id, "status": "installed"},
    )
    return {
        "success": True,
        "appointment_id": appointment_id,
        "order_id": order_id,
        "status": "installation_complete",
        "completed_at": completed_at,
        "equipment_installed": list(equipment_installed or []),
        "tests_passed": tests_passed,
        "customer_signature": customer_signature,
        "notes": notes,
        "notification_queued": notification_id is not None,
        "next_steps": [
            "Service activation initiated",
            "Customer portal access will be emailed",
            "Billing will begin on next cycle",
        ],
        "message": "Installation completed successfully",
    }
