"""
Order management tools for the Order Agent.

These tools handle order creation, contract generation, and order lifecycle.
Moved from ServiceFulfillmentAgent to maintain proper separation of concerns:
- OrderAgent: Cart management, order creation, contract generation (PRE-FULFILLMENT)
- ServiceFulfillmentAgent: Installation scheduling, provisioning, activation (POST-ORDER)
"""

import json
from typing import Dict, Any
from datetime import datetime
from ..utils.logger import get_logger
from ..models import Order, OrderStatus

logger = get_logger(__name__)

# In-memory order storage (in production, use database)
_ORDERS: Dict[str, Order] = {}


def create_order(
    customer_name: str,
    service_address: str,
    service_type: str,
    contact_phone: str,
    customer_id: str = None,
    contact_email: str = None,
    price: float = None
) -> Dict[str, Any]:
    """
    Creates a new service order from cart or direct input.
    
    NOTE: customer_id is now OPTIONAL. If not provided, generates one automatically
    in format CUST-YYYYMMDD-XXX where XXX is hash of customer_name.
    
    Args:
        customer_name: Customer or business name
        service_address: Installation address
        service_type: Type of service to be ordered
        contact_phone: Customer contact phone
        customer_id: Customer identifier (auto-generated if not provided)
        contact_email: Customer contact email
        price: Service price (optional, for price tracking)
    
    Returns:
        Created order details with JSON structure
    """
    logger.info(f"Creating order for customer {customer_name}")
    
    try:
        # Auto-generate customer_id if not provided (fixes critical bug)
        if not customer_id:
            customer_id = f"CUST-{datetime.now().strftime('%Y%m%d')}-{hash(customer_name) % 1000:03d}"
            logger.info(f"Auto-generated customer_id: {customer_id}")
        
        # Generate order ID
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{hash(customer_name) % 1000:03d}"
        
        # Create order instance
        order = Order(
            order_id=order_id,
            customer_name=customer_name,
            customer_id=customer_id,
            service_address=service_address,
            contact_phone=contact_phone,
            contact_email=contact_email,
            status=OrderStatus.DRAFT,
        )
        
        # Add service as order item
        if price:
            order.add_item(service_type=service_type, price=price, quantity=1)
        else:
            order.add_item(service_type=service_type, price=0.0, quantity=1)
        
        # Store order
        _ORDERS[order_id] = order
        
        logger.info(f"Order created: {order_id} for customer {customer_id}")
        
        # Return JSON structure
        return json.loads(json.dumps({
            "success": True,
            "order_id": order_id,
            "customer_name": customer_name,
            "customer_id": customer_id,
            "service_address": service_address,
            "service_type": service_type,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "message": f"Order {order_id} created successfully. Customer ID: {customer_id}"
        }))
    
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Order creation error: {str(e)}"
        }))


def update_order_status(
    order_id: str,
    new_status: str,
    notes: str = None
) -> Dict[str, Any]:
    """
    Updates the status of an order.
    
    Args:
        order_id: Order identifier
        new_status: New status value (draft, pending_payment, payment_approved, confirmed, cancelled, failed)
        notes: Optional status update notes
    
    Returns:
        Updated order status as JSON
    """
    logger.info(f"Updating order {order_id} status to: {new_status}")
    
    try:
        valid_statuses = [
            "draft",
            "pending_payment",
            "payment_approved",
            "confirmed",
            "cancelled",
            "failed"
        ]
        
        if new_status not in valid_statuses:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }))
        
        if order_id not in _ORDERS:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        order = _ORDERS[order_id]
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.now().isoformat()
        
        logger.info(f"Order {order_id} status updated: {old_status} -> {new_status}")
        
        return json.loads(json.dumps({
            "success": True,
            "order_id": order_id,
            "old_status": old_status,
            "new_status": new_status,
            "updated_at": order.updated_at,
            "notes": notes,
            "message": f"Order status updated to {new_status}"
        }))
    
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Order status update error: {str(e)}"
        }))


