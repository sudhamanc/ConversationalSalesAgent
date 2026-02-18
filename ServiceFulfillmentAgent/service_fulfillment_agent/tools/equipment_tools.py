"""
Equipment provisioning and tracking tools for the Service Fulfillment Agent.

These tools handle equipment ordering, tracking, and delivery verification.
"""

import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from ..utils.logger import get_logger

logger = get_logger(__name__)


def provision_equipment(
    order_id: str,
    service_type: str,
    equipment_list_json: str = None
) -> Dict[str, Any]:
    """
    Orders equipment for an installation.

    For production: Integrates with equipment management system
    For testing: Simulates equipment ordering

    Args:
        order_id: Order identifier
        service_type: Type of service (determines required equipment)
        equipment_list_json: Optional JSON string of equipment array. Each item has "type" (str), "model" (str), "quantity" (int). Example: '[{"type": "Router", "model": "XR-1000", "quantity": 1}]'. If not provided, equipment is auto-determined from service_type.

    Returns:
        Equipment order details with tracking
    """
    logger.info(f"Provisioning equipment for order {order_id}")

    try:
        # Determine equipment based on service type if not specified
        equipment_list = None
        if equipment_list_json:
            try:
                equipment_list = json.loads(equipment_list_json)
            except (json.JSONDecodeError, TypeError):
                return {
                    "success": False,
                    "error": "Invalid equipment_list_json format. Must be a valid JSON array string."
                }
        if equipment_list is None:
            equipment_list = _get_required_equipment(service_type)
        
        # Simulate equipment ordering
        # In production: Call equipment management system API
        
        provisioned_items = []
        delivery_date = datetime.now() + timedelta(days=3)
        
        for idx, item in enumerate(equipment_list):
            equipment_id = f"EQ-{order_id.split('-')[-1]}-{idx+1:03d}"
            tracking_number = f"TRACK-{datetime.now().strftime('%Y%m%d')}-{hash(equipment_id) % 100000:05d}"
            
            provisioned_items.append({
                "equipment_id": equipment_id,
                "type": item.get("type"),
                "model": item.get("model"),
                "quantity": item.get("quantity", 1),
                "tracking_number": tracking_number,
                "status": "ordered",
                "estimated_delivery": delivery_date.isoformat()
            })
        
        return {
            "success": True,
            "order_id": order_id,
            "equipment_items": provisioned_items,
            "total_items": len(provisioned_items),
            "estimated_delivery": delivery_date.isoformat(),
            "message": f"Equipment ordered: {len(provisioned_items)} items, delivery by {delivery_date.strftime('%Y-%m-%d')}"
        }
    
    except Exception as e:
        logger.error(f"Error provisioning equipment: {e}")
        return {
            "success": False,
            "error": f"Equipment provisioning error: {str(e)}"
        }


