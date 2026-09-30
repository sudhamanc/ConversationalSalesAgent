"""
Order management tools for the Order Agent.

These tools handle order creation, contract generation, and order lifecycle.
Moved from ServiceFulfillmentAgent to maintain proper separation of concerns:
- OrderAgent: Cart management, order creation, contract generation (PRE-FULFILLMENT)
- ServiceFulfillmentAgent: Installation scheduling, provisioning, activation (POST-ORDER)
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

import psycopg
from google.adk.tools.tool_context import ToolContext

from sales_common import db, notifications
from sales_common.ids import new_id
from sales_common.repositories.quotes import mark_ordered

from ..models import Order, OrderStatus
from ..utils.database import load_order, quote_exists, save_order, update_order_field
from ..utils.logger import get_logger

logger = get_logger(__name__)

_PHONE_RE = re.compile(r"\d{3}")


def _recipient_phone(contact_phone: Optional[str]) -> Optional[str]:
    """Only real phone numbers are used as SMS recipients (not "Not provided")."""
    if contact_phone and _PHONE_RE.search(contact_phone):
        return contact_phone
    return None


def create_order(
    customer_name: str,
    service_address: str,
    service_type: str,
    contact_phone: str = "Not provided",
    customer_id: str = None,
    contact_email: str = None,
    price: float = None,
    offer_id: str = None,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """
    Creates a new service order from cart or direct input.

    NOTE: customer_id is now OPTIONAL. If not provided, generates one automatically
    in format CUST-YYYYMMDD-XXX where XXX is hash of customer_name.

    Args:
        customer_name: Customer or business name
        service_address: Installation address
        service_type: Type of service to be ordered
        contact_phone: Customer contact phone (optional, defaults to "Not provided")
        customer_id: Customer identifier (auto-generated if not provided)
        contact_email: Customer contact email
        price: Service price (optional, for price tracking)
        offer_id: Offer/quote identifier from OfferManagement (links order to quote)

    Returns:
        Created order details with JSON structure
    """
    logger.info(f"Creating order for customer {customer_name}")

    try:
        # Read state first (Priority 1) — pulls customer_id and offer_id
        # deterministically from upstream agents instead of relying on the
        # LLM to extract them from conversation history.
        if tool_context is not None:
            cust_ctx = tool_context.state.get("customer_context") or {}
            offer_ctx = tool_context.state.get("offer_context") or {}
            logger.info(f"[STATE READ] create_order <- customer_context = {cust_ctx}")
            logger.info(f"[STATE READ] create_order <- offer_context offer_id={offer_ctx.get('offer_id')} total_price={offer_ctx.get('total_price')}")
            if not customer_id:
                state_cid = cust_ctx.get("customer_id")
                if isinstance(state_cid, str):
                    customer_id = state_cid
            if not offer_id:
                state_oid = offer_ctx.get("offer_id")
                if isinstance(state_oid, str):
                    offer_id = state_oid
            if price is None:
                state_price = offer_ctx.get("total_price")
                if isinstance(state_price, (int, float)):
                    price = float(state_price)

        # Auto-generate customer_id if not provided (fixes critical bug)
        if not customer_id:
            customer_id = new_id("CUST")
            logger.info(f"Auto-generated customer_id: {customer_id}")
        
        # Generate order ID
        order_id = new_id("ORD")
        
        # Create order instance (starts as pending_payment — confirmed after payment)
        order = Order(
            order_id=order_id,
            customer_name=customer_name,
            customer_id=customer_id,
            service_address=service_address,
            contact_phone=contact_phone,
            contact_email=contact_email,
            offer_id=offer_id,
            status=OrderStatus.PENDING_PAYMENT,
        )

        # Add service as order item
        if price:
            order.add_item(service_type=service_type, price=price, quantity=1)
        else:
            order.add_item(service_type=service_type, price=0.0, quantity=1)

        # Persist the order, mark the source quote as 'ordered' and enqueue the
        # ORDER_CONFIRMATION notification in ONE transaction (outbox pattern).
        offer_warning = None
        with db.transaction() as conn:
            # orders.offer_id is a foreign key to quotes; an unknown id would
            # abort the order, so it is dropped (and reported) instead.
            if offer_id and not quote_exists(offer_id, conn=conn):
                offer_warning = f"Offer {offer_id} not found; order created without a quote link"
                logger.warning(offer_warning)
                offer_id = None
                order.offer_id = None

            save_order(order.to_dict(), conn=conn)

            # Mark the source quote as 'ordered' so it can't be reused
            if offer_id:
                mark_ordered(offer_id, conn=conn)
                logger.info(f"Marked quote {offer_id} as ordered")

            email_notification_id = notifications.enqueue(
                "order_confirmation",
                recipient_email=contact_email,
                recipient_phone=_recipient_phone(contact_phone),
                customer_id=customer_id,
                order_id=order_id,
                args={
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "customer_email": contact_email,
                    "customer_phone": contact_phone,
                    "service_address": service_address,
                    "service_type": service_type,
                    "items": order.items,
                    "price": price,
                    "total_amount": order.total_amount,
                    "offer_id": offer_id,
                    "status": OrderStatus.PENDING_PAYMENT.value,
                    "created_at": order.created_at,
                },
                conn=conn,
            )

        logger.info(f"Order created: {order_id} for customer {customer_id}")
        email_sent = email_notification_id is not None

        # Publish order to session state so PaymentAgent and ServiceFulfillmentAgent
        # can read order_id / customer_id / amount directly without LLM extraction.
        if tool_context is not None:
            tool_context.state["order_context"] = {
                "order_id": order_id,
                "customer_id": customer_id,
                "customer_name": customer_name,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
                "service_address": service_address,
                "service_type": service_type,
                "price": price,
                "offer_id": offer_id,
                "total_amount": order.total_amount,
                "status": OrderStatus.PENDING_PAYMENT.value,
            }
            logger.info(f"[STATE WRITE] create_order -> order_context order_id={order_id} customer_id={customer_id} offer_id={offer_id}")

        # Return JSON structure
        response = {
            "success": True,
            "order_id": order_id,
            "customer_name": customer_name,
            "customer_id": customer_id,
            "service_address": service_address,
            "service_type": service_type,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "offer_id": offer_id,
            "status": OrderStatus.PENDING_PAYMENT.value,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "email_confirmation_sent": email_sent,
            "email_notification_id": email_notification_id,
            "message": f"Order {order_id} created successfully. Customer ID: {customer_id}"
        }
        if offer_warning:
            response["warning"] = offer_warning
        return json.loads(json.dumps(response))
    
    except psycopg.Error as e:
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
        
        order_dict = load_order(order_id)
        if not order_dict:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        old_status = order_dict["status"]
        now = db.now_iso()
        update_order_field(order_id, status=new_status, updated_at=now)
        
        logger.info(f"Order {order_id} status updated: {old_status} -> {new_status}")
        
        return json.loads(json.dumps({
            "success": True,
            "order_id": order_id,
            "old_status": old_status,
            "new_status": new_status,
            "updated_at": now,
            "notes": notes,
            "message": f"Order status updated to {new_status}"
        }))
    
    except psycopg.Error as e:
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
        order_dict = load_order(order_id)
        if not order_dict:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        return json.loads(json.dumps({
            "success": True,
            "order": order_dict
        }))
    
    except psycopg.Error as e:
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
        order_dict = load_order(order_id)
        if not order_dict:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        # Only allow modification of draft/pending orders
        if order_dict["status"] not in [OrderStatus.DRAFT, OrderStatus.PENDING_PAYMENT]:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Cannot modify order in {order_dict['status']} status. Only draft or pending_payment orders can be modified."
            }))
        
        # Update service and price
        if service_type or price:
            order_dict["items"] = []
            if service_type and price:
                order_dict["items"].append({"service_type": service_type, "price": price, "quantity": 1, "subtotal": price})
                order_dict["total_amount"] = price
            elif service_type:
                order_dict["items"].append({"service_type": service_type, "price": 0.0, "quantity": 1, "subtotal": 0.0})
                order_dict["total_amount"] = 0.0
        
        order_dict["updated_at"] = db.now_iso()
        save_order(order_dict)
        
        logger.info(f"Order {order_id} modified successfully")

        return json.loads(json.dumps({
            "success": True,
            "order_id": order_id,
            "order": order_dict,
            "message": f"Order {order_id} modified successfully"
        }))
    
    except psycopg.Error as e:
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
        order_dict = load_order(order_id)
        if not order_dict:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        contract = {
            "contract_id": f"CONT-{order_id}",
            "order_id": order_id,
            "customer_name": order_dict["customer_name"],
            "customer_id": order_dict["customer_id"],
            "service_address": order_dict["service_address"],
            "services": order_dict["items"],
            "total_amount": order_dict["total_amount"],
            "terms": {
                "duration": "12 months",
                "auto_renewal": True,
                "early_termination_fee": order_dict["total_amount"] * 3,  # 3 months of service
                "billing_cycle": "monthly",
                "payment_terms": "NET-30"
            },
            "generated_at": db.now_iso(),
            "status": "pending_signature"
        }
        
        logger.info(f"Contract generated: {contract['contract_id']}")
        
        return json.loads(json.dumps({
            "success": True,
            "contract": contract,
            "message": f"Contract {contract['contract_id']} generated successfully"
        }))
    
    except psycopg.Error as e:
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
        order_dict = load_order(order_id)
        if not order_dict:
            return json.loads(json.dumps({
                "success": False,
                "error": f"Order {order_id} not found"
            }))
        
        now = db.now_iso()
        update_order_field(order_id, status=OrderStatus.CANCELLED, updated_at=now)
        
        logger.info(f"Order {order_id} cancelled. Reason: {reason}")
        
        return json.loads(json.dumps({
            "success": True,
            "order_id": order_id,
            "status": OrderStatus.CANCELLED,
            "reason": reason,
            "message": f"Order {order_id} cancelled successfully"
        }))
    
    except psycopg.Error as e:
        logger.error(f"Error cancelling order: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Order cancellation error: {str(e)}"
        }))