def get_order(order_id: str) -> Dict[str, Any]:
    """
    Retrieve order details.
    
    Args:
        order_id: Order identifier
    
    Returns:
        Order details as JSON
    """
    logger.info(f"Getting order {order_id}")
    
    try:
        if order_id not in _ORDERS:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        order = _ORDERS[order_id]
        
        return json.loads(json.dumps({
            "success": True,
            "order": order.to_dict()
        }))
    
    except Exception as e:
        logger.error(f"Error getting order: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Get order error: {str(e)}"
        }))


def modify_order(
    order_id: str,
    service_type: str = None,
    price: float = None
) -> Dict[str, Any]:
    """
    Modify an existing order (before it's confirmed).
    Only draft and pending_payment orders can be modified.
    
    Args:
        order_id: Order identifier
        service_type: New service type
        price: New price
    
    Returns:
        Updated order details as JSON
    """
    logger.info(f"Modifying order {order_id}")
    
    try:
        if order_id not in _ORDERS:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        order = _ORDERS[order_id]
        
        # Only allow modification of draft/pending orders
        if order.status not in [OrderStatus.DRAFT, OrderStatus.PENDING_PAYMENT]:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Cannot modify order in {order.status} status. Only draft or pending_payment orders can be modified."
            }))
        
        # Update service and price
        if service_type or price:
            order.items = []  # Clear existing items
            if service_type and price:
                order.add_item(service_type=service_type, price=price, quantity=1)
            elif service_type:
                order.add_item(service_type=service_type, price=0.0, quantity=1)
        
        logger.info(f"Order {order_id} modified successfully")
        
        return json.loads(json.dumps({
            "success": True,
            "order_id": order_id,
            "order": order.to_dict(),
            "message": f"Order {order_id} modified successfully"
        }))
    
    except Exception as e:
        logger.error(f"Error modifying order: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Order modification error: {str(e)}"
        }))


def generate_contract(order_id: str) -> Dict[str, Any]:
    """
    Generate a service contract for an order.
    
    Args:
        order_id: Order identifier
    
    Returns:
        Contract details as JSON
    """
    logger.info(f"Generating contract for order {order_id}")
    
    try:
        if order_id not in _ORDERS:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        order = _ORDERS[order_id]
        
        contract = {
            "contract_id": f"CONT-{order_id}",
            "order_id": order_id,
            "customer_name": order.customer_name,
            "customer_id": order.customer_id,
            "service_address": order.service_address,
            "services": order.items,
            "total_amount": order.total_amount,
            "terms": {
                "duration": "12 months",
                "auto_renewal": True,
                "early_termination_fee": order.total_amount * 3,  # 3 months of service
                "billing_cycle": "monthly",
                "payment_terms": "NET-30"
            },
            "generated_at": datetime.now().isoformat(),
            "status": "pending_signature"
        }
        
        logger.info(f"Contract generated: {contract['contract_id']}")
        
        return json.loads(json.dumps({
            "success": True,
            "contract": contract,
            "message": f"Contract {contract['contract_id']} generated successfully"
        }))
    
    except Exception as e:
        logger.error(f"Error generating contract: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Contract generation error: {str(e)}"
        }))


def cancel_order(order_id: str, reason: str = None) -> Dict[str, Any]:
    """
    Cancel an order.
    
    Args:
        order_id: Order identifier
        reason: Cancellation reason
    
    Returns:
        Cancellation result as JSON
    """
    logger.info(f"Cancelling order {order_id}")
    
    try:
        if order_id not in _ORDERS:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        order = _ORDERS[order_id]
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now().isoformat()
        
        logger.info(f"Order {order_id} cancelled. Reason: {reason}")
        
        return json.loads(json.dumps({
            "success": True,
            "order_id": order_id,
            "status": order.status,
            "reason": reason,
            "message": f"Order {order_id} cancelled successfully"
        }))
    
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Order cancellation error: {str(e)}"
        }))
