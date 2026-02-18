"""
Order management tools for the Service Fulfillment Agent.

These tools handle order creation, status tracking, and updates.
"""

import json
from typing import Dict, Any
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


def create_order(
    customer_name: str,
    customer_id: str,
    service_address: str,
    service_type: str,
    contact_phone: str,
    contact_email: str = None
) -> Dict[str, Any]:
    """
    Creates a new service fulfillment order.
    
    Args:
        customer_name: Customer or business name
        customer_id: Customer identifier
        service_address: Installation address
        service_type: Type of service to be installed
        contact_phone: Customer contact phone
        contact_email: Customer contact email
    
    Returns:
        Created order details
    """
    logger.info(f"Creating order for customer {customer_name}")
    
    try:
        # Generate order ID
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{hash(customer_name) % 1000:03d}"
        
        order = {
            "success": True,
            "order_id": order_id,
            "customer_name": customer_name,
            "customer_id": customer_id,
            "service_address": service_address,
            "service_type": service_type,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "status": "received",
            "created_at": datetime.now().isoformat(),
            "expected_completion": None,  # Set after scheduling
            "message": f"Order {order_id} created successfully"
        }
        
        logger.info(f"Order created: {order_id}")
        return order
    
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return {
            "success": False,
            "error": f"Order creation error: {str(e)}"
        }


def get_order_status(order_id: str) -> Dict[str, Any]:
    """
    Retrieves the current status of an order.
    
    Args:
        order_id: Order identifier
    
    Returns:
        Order status and progress details
    """
    logger.info(f"Getting status for order {order_id}")
    
    try:
        # Simulate order status retrieval
        # In production: Query order management system
        
        # Generate sample status based on order ID
        # This would be replaced with actual database query
        
        status_stages = [
            {"stage": "order_received", "completed": True, "timestamp": (datetime.now()).isoformat()},
            {"stage": "scheduled", "completed": True, "timestamp": (datetime.now()).isoformat()},
            {"stage": "equipment_ordered", "completed": True, "timestamp": (datetime.now()).isoformat()},
            {"stage": "equipment_delivered", "completed": False, "timestamp": None},
            {"stage": "technician_dispatched", "completed": False, "timestamp": None},
            {"stage": "installation_complete", "completed": False, "timestamp": None},
            {"stage": "service_active", "completed": False, "timestamp": None},
        ]
        
        order_status = {
            "success": True,
            "order_id": order_id,
            "customer_name": "ABC Corporation",
            "service_type": "Business Fiber 1 Gbps",
            "current_status": "equipment_ordered",
            "progress_percentage": 43,  # 3 out of 7 stages complete
            "status_stages": status_stages,
            "scheduled_installation": "2026-02-18T08:00:00",
            "estimated_completion": "2026-02-18T17:00:00",
            "last_updated": datetime.now().isoformat(),
            "message": "Order in progress - equipment in transit"
        }
        
        return order_status
    
    except Exception as e:
        logger.error(f"Error getting order status: {e}")
        return {
            "success": False,
            "error": f"Order status error: {str(e)}"
        }


def update_order_status(
    order_id: str,
    new_status: str,
    notes: str = None
) -> Dict[str, Any]:
    """
    Updates the status of an order.
    
    Args:
        order_id: Order identifier
        new_status: New status value
        notes: Optional status update notes
    
    Returns:
        Updated order status
    """
    logger.info(f"Updating order {order_id} status to: {new_status}")
    
    try:
        valid_statuses = [
            "received",
            "scheduled",
            "equipment_ordered",
            "equipment_delivered",
            "technician_dispatched",
            "in_progress",
            "service_active",
            "complete",
            "cancelled"
        ]
        
        if new_status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }
        
        # Simulate status update
        # In production: Update order management system
        
        update = {
            "success": True,
            "order_id": order_id,
            "previous_status": "equipment_ordered",  # Would come from database
            "new_status": new_status,
            "updated_at": datetime.now().isoformat(),
            "notes": notes,
            "message": f"Order status updated to: {new_status}"
        }
        
        logger.info(f"Order status updated: {new_status}")
        return update
    
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        return {
            "success": False,
            "error": f"Order update error: {str(e)}"
        }
