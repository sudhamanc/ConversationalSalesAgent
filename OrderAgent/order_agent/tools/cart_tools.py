"""
Shopping cart management tools for the Order Agent.

Carts are persisted in SQLite (OrderAgent/data/orders.db) so they survive
process restarts and returning customers can resume where they left off.
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from ..utils.logger import get_logger
from ..utils.database import save_cart, load_cart, load_carts_for_customer, delete_cart

logger = get_logger(__name__)


def create_cart(customer_id: str) -> Dict[str, Any]:
    """
    Create a new shopping cart for a customer.
    
    Args:
        customer_id: Unique customer identifier
    
    Returns:
        Created cart details
    """
    logger.info(f"Creating cart for customer {customer_id}")
    
    try:
        cart_id = f"CART-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(customer_id) % 1000:03d}"
        
        cart = {
            "cart_id": cart_id,
            "customer_id": customer_id,
            "items": [],
            "total_amount": 0.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "expires_at": None,  # Set to 30 minutes from last update
        }
        
        save_cart(cart)
        
        logger.info(f"Cart created: {cart_id}")
        return {
            "success": True,
            "cart_id": cart_id,
            "cart": cart,
            "message": f"Cart {cart_id} created successfully"
        }
    
    except Exception as e:
        logger.error(f"Error creating cart: {e}")
        return {
            "success": False,
            "error": f"Cart creation error: {str(e)}"
        }


def add_to_cart(
    cart_id: str,
    service_type: str,
    price: float,
    quantity: int = 1
) -> Dict[str, Any]:
    """
    Add a service/product to the shopping cart.
    
    Args:
        cart_id: Cart identifier
        service_type: Type of service to add
        price: Price per unit
        quantity: Quantity to add
    
    Returns:
        Updated cart details
    """
    logger.info(f"Adding {service_type} to cart {cart_id}")
    
    try:
        cart = load_cart(cart_id)
        if not cart:
            return {
                "success": False,
                "error": f"Cart {cart_id} not found"
            }
        
        # Check if item already exists in cart
        existing_item = next((item for item in cart["items"] if item["service_type"] == service_type), None)
        
        if existing_item:
            # Update quantity
            existing_item["quantity"] += quantity
            existing_item["subtotal"] = existing_item["price"] * existing_item["quantity"]
        else:
            # Add new item
            cart["items"].append({
                "service_type": service_type,
                "price": price,
                "quantity": quantity,
                "subtotal": price * quantity
            })
        
        # Update total
        cart["total_amount"] = sum(item["subtotal"] for item in cart["items"])
        cart["updated_at"] = datetime.now().isoformat()
        
        save_cart(cart)
        
        logger.info(f"Cart {cart_id} updated: {len(cart['items'])} items, total ${cart['total_amount']}")
        
        return {
            "success": True,
            "cart_id": cart_id,
            "cart": cart,
            "message": f"Added {service_type} to cart"
        }
    
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        return {
            "success": False,
            "error": f"Add to cart error: {str(e)}"
        }


def remove_from_cart(cart_id: str, service_type: str) -> Dict[str, Any]:
    """
    Remove a service/product from the shopping cart.
    
    Args:
        cart_id: Cart identifier
        service_type: Type of service to remove
    
    Returns:
        Updated cart details
    """
    logger.info(f"Removing {service_type} from cart {cart_id}")
    
    try:
        cart = load_cart(cart_id)
        if not cart:
            return {
                "success": False,
                "error": f"Cart {cart_id} not found"
            }
        
        cart["items"] = [item for item in cart["items"] if item["service_type"] != service_type]
        cart["total_amount"] = sum(item["subtotal"] for item in cart["items"])
        cart["updated_at"] = datetime.now().isoformat()
        
        save_cart(cart)
        
        logger.info(f"Removed {service_type} from cart {cart_id}")
        
        return {
            "success": True,
            "cart_id": cart_id,
            "cart": cart,
            "message": f"Removed {service_type} from cart"
        }
    
    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        return {
            "success": False,
            "error": f"Remove from cart error: {str(e)}"
        }


def get_cart(cart_id: str) -> Dict[str, Any]:
    """
    Retrieve cart details.
    
    Args:
        cart_id: Cart identifier
    
    Returns:
        Cart details
    """
    logger.info(f"Getting cart {cart_id}")
    
    try:
        cart = load_cart(cart_id)
        if not cart:
            return {
                "success": False,
                "error": f"Cart {cart_id} not found"
            }
        
        return {
            "success": True,
            "cart": cart
        }
    
    except Exception as e:
        logger.error(f"Error getting cart: {e}")
        return {
            "success": False,
            "error": f"Get cart error: {str(e)}"
        }


def clear_cart(cart_id: str) -> Dict[str, Any]:
    """
    Clear all items from the cart.
    
    Args:
        cart_id: Cart identifier
    
    Returns:
        Operation result
    """
    logger.info(f"Clearing cart {cart_id}")
    
    try:
        cart = load_cart(cart_id)
        if not cart:
            return {
                "success": False,
                "error": f"Cart {cart_id} not found"
            }
        
        cart["items"] = []
        cart["total_amount"] = 0.0
        cart["updated_at"] = datetime.now().isoformat()
        
        save_cart(cart)
        
        return {
            "success": True,
            "message": f"Cart {cart_id} cleared successfully"
        }
    
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        return {
            "success": False,
            "error": f"Clear cart error: {str(e)}"
        }
