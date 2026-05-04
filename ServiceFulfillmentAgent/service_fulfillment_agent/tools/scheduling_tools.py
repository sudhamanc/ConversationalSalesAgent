"""
Scheduling tools for the Service Fulfillment Agent.

These tools handle appointment scheduling, availability checking,
and calendar management for installations.
"""

import json
import os
import sqlite3
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
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


def check_availability(
    service_address: str,
    service_type: str,
    start_date: Optional[str] = None,
    num_days: int = 7
) -> Dict[str, Any]:
    """
    Checks available installation time slots.
    
    For production: Integrates with scheduling system API
    For testing: Simulates availability based on business rules
    
    Args:
        service_address: Installation address
        service_type: Type of service to be installed
        start_date: Start date to check (ISO format), defaults to tomorrow
        num_days: Number of days to check for availability
    
    Returns:
        Available time slots
    """
    logger.info(f"Checking availability for {service_address}")
    
    try:
        # Parse or set start date
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.now() + timedelta(days=1)
        
        # Simulate checking availability
        # In production: Call scheduling system API
        
        available_slots = []
        current_date = start
        
        for day in range(num_days):
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:  # Monday-Friday
                # Simulate some slots being available
                # AM slot usually available
                if current_date.weekday() not in [2]:  # Not Wednesday AM
                    available_slots.append({
                        "date": current_date.strftime("%Y-%m-%d"),
                        "window": "AM",
                        "start_time": "08:00",
                        "end_time": "12:00",
                        "available_technicians": 3
                    })
                
                # PM slot availability varies
                if current_date.weekday() not in [1, 3]:  # Not Tuesday or Thursday PM
                    available_slots.append({
                        "date": current_date.strftime("%Y-%m-%d"),
                        "window": "PM",
                        "start_time": "13:00",
                        "end_time": "17:00",
                        "available_technicians": 2
                    })
            
            current_date += timedelta(days=1)
        
        return {
            "success": True,
            "service_address": service_address,
            "service_type": service_type,
            "available_slots": available_slots,
            "total_slots": len(available_slots),
            "message": f"Found {len(available_slots)} available installation windows"
        }
    
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        return {
            "success": False,
            "error": f"Availability check error: {str(e)}"
        }


