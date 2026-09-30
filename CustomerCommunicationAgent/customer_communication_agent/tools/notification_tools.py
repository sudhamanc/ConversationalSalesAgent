"""Agent-facing notification tools for the Customer Communication Agent.

Every ``send_*`` tool writes to the shared notification outbox
(``sales_common.notifications.enqueue``) and then immediately dispatches that one
row (:func:`customer_communication_agent.dispatcher.dispatch_pending`), so the
model gets the real delivery status (``sent``, ``simulated``, ``deduped``,
``failed``) in the same turn. Rendering, de-duplication and SMTP delivery live in
the dispatcher, shared with the background outbox loop.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import psycopg

from google.adk.tools.tool_context import ToolContext
from sales_common import notifications
from sales_common.config import ConfigError

from ..dispatcher import DEDUP_WINDOW_MINUTES, dispatch_pending
from ..models import normalize_type
from ..utils.db import get_history, get_notification

logger = logging.getLogger(__name__)

MAX_HISTORY_LIMIT = 50

_LABELS = {
    "order_confirmation": "Order confirmation",
    "quote_confirmation": "Quote confirmation",
    "payment_confirmation": "Payment notification",
    "installation_reminder": "Installation reminder",
    "service_activated": "Service activation notification",
    "abandoned_cart": "Abandoned cart reminder",
    "order_status_update": "Order status update",
}


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _state_defaults(
    tool_context: Optional[ToolContext], email: Optional[str], phone: Optional[str]
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Fill customer_id (and contact details when none were given) from journey state."""
    if tool_context is None:
        return None, email, phone
    cust = tool_context.state.get("customer_context") or {}
    order = tool_context.state.get("order_context") or {}
    customer_id = cust.get("customer_id") if isinstance(cust.get("customer_id"), str) else None
    if not email and not phone:
        email = _clean(order.get("contact_email")) if isinstance(order.get("contact_email"), str) else None
        phone = _clean(order.get("contact_phone")) if isinstance(order.get("contact_phone"), str) else None
    return customer_id, email, phone


