"""
Installation coordination tools for the Service Fulfillment Agent.

These tools handle technician dispatch, installation tracking, and completion.
"""

import json
import os
import sqlite3
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


def _get_db_connection():
    """Return a connection to the unified sales_agent.db, or None if not configured."""
    db_path = os.getenv("SALES_AGENT_DB_PATH")
    if not db_path:
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def dispatch_technician(
    appointment_id: str,
    order_id: str,
    scheduled_date: str
) -> Dict[str, Any]:
    """
    Dispatches a technician for an installation appointment.
    
    For production: Integrates with dispatch management system
    For testing: Simulates technician assignment
    
    Args:
        appointment_id: Appointment identifier
        order_id: Order identifier
        scheduled_date: Scheduled installation date
    
    Returns:
        Dispatch details with technician information
    """
    logger.info(f"Dispatching technician for appointment {appointment_id}")
    
    try:
        # Simulate technician assignment
        # In production: Call dispatch management system API
        
        # Generate dispatch ID
        dispatch_id = f"DISP-{appointment_id.split('-')[-1]}"
        
        # Assign technician (simulated)
        technicians = [
            {"id": "TECH-101", "name": "Mike Johnson", "phone": "555-0101"},
            {"id": "TECH-102", "name": "Sarah Williams", "phone": "555-0102"},
            {"id": "TECH-103", "name": "David Brown", "phone": "555-0103"},
        ]
        
        # Select technician based on appointment ID hash
        tech_idx = hash(appointment_id) % len(technicians)
        assigned_tech = technicians[tech_idx]
        
        dispatch = {
            "success": True,
            "dispatch_id": dispatch_id,
            "appointment_id": appointment_id,
            "order_id": order_id,
            "technician_id": assigned_tech["id"],
            "technician_name": assigned_tech["name"],
            "technician_phone": assigned_tech["phone"],
            "vehicle_id": f"VEH-{assigned_tech['id'].split('-')[1]}",
            "scheduled_date": scheduled_date,
            "dispatched_at": datetime.now().isoformat(),
            "status": "dispatched",
            "message": f"Technician {assigned_tech['name']} assigned and dispatched"
        }
        
        logger.info(f"Technician dispatched: {assigned_tech['name']}")
        
        # Update fulfillment record in unified DB
        _update_fulfillment(appointment_id, dispatch_id=dispatch_id, status="dispatched")

        # Auto-send INSTALL_DISPATCHED notification
        _auto_send_notification(
            notification_type="INSTALL_DISPATCHED",
            order_id=order_id,
            metadata={"appointment_id": appointment_id, "dispatch_id": dispatch_id,
                       "technician_name": assigned_tech["name"],
                       "technician_phone": assigned_tech["phone"]},
        )

        return dispatch
    
    except Exception as e:
        logger.error(f"Error dispatching technician: {e}")
        return {
            "success": False,
            "error": f"Technician dispatch error: {str(e)}"
        }