def schedule_installation(
    service_address: str,
    scheduled_date: str,
    window: str,
    order_id: Optional[str] = None,
    cart_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_contact: Optional[str] = None,
    customer_phone: Optional[str] = None,
    special_instructions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Schedules an installation appointment.
    
    Supports both PRE-ORDER scheduling (cart_id, no order_id yet) and 
    POST-ORDER scheduling (order_id exists).
    
    Args:
        service_address: Installation address (REQUIRED)
        scheduled_date: Date for installation (YYYY-MM-DD) (REQUIRED)
        window: Time window ('AM' or 'PM') (REQUIRED)
        order_id: Order identifier (optional - for post-order scheduling)
        cart_id: Cart identifier (optional - for pre-order scheduling)
        customer_id: Customer identifier (optional - for linking fulfillment to customer)
        customer_name: Customer/company name (optional)
        customer_contact: On-site contact name (optional, defaults to customer_name)
        customer_phone: Contact phone number (optional, defaults to placeholder)
        special_instructions: Special notes for technician (optional)
    
    Returns:
        Appointment details
    """
    # Use cart_id or order_id for reference
    reference_id = order_id or cart_id or "PENDING"
    logger.info(f"Scheduling installation for reference {reference_id}")
    
    try:
        # Validate inputs
        if window not in ['AM', 'PM', 'all_day']:
            return {
                "success": False,
                "error": "Window must be 'AM', 'PM', or 'all_day'"
            }
        
        # Parse date
        appt_date = datetime.strptime(scheduled_date, "%Y-%m-%d")
        
        # Check if date is in the past
        if appt_date < datetime.now():
            return {
                "success": False,
                "error": "Cannot schedule installation in the past"
            }
        
        # Check if date is a weekend
        if appt_date.weekday() >= 5:
            return {
                "success": False,
                "error": "Installations are only available Monday-Friday"
            }
        
        # Generate appointment ID
        appointment_id = f"APT-{appt_date.strftime('%Y%m%d')}-{hash(reference_id) % 1000:03d}"
        
        # Determine time range
        if window == 'AM':
            start_time = "08:00"
            end_time = "12:00"
        elif window == 'PM':
            start_time = "13:00"
            end_time = "17:00"
        else:  # all_day
            start_time = "08:00"
            end_time = "17:00"
        
        # Use defaults for optional contact info
        contact_name = customer_contact or customer_name or "On-site representative"
        contact_phone = customer_phone or "To be confirmed"
        
        appointment = {
            "success": True,
            "appointment_id": appointment_id,
            "order_id": order_id,
            "cart_id": cart_id,
            "reference_id": reference_id,
            "service_address": service_address,
            "scheduled_date": scheduled_date,
            "window": window,
            "start_time": start_time,
            "end_time": end_time,
            "customer_name": customer_name,
            "customer_contact": contact_name,
            "customer_phone": contact_phone,
            "special_instructions": special_instructions,
            "status": "scheduled",
            "message": f"Installation scheduled for {scheduled_date} {window} ({start_time}-{end_time})"
        }
        
        logger.info(f"Appointment created: {appointment_id}")
        
        # Persist fulfillment record to unified DB
        _persist_fulfillment(
            fulfillment_id=appointment_id,
            order_id=order_id or "",
            customer_id=customer_id or "",
            appointment_date=scheduled_date,
            status="scheduled",
        )

        # Auto-send INSTALL_SCHEDULED notification
        # Look up customer email from orders table
        _notif_email = None
        _notif_customer_id = customer_id or ""
        _notif_customer_name = customer_name or ""
        if order_id:
            _notif_conn = _get_db_connection()
            if _notif_conn:
                try:
                    _row = _notif_conn.execute(
                        "SELECT customer_id, customer_name, contact_email FROM orders WHERE order_id = ?",
                        (order_id,),
                    ).fetchone()
                    if _row:
                        _notif_email = _row["contact_email"]
                        _notif_customer_id = _notif_customer_id or (_row["customer_id"] or "")
                        _notif_customer_name = _notif_customer_name or (_row["customer_name"] or "")
                except Exception:
                    pass
                finally:
                    _notif_conn.close()

        _auto_send_notification(
            notification_type="INSTALL_SCHEDULED",
            customer_id=_notif_customer_id,
            order_id=order_id or "",
            recipient_email=_notif_email,
            metadata={"appointment_id": appointment_id, "appointment_date": scheduled_date,
                       "window": window, "service_address": service_address,
                       "customer_name": _notif_customer_name},
        )

        return appointment
    
    except Exception as e:
        logger.error(f"Error scheduling installation: {e}")
        return {
            "success": False,
            "error": f"Scheduling error: {str(e)}"
        }


def reschedule_appointment(
    appointment_id: str,
    new_date: str,
    new_window: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reschedules an existing appointment.
    
    Args:
        appointment_id: Existing appointment ID
        new_date: New date (YYYY-MM-DD)
        new_window: New time window ('AM' or 'PM')
        reason: Reason for rescheduling
    
    Returns:
        Updated appointment details
    """
    logger.info(f"Rescheduling appointment {appointment_id}")
    
    try:
        # In production: Retrieve existing appointment and update
        
        # Validate new date
        appt_date = datetime.strptime(new_date, "%Y-%m-%d")
        
        if appt_date < datetime.now():
            return {
                "success": False,
                "error": "Cannot reschedule to a past date"
            }
        
        if appt_date.weekday() >= 5:
            return {
                "success": False,
                "error": "Installations are only available Monday-Friday"
            }
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "new_date": new_date,
            "new_window": new_window,
            "reason": reason,
            "status": "rescheduled",
            "message": f"Appointment rescheduled to {new_date} {new_window}"
        }
    
    except Exception as e:
        logger.error(f"Error rescheduling appointment: {e}")
        return {
            "success": False,
            "error": f"Rescheduling error: {str(e)}"
        }


def cancel_appointment(
    appointment_id: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cancels an installation appointment.
    
    Args:
        appointment_id: Appointment to cancel
        reason: Cancellation reason
    
    Returns:
        Cancellation confirmation
    """
    logger.info(f"Cancelling appointment {appointment_id}")
    
    try:
        # In production: Update appointment status in system
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "status": "cancelled",
            "reason": reason,
            "cancelled_at": datetime.now().isoformat(),
            "message": f"Appointment {appointment_id} has been cancelled"
        }
    
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        return {
            "success": False,
            "error": f"Cancellation error: {str(e)}"
        }


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------

def _persist_fulfillment(
    fulfillment_id: str,
    order_id: str,
    customer_id: str,
    appointment_date: str,
    status: str = "scheduled",
) -> None:
    """INSERT a new fulfillment record (best-effort)."""
    conn = _get_db_connection()
    if conn is None:
        return
    try:
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT OR REPLACE INTO fulfillments
               (fulfillment_id, order_id, customer_id, appointment_date,
                status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fulfillment_id, order_id, customer_id, appointment_date, status, now, now),
        )
        conn.commit()
        logger.info(f"Fulfillment {fulfillment_id} persisted: status={status}")
    except Exception as exc:
        logger.warning(f"Failed to persist fulfillment (non-fatal): {exc}")
    finally:
        conn.close()


def _auto_send_notification(
    notification_type: str,
    customer_id: str,
    order_id: str,
    recipient_email: str | None,
    metadata: dict,
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
        elif notification_type == "INSTALL_SCHEDULED" and hasattr(comms, "send_install_scheduled_notification"):
            comms.send_install_scheduled_notification(
                order_id=order_id,
                customer_name=metadata.get("customer_name", customer_id),
                customer_email=recipient_email,
                appointment_date=metadata.get("appointment_date", ""),
                window=metadata.get("window", ""),
                service_address=metadata.get("service_address", ""),
            )
            logger.info(f"Auto-sent {notification_type} notification to {recipient_email}")
    except Exception as exc:
        logger.warning(f"Auto notification {notification_type} failed (non-fatal): {exc}")
