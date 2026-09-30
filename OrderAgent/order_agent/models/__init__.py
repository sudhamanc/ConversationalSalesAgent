"""
Data models for the Order Agent.
"""

from typing import Dict, Any, List, Optional
from enum import Enum

from sales_common.db import compute_expires_at, now_iso


class OrderStatus(str, Enum):
    """Order status enumeration."""
    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_APPROVED = "payment_approved"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Order:
    """Order data model."""
    
    def __init__(
        self,
        order_id: str,
        customer_name: str,
        customer_id: str,
        service_address: str,
        contact_phone: str,
        contact_email: Optional[str] = None,
        offer_id: Optional[str] = None,
        status: str = OrderStatus.DRAFT,
    ):
        self.order_id = order_id
        self.customer_name = customer_name
        self.customer_id = customer_id
        self.service_address = service_address
        self.contact_phone = contact_phone
        self.contact_email = contact_email
        self.offer_id = offer_id
        self.status = status
        self.items: List[Dict[str, Any]] = []
        self.created_at = now_iso()
        self.updated_at = self.created_at
        # Order TTL: 48h from creation while pending_payment (enforced by
        # sales_common.maintenance.cleanup_stale_records).
        self.expires_at = compute_expires_at(self.created_at, "order")
        self.total_amount = 0.0
    
    def add_item(self, service_type: str, price: float, quantity: int = 1):
        """Add an item to the order."""
        self.items.append({
            "service_type": service_type,
            "price": price,
            "quantity": quantity,
            "subtotal": price * quantity
        })
        self.total_amount = sum(item["subtotal"] for item in self.items)
        self.updated_at = now_iso()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary."""
        return {
            "order_id": self.order_id,
            "customer_name": self.customer_name,
            "customer_id": self.customer_id,
            "service_address": self.service_address,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "offer_id": self.offer_id,
            "status": self.status,
            "items": self.items,
            "total_amount": self.total_amount,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
        }


__all__ = ["Order", "OrderStatus"]
