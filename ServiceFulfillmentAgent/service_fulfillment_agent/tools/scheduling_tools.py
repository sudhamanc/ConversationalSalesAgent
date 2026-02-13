"""
Scheduling tools for the Service Fulfillment Agent.

These tools handle appointment scheduling, availability checking,
and calendar management for installations.
"""

import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from ..utils.logger import get_logger

logger = get_logger(__name__)


def check_availability(
    service_address: str,
    service_type: str,
    start_date: str = None,
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
    order_id: str,
    service_address: str,
    scheduled_date: str,
    window: str,
    customer_contact: str,
    customer_phone: str,
    special_instructions: str = None
) -> Dict[str, Any]:
    """
    Schedules an installation appointment.
    
    Args:
        order_id: Order identifier
        service_address: Installation address
        scheduled_date: Date for installation (YYYY-MM-DD)
        window: Time window ('AM' or 'PM')
        customer_contact: On-site contact name
        customer_phone: Contact phone number
        special_instructions: Special notes for technician
    
    Returns:
        Appointment details
    """
    logger.info(f"Scheduling installation for order {order_id}")
    
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
        appointment_id = f"APT-{appt_date.strftime('%Y%m%d')}-{hash(order_id) % 1000:03d}"
        
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
        
        appointment = {
            "success": True,
            "appointment_id": appointment_id,
            "order_id": order_id,
            "service_address": service_address,
            "scheduled_date": scheduled_date,
            "window": window,
            "start_time": start_time,
            "end_time": end_time,
            "customer_contact": customer_contact,
            "customer_phone": customer_phone,
            "special_instructions": special_instructions,
            "status": "scheduled",
            "message": f"Installation scheduled for {scheduled_date} {window} ({start_time}-{end_time})"
        }
        
        logger.info(f"Appointment created: {appointment_id}")
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
    reason: str = None
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
    reason: str = None
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