def _send(
    notification_type: str,
    *,
    customer_email: Optional[str],
    customer_phone: Optional[str],
    args: dict[str, Any],
    order_id: Optional[str] = None,
    email_only: bool = False,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    label = _LABELS.get(notification_type, "Notification")
    email, phone = _clean(customer_email), _clean(customer_phone)
    customer_id, email, phone = _state_defaults(tool_context, email, phone)
    if not email and not phone:
        return {"success": False, "error": "No contact information provided (email or phone required)"}
    if email_only and not email:
        return {"success": False, "error": f"{label} is email-only (marketing); no email address provided"}

    channels = (["email"] if email else []) + (["sms"] if phone and not email_only else [])
    try:
        notification_id = notifications.enqueue(
            notification_type,
            recipient_email=email,
            recipient_phone=None if email_only else phone,
            args={k: v for k, v in args.items() if v is not None},
            customer_id=customer_id,
            order_id=_clean(order_id),
            channels=channels,
        )
        if notification_id is None:
            return {"success": False, "error": "Invalid email address and no phone number provided"}
        dispatch_pending(limit=1, notification_id=notification_id)
        record = get_notification(notification_id)
    except (psycopg.Error, ConfigError) as exc:
        logger.error("%s failed: %s", label, type(exc).__name__)
        return {"success": False, "error": f"Notification error: {type(exc).__name__}"}

    if record is None:  # pragma: no cover - row was just inserted
        return {"success": False, "error": "Notification record not found after enqueue"}

    status = record["status"]
    result: dict[str, Any] = {
        "notification_id": notification_id,
        "notification_type": notification_type,
        "recipient_email": record["recipient_email"],
        "recipient_phone": record["recipient_phone"],
        "status": status,
        "channels": record["channels"] if status in {"sent", "simulated"} else [],
    }
    if status in {"sent", "simulated"}:
        via = ", ".join(result["channels"])
        result.update(
            success=True,
            email_delivery=("delivered" if status == "sent" else "simulated")
            if "email" in result["channels"] else None,
            message=f"{label} sent successfully via {via}"
            + (" (simulated: SMTP delivery is disabled)" if status == "simulated" else ""),
        )
    elif status == "deduped":
        result.update(
            success=True,
            message=f"Duplicate notification prevented (already sent within {DEDUP_WINDOW_MINUTES} minutes)",
        )
    elif status == "pending" and not record["attempts"]:
        # Another dispatcher instance holds the row; it will be delivered shortly.
        result.update(success=True, status="queued", message=f"{label} queued for delivery")
    else:
        result.update(
            success=False,
            error=record["error"] or "Delivery failed",
            attempts=record["attempts"],
            message=(
                f"{label} delivery failed; it will be retried automatically"
                if status == "pending" else f"{label} delivery failed"
            ),
        )
    return result


def send_order_confirmation(
    order_id: str,
    customer_name: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    service_type: Optional[str] = None,
    total_amount: Optional[float] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Send an order confirmation notification to the customer (email and/or SMS).

    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email address
        customer_phone: Customer phone number
        service_type: Type of service ordered
        total_amount: Total order amount
    """
    return _send(
        "order_confirmation",
        customer_email=customer_email,
        customer_phone=customer_phone,
        order_id=order_id,
        args={"order_id": order_id, "customer_name": customer_name,
              "service_type": service_type, "total_amount": total_amount},
        tool_context=tool_context,
    )


def send_quote_confirmation(
    quote_id: str,
    customer_name: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    items_summary: Optional[str] = None,
    monthly_total: Optional[float] = None,
    term_months: Optional[int] = None,
    total_discount: Optional[float] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Send a quote confirmation notification when a quote is saved.

    Args:
        quote_id: Saved quote identifier
        customer_name: Customer name
        customer_email: Customer email address
        customer_phone: Customer phone number
        items_summary: Human-readable summary of quoted products
        monthly_total: Monthly total price after discounts
        term_months: Contract term in months
        total_discount: Total monthly discount amount
    """
    return _send(
        "quote_confirmation",
        customer_email=customer_email,
        customer_phone=customer_phone,
        args={"quote_id": quote_id, "customer_name": customer_name, "items_summary": items_summary,
              "monthly_total": monthly_total, "term_months": term_months,
              "total_discount": total_discount},
        tool_context=tool_context,
    )


def send_payment_notification(
    order_id: str,
    customer_name: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    payment_status: str = "success",
    amount: Optional[float] = None,
    payment_method: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Send a payment status notification (success or failure).

    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone
        payment_status: Payment status ("success" or "failed")
        amount: Payment amount
        payment_method: Payment method used
    """
    status = "success" if (payment_status or "success").strip().lower() == "success" else "failed"
    return _send(
        "payment_confirmation",
        customer_email=customer_email,
        customer_phone=customer_phone,
        order_id=order_id,
        args={"order_id": order_id, "customer_name": customer_name, "payment_status": status,
              "amount": amount, "payment_method": payment_method},
        tool_context=tool_context,
    )


def send_installation_reminder(
    order_id: str,
    customer_name: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    installation_date: Optional[str] = None,
    installation_time: Optional[str] = None,
    service_address: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Send an installation reminder notification (24 hours before).

    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone
        installation_date: Installation date
        installation_time: Installation time window
        service_address: Service installation address
    """
    return _send(
        "installation_reminder",
        customer_email=customer_email,
        customer_phone=customer_phone,
        order_id=order_id,
        args={"order_id": order_id, "customer_name": customer_name,
              "installation_date": installation_date, "installation_time": installation_time,
              "service_address": service_address},
        tool_context=tool_context,
    )


def send_service_activated_notification(
    order_id: str,
    customer_name: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    service_type: Optional[str] = None,
    account_number: Optional[str] = None,
    circuit_id: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Send a service activation notification.

    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone
        service_type: Type of service activated
        account_number: Customer account number
        circuit_id: Service circuit ID
    """
    return _send(
        "service_activated",
        customer_email=customer_email,
        customer_phone=customer_phone,
        order_id=order_id,
        args={"order_id": order_id, "customer_name": customer_name, "service_type": service_type,
              "account_number": account_number, "circuit_id": circuit_id},
        tool_context=tool_context,
    )


def send_abandoned_cart_reminder(
    cart_id: str,
    customer_name: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    cart_items: Optional[str] = None,
    total_amount: Optional[float] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Send an abandoned cart recovery notification (email only; marketing message).

    Args:
        cart_id: Cart identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone (not used: no SMS for marketing without opt-in)
        cart_items: Description of cart items
        total_amount: Total cart amount
    """
    return _send(
        "abandoned_cart",
        customer_email=customer_email,
        customer_phone=customer_phone,
        email_only=True,
        args={"cart_id": cart_id, "customer_name": customer_name, "cart_items": cart_items,
              "total_amount": total_amount},
        tool_context=tool_context,
    )


def send_order_status_update(
    order_id: str,
    customer_name: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    status_message: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Send an order status update notification.

    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone
        old_status: Previous order status
        new_status: New order status
        status_message: Status update message
    """
    return _send(
        "order_status_update",
        customer_email=customer_email,
        customer_phone=customer_phone,
        order_id=order_id,
        args={"order_id": order_id, "customer_name": customer_name, "old_status": old_status,
              "new_status": new_status, "status_message": status_message},
        tool_context=tool_context,
    )


def get_notification_history(
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    notification_type: Optional[str] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Retrieve notification history for a customer, newest first.

    Args:
        customer_email: Customer email
        customer_phone: Customer phone
        notification_type: Filter by notification type (e.g. "order_confirmation")
        limit: Maximum number of notifications to return (1-50)
    """
    email, phone = _clean(customer_email), _clean(customer_phone)
    if not email and not phone:
        return {"success": False, "error": "No contact information provided"}
    ntype = normalize_type(notification_type) if _clean(notification_type) else None
    try:
        limit = max(1, min(int(limit), MAX_HISTORY_LIMIT))
    except (TypeError, ValueError):
        limit = 10
    try:
        rows = get_history(customer_email=email, customer_phone=phone,
                           notification_type=ntype, limit=limit)
    except (psycopg.Error, ConfigError) as exc:
        logger.error("Notification history query failed: %s", type(exc).__name__)
        return {"success": False, "error": f"Notification history error: {type(exc).__name__}"}
    return {
        "success": True,
        "count": len(rows),
        "notifications": rows,
        "message": f"Retrieved {len(rows)} notifications",
    }