def track_equipment(
    order_id: str = None,
    tracking_number: str = None
) -> Dict[str, Any]:
    """
    Tracks equipment shipment status.
    
    Args:
        order_id: Order identifier (tracks all equipment for order)
        tracking_number: Specific tracking number
    
    Returns:
        Equipment tracking information
    """
    logger.info(f"Tracking equipment for order {order_id} / tracking {tracking_number}")
    
    try:
        # Simulate equipment tracking
        # In production: Query equipment management / shipping system
        
        if order_id:
            # Return all equipment for order
            equipment_items = [
                {
                    "equipment_id": f"EQ-001",
                    "type": "router",
                    "model": "XR-1000 Business Router",
                    "tracking_number": "TRACK-123456",
                    "status": "in_transit",
                    "location": "Distribution Center - Philadelphia",
                    "estimated_delivery": (datetime.now() + timedelta(days=2)).isoformat()
                },
                {
                    "equipment_id": f"EQ-002",
                    "type": "ont",
                    "model": "Fiber ONT",
                    "tracking_number": "TRACK-123457",
                    "status": "in_transit",
                    "location": "Distribution Center - Philadelphia",
                    "estimated_delivery": (datetime.now() + timedelta(days=2)).isoformat()
                }
            ]
            
            return {
                "success": True,
                "order_id": order_id,
                "equipment_items": equipment_items,
                "message": f"Tracking {len(equipment_items)} equipment items"
            }
        
        elif tracking_number:
            # Return specific item tracking
            return {
                "success": True,
                "tracking_number": tracking_number,
                "status": "in_transit",
                "location": "Distribution Center - Philadelphia",
                "estimated_delivery": (datetime.now() + timedelta(days=2)).isoformat(),
                "tracking_events": [
                    {
                        "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                        "location": "Warehouse - New York",
                        "status": "shipped"
                    },
                    {
                        "timestamp": datetime.now().isoformat(),
                        "location": "Distribution Center - Philadelphia",
                        "status": "in_transit"
                    }
                ],
                "message": "Equipment is in transit"
            }
        else:
            return {
                "success": False,
                "error": "Either order_id or tracking_number must be provided"
            }
    
    except Exception as e:
        logger.error(f"Error tracking equipment: {e}")
        return {
            "success": False,
            "error": f"Equipment tracking error: {str(e)}"
        }


def verify_equipment_delivery(
    order_id: str,
    equipment_ids: List[str] = None
) -> Dict[str, Any]:
    """
    Verifies equipment has been delivered and is ready for installation.
    
    Args:
        order_id: Order identifier
        equipment_ids: Optional list of specific equipment IDs to verify
    
    Returns:
        Delivery verification status
    """
    logger.info(f"Verifying equipment delivery for order {order_id}")
    
    try:
        # Simulate delivery verification
        # In production: Check equipment management system
        
        verified_items = []
        missing_items = []
        
        # Simulate some items delivered
        if equipment_ids:
            for eq_id in equipment_ids:
                verified_items.append({
                    "equipment_id": eq_id,
                    "status": "delivered",
                    "delivered_at": datetime.now().isoformat(),
                    "verified": True
                })
        else:
            # Default items for order
            verified_items = [
                {
                    "equipment_id": "EQ-001",
                    "type": "router",
                    "status": "delivered",
                    "delivered_at": datetime.now().isoformat(),
                    "verified": True
                },
                {
                    "equipment_id": "EQ-002",
                    "type": "ont",
                    "status": "delivered",
                    "delivered_at": datetime.now().isoformat(),
                    "verified": True
                }
            ]
        
        all_verified = len(missing_items) == 0
        
        return {
            "success": True,
            "order_id": order_id,
            "all_equipment_delivered": all_verified,
            "verified_items": verified_items,
            "missing_items": missing_items,
            "message": "All equipment delivered and verified" if all_verified else "Some equipment is missing"
        }
    
    except Exception as e:
        logger.error(f"Error verifying equipment delivery: {e}")
        return {
            "success": False,
            "error": f"Equipment verification error: {str(e)}"
        }


# Helper function

def _get_required_equipment(service_type: str) -> List[Dict[str, Any]]:
    """
    Determines required equipment based on service type.
    
    Args:
        service_type: Type of service being installed
    
    Returns:
        List of required equipment items
    """
    equipment_map = {
        "fiber": [
            {"type": "ont", "model": "Fiber ONT", "quantity": 1},
            {"type": "router", "model": "XR-1000 Business Router", "quantity": 1}
        ],
        "coax": [
            {"type": "modem", "model": "CM-2000 Business Modem", "quantity": 1},
            {"type": "router", "model": "XR-1000 Business Router", "quantity": 1}
        ],
        "ethernet": [
            {"type": "router", "model": "XR-1000 Business Router", "quantity": 1}
        ]
    }
    
    # Determine service technology from service_type string
    service_lower = service_type.lower()
    if "fiber" in service_lower:
        return equipment_map["fiber"]
    elif "coax" in service_lower or "cable" in service_lower:
        return equipment_map["coax"]
    else:
        return equipment_map["ethernet"]
