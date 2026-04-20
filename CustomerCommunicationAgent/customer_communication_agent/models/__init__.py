"""
Data models for the Customer Communication Agent.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    """Notification type enumeration."""
    ORDER_CONFIRMATION = "order_confirmation"
    QUOTE_SAVED = "quote_saved"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    INSTALLATION_SCHEDULED = "installation_scheduled"
    INSTALLATION_REMINDER = "installation_reminder"
    SERVICE_ACTIVATED = "service_activated"
    ORDER_STATUS_UPDATE = "order_status_update"
    ABANDONED_CART = "abandoned_cart"
    GENERIC = "generic"


class NotificationChannel(str, Enum):
    """Notification channel enumeration."""
    EMAIL = "email"
    SMS = "sms"
    BOTH = "both"


class NotificationStatus(str, Enum):
    """Notification status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DEDUPED = "deduped"


class Notification:
    """Notification data model."""
    
    def __init__(
        self,
        notification_id: str,
        notification_type: NotificationType,
        recipient_email: Optional[str] = None,
        recipient_phone: Optional[str] = None,
        subject: str = "",
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.notification_id = notification_id
        self.notification_type = notification_type
        self.recipient_email = recipient_email
        self.recipient_phone = recipient_phone
        self.subject = subject
        self.message = message
        self.metadata = metadata or {}
        self.status = NotificationStatus.PENDING
        self.channels: List[str] = []
        self.created_at = datetime.now().isoformat()
        self.sent_at: Optional[str] = None
        self.error: Optional[str] = None
    
    def mark_sent(self, channel: str):
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now().isoformat()
        if channel not in self.channels:
            self.channels.append(channel)
    
    def mark_failed(self, error: str):
        """Mark notification as failed."""
        self.status = NotificationStatus.FAILED
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary."""
        return {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type,
            "recipient_email": self.recipient_email,
            "recipient_phone": self.recipient_phone,
            "subject": self.subject,
            "message": self.message,
            "metadata": self.metadata,
            "status": self.status,
            "channels": self.channels,
            "created_at": self.created_at,
            "sent_at": self.sent_at,
            "error": self.error,
        }


__all__ = ["Notification", "NotificationType", "NotificationChannel", "NotificationStatus"]