def update_installation_status(
    appointment_id: str,
    status: str,
    notes: str = None,
    issues: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Updates the status of an ongoing installation.
    
    Args:
        appointment_id: Appointment identifier
        status: New status (technician_en_route, on_site, in_progress, testing, complete, failed)
        notes: Optional status notes
        issues: Optional list of issues encountered
    
    Returns:
        Updated installation status
    """
    logger.info(f"Updating installation status for {appointment_id}: {status}")
    
    try:
        valid_statuses = [
            "scheduled",
            "technician_en_route",
            "on_site",
            "in_progress",
            "testing",
            "complete",
            "failed"
        ]
        
        if status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }
        
        # Simulate status update
        # In production: Update installation tracking system
        
        status_update = {
            "success": True,
            "appointment_id": appointment_id,
            "status": status,
            "updated_at": datetime.now().isoformat(),
            "notes": notes,
            "issues": issues or [],
            "message": f"Installation status updated to: {status}"
        }
        
        logger.info(f"Status updated: {status}")
        return status_update
    
    except Exception as e:
        logger.error(f"Error updating installation status: {e}")
        return {
            "success": False,
            "error": f"Status update error: {str(e)}"
        }


def complete_installation(
    appointment_id: str,
    order_id: str,
    equipment_installed: List[str],
    tests_passed: bool = True,
    customer_signature: str = None,
    notes: str = None
) -> Dict[str, Any]:
    """
    Completes an installation and marks it as finished.
    
    Args:
        appointment_id: Appointment identifier
        order_id: Order identifier
        equipment_installed: List of equipment IDs installed
        tests_passed: Whether all service tests passed
        customer_signature: Customer signature (name or digital signature)
        notes: Completion notes
    
    Returns:
        Installation completion record
    """
    logger.info(f"Completing installation for appointment {appointment_id}")
    
    try:
        if not tests_passed:
            return {
                "success": False,
                "error": "Cannot complete installation - service tests failed. Please resolve issues first."
            }
        
        # Generate completion record
        completion = {
            "success": True,
            "appointment_id": appointment_id,
            "order_id": order_id,
            "status": "installation_complete",
            "completed_at": datetime.now().isoformat(),
            "equipment_installed": equipment_installed,
            "tests_passed": tests_passed,
            "customer_signature": customer_signature,
            "notes": notes,
            "next_steps": [
                "Service activation initiated",
                "Customer portal access will be emailed",
                "Billing will begin on next cycle"
            ],
            "message": "Installation completed successfully"
        }
        
        logger.info(f"Installation completed: {appointment_id}")
        
        # Update fulfillment record in unified DB
        _update_fulfillment(appointment_id, status="installed")

        # Auto-send INSTALL_COMPLETE notification
        _auto_send_notification(
            notification_type="INSTALL_COMPLETE",
            order_id=order_id,
            metadata={"appointment_id": appointment_id,
                       "equipment_installed": equipment_installed},
        )

        return completion
    
    except Exception as e:
        logger.error(f"Error completing installation: {e}")
        return {
            "success": False,
            "error": f"Installation completion error: {str(e)}"
        }


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------

def _update_fulfillment(
    fulfillment_id: str,
    dispatch_id: str | None = None,
    status: str | None = None,
) -> None:
    """Update a fulfillment record in the unified DB (best-effort)."""
    conn = _get_db_connection()
    if conn is None:
        return
    try:
        now = datetime.now().isoformat()
        sets = ["updated_at = ?"]
        params: list = [now]
        if dispatch_id is not None:
            sets.append("dispatch_id = ?")
            params.append(dispatch_id)
        if status is not None:
            sets.append("status = ?")
            params.append(status)
        params.append(fulfillment_id)
        conn.execute(
            f"UPDATE fulfillments SET {', '.join(sets)} WHERE fulfillment_id = ?",
            params,
        )
        conn.commit()
        logger.info(f"Fulfillment {fulfillment_id} updated: status={status}")
    except Exception as exc:
        logger.warning(f"Failed to update fulfillment (non-fatal): {exc}")
    finally:
        conn.close()


def _auto_send_notification(
    notification_type: str,
    order_id: str,
    metadata: dict,
    customer_id: str = "",
    recipient_email: str | None = None,
) -> None:
    """Send a notification via sys.modules dispatcher (best-effort, non-fatal)."""
    try:
        comms = sys.modules.get("customer_communication_agent.tools.notification_tools")
        if comms is None:
            return
        if hasattr(comms, "send_notification"):
            comms.send_notification(
                notification_type=notification_type,
                customer_id=customer_id,
                order_id=order_id,
                recipient_email=recipient_email,
                metadata=metadata,
            )
            logger.info(f"Auto-sent {notification_type} notification")
        elif notification_type == "INSTALL_DISPATCHED" and hasattr(comms, "send_install_dispatched_notification"):
            comms.send_install_dispatched_notification(
                order_id=order_id,
                customer_name=customer_id,
                customer_email=recipient_email,
                technician_name=metadata.get("technician_name", ""),
                technician_phone=metadata.get("technician_phone", ""),
            )
            logger.info(f"Auto-sent {notification_type} notification")
        elif notification_type == "INSTALL_COMPLETE" and hasattr(comms, "send_install_complete_notification"):
            comms.send_install_complete_notification(
                order_id=order_id,
                customer_name=customer_id,
                customer_email=recipient_email,
                equipment_installed=metadata.get("equipment_installed"),
            )
            logger.info(f"Auto-sent {notification_type} notification")
    except Exception as exc:
        logger.warning(f"Auto notification {notification_type} failed (non-fatal): {exc}")
