"""
Notification tools for the Customer Communication Agent.

These tools handle sending notifications via email, SMS, and multi-channel delivery
for various customer communication scenarios.
"""

import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from ..utils.logger import get_logger
from ..models import Notification, NotificationType, NotificationStatus

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Email configuration (set via environment variables)
# ---------------------------------------------------------------------------
SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Gmail: use App Password
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "B2B Sales Notifications")

if SMTP_ENABLED:
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP_ENABLED=true but SMTP_USER or SMTP_PASSWORD not set")
        SMTP_ENABLED = False
    else:
        logger.info(f"Real email delivery enabled via {SMTP_HOST}:{SMTP_PORT}")
else:
    logger.info("Email delivery in simulation mode (set SMTP_ENABLED=true to send real emails)")


def _send_email(to_address: str, subject: str, body: str) -> dict:
    """
    Send a real email via SMTP when SMTP_ENABLED=true, otherwise simulate.

    Returns:
        dict with "sent" (bool) and "detail" (str)
    """
    if not SMTP_ENABLED:
        logger.info(f"[SIMULATED] Email to {to_address}: {subject}")
        return {"sent": True, "detail": "simulated"}

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [to_address], msg.as_string())

        logger.info(f"Email delivered to {to_address}: {subject}")
        return {"sent": True, "detail": "delivered"}
    except smtplib.SMTPAuthenticationError as exc:
        logger.error(f"SMTP auth failed: {exc}")
        return {"sent": False, "detail": f"SMTP auth error: {exc}"}
    except Exception as exc:
        logger.error(f"Email send failed to {to_address}: {exc}")
        return {"sent": False, "detail": f"SMTP error: {exc}"}


# In-memory notification storage (in production, use database)
_NOTIFICATIONS: Dict[str, Notification] = {}
_DEDUP_CACHE: Dict[str, datetime] = {}  # Track recent notifications for deduplication


def _generate_notification_id(notification_type: str, recipient: str) -> str:
    """Generate unique notification ID using microsecond precision to avoid collisions."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    return f"NOTIF-{timestamp}"


def _check_duplicate(notification_type: str, recipient: str, window_minutes: int = 5) -> bool:
    """
    Check if a similar notification was sent recently.
    
    Args:
        notification_type: Type of notification
        recipient: Recipient identifier
        window_minutes: Time window for deduplication (default 5 minutes)
    
    Returns:
        True if duplicate found, False otherwise
    """
    dedup_key = f"{notification_type}:{recipient}"
    
    if dedup_key in _DEDUP_CACHE:
        last_sent = _DEDUP_CACHE[dedup_key]
        if datetime.now() - last_sent < timedelta(minutes=window_minutes):
            logger.warning(f"Duplicate notification blocked: {dedup_key}")
            return True
    
    # Update cache
    _DEDUP_CACHE[dedup_key] = datetime.now()
    return False


def send_order_confirmation(
    order_id: str,
    customer_name: str,
    customer_email: str = None,
    customer_phone: str = None,
    service_type: str = None,
    total_amount: float = None
) -> Dict[str, Any]:
    """
    Send order confirmation notification to customer.
    
    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email address
        customer_phone: Customer phone number
        service_type: Type of service ordered
        total_amount: Total order amount
    
    Returns:
        Notification result as JSON
    """
    logger.info(f"Sending order confirmation for order {order_id} to {customer_name}")
    
    try:
        # Validate contact info
        if not customer_email and not customer_phone:
            return json.loads(json.dumps({
                "success": False,
                "error": "No contact information provided (email or phone required)"
            }))
        
        # Check for duplicate
        recipient = customer_email or customer_phone
        if _check_duplicate(NotificationType.ORDER_CONFIRMATION, recipient):
            return json.loads(json.dumps({
                "success": True,
                "status": "deduped",
                "message": "Duplicate notification prevented (already sent within 5 minutes)"
            }))
        
        # Generate notification
        notification_id = _generate_notification_id(NotificationType.ORDER_CONFIRMATION, recipient)
        
        subject = f"Order Confirmation - {order_id}"
        message = f"""
Dear {customer_name},

Thank you for your order! We're excited to serve you.

Order Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order ID: {order_id}
Service: {service_type or 'N/A'}
Total Amount: ${f'{total_amount:.2f}' if total_amount is not None else '0.00'}

Your order has been confirmed and is now being processed.

Next Steps:
1. Payment validation
2. Installation scheduling
3. Service activation

You'll receive updates via email and SMS as your order progresses.

Questions? Contact us at 1-800-BUSINESS

Thank you for choosing our services!
"""
        
        notification = Notification(
            notification_id=notification_id,
            notification_type=NotificationType.ORDER_CONFIRMATION,
            recipient_email=customer_email,
            recipient_phone=customer_phone,
            subject=subject,
            message=message,
            metadata={
                "order_id": order_id,
                "customer_name": customer_name,
                "service_type": service_type,
                "total_amount": total_amount
            }
        )
        
        # Send via real or simulated channels
        channels_sent = []
        email_detail = None
        if customer_email:
            email_result = _send_email(customer_email, subject, message)
            if email_result["sent"]:
                notification.mark_sent("email")
                channels_sent.append("email")
            email_detail = email_result["detail"]
        
        if customer_phone:
            # SMS remains simulated (real SMS requires Twilio or similar)
            notification.mark_sent("sms")
            channels_sent.append("sms")
            logger.info(f"[SIMULATED] SMS sent to {customer_phone}")
        
        # Store notification
        _NOTIFICATIONS[notification_id] = notification
        
        return json.loads(json.dumps({
            "success": True,
            "notification_id": notification_id,
            "notification_type": NotificationType.ORDER_CONFIRMATION,
            "channels": channels_sent,
            "recipient_email": customer_email,
            "recipient_phone": customer_phone,
            "status": "sent",
            "email_delivery": email_detail,
            "message": f"Order confirmation sent successfully via {', '.join(channels_sent)}"
        }))
    
    except Exception as e:
        logger.error(f"Error sending order confirmation: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Notification error: {str(e)}"
        }))


def send_payment_notification(
    order_id: str,
    customer_name: str,
    customer_email: str = None,
    customer_phone: str = None,
    payment_status: str = "success",
    amount: float = None,
    payment_method: str = None
) -> Dict[str, Any]:
    """
    Send payment status notification (success or failure).
    
    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone
        payment_status: Payment status ("success" or "failed")
        amount: Payment amount
        payment_method: Payment method used
    
    Returns:
        Notification result as JSON
    """
    logger.info(f"Sending payment {payment_status} notification for order {order_id}")
    
    try:
        if not customer_email and not customer_phone:
            return json.loads(json.dumps({
                "success": False,
                "error": "No contact information provided"
            }))
        
        recipient = customer_email or customer_phone
        notif_type = NotificationType.PAYMENT_SUCCESS if payment_status == "success" else NotificationType.PAYMENT_FAILED
        
        if _check_duplicate(notif_type, recipient):
            return json.loads(json.dumps({
                "success": True,
                "status": "deduped",
                "message": "Duplicate notification prevented"
            }))
        
        notification_id = _generate_notification_id(notif_type, recipient)
        
        if payment_status == "success":
            subject = f"Payment Processed - Order {order_id}"
            message = f"""
Dear {customer_name},

Your payment has been processed successfully!

Payment Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order ID: {order_id}
Amount: ${f'{amount:.2f}' if amount is not None else 'N/A'}
Payment Method: {payment_method or 'N/A'}
Status: ✓ Paid

Your order is now confirmed and will proceed to fulfillment.

Next step: Installation scheduling

Thank you!
"""
        else:
            subject = f"Payment Failed - Order {order_id}"
            message = f"""
Dear {customer_name},

We were unable to process your payment for order {order_id}.

Order ID: {order_id}
Amount: ${f'{amount:.2f}' if amount is not None else 'N/A'}
Status: ✗ Payment Failed

Action Required:
Please update your payment method or contact us at 1-800-BUSINESS

Your order is on hold until payment is received.
"""
        
        notification = Notification(
            notification_id=notification_id,
            notification_type=notif_type,
            recipient_email=customer_email,
            recipient_phone=customer_phone,
            subject=subject,
            message=message,
            metadata={
                "order_id": order_id,
                "payment_status": payment_status,
                "amount": amount
            }
        )
        
        channels_sent = []
        email_detail = None
        if customer_email:
            email_result = _send_email(customer_email, subject, message)
            if email_result["sent"]:
                notification.mark_sent("email")
                channels_sent.append("email")
            email_detail = email_result["detail"]
        if customer_phone:
            notification.mark_sent("sms")
            channels_sent.append("sms")
            logger.info(f"[SIMULATED] SMS sent to {customer_phone}")
        
        _NOTIFICATIONS[notification_id] = notification
        
        return json.loads(json.dumps({
            "success": True,
            "notification_id": notification_id,
            "notification_type": notif_type,
            "channels": channels_sent,
            "status": "sent",
            "email_delivery": email_detail,
            "message": f"Payment notification sent via {', '.join(channels_sent)}"
        }))
    
    except Exception as e:
        logger.error(f"Error sending payment notification: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Notification error: {str(e)}"
        }))


def send_installation_reminder(
    order_id: str,
    customer_name: str,
    customer_email: str = None,
    customer_phone: str = None,
    installation_date: str = None,
    installation_time: str = None,
    service_address: str = None
) -> Dict[str, Any]:
    """
    Send installation reminder notification (24 hours before).
    
    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone
        installation_date: Installation date
        installation_time: Installation time window
        service_address: Service installation address
    
    Returns:
        Notification result as JSON
    """
    logger.info(f"Sending installation reminder for order {order_id}")
    
    try:
        if not customer_email and not customer_phone:
            return json.loads(json.dumps({
                "success": False,
                "error": "No contact information provided"
            }))
        
        recipient = customer_email or customer_phone
        if _check_duplicate(NotificationType.INSTALLATION_REMINDER, recipient):
            return json.loads(json.dumps({
                "success": True,
                "status": "deduped",
                "message": "Duplicate notification prevented"
            }))
        
        notification_id = _generate_notification_id(NotificationType.INSTALLATION_REMINDER, recipient)
        
        subject = f"Installation Reminder - Tomorrow"
        message = f"""
Dear {customer_name},

This is a friendly reminder about your installation appointment tomorrow.

Installation Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order ID: {order_id}
Date: {installation_date or 'TBD'}
Time: {installation_time or 'TBD'}
Address: {service_address or 'N/A'}

Preparation Checklist:
□ Business representative on-site
□ Access to telecom room available
□ Parking spot reserved for service vehicle
□ Any pets secured

Our technician will call 30 minutes before arrival.

Need to reschedule? Call 1-800-BUSINESS (48-hour notice required)

See you tomorrow!
"""
        
        notification = Notification(
            notification_id=notification_id,
            notification_type=NotificationType.INSTALLATION_REMINDER,
            recipient_email=customer_email,
            recipient_phone=customer_phone,
            subject=subject,
            message=message,
            metadata={
                "order_id": order_id,
                "installation_date": installation_date,
                "installation_time": installation_time
            }
        )
        
        channels_sent = []
        email_detail = None
        if customer_email:
            email_result = _send_email(customer_email, subject, message)
            if email_result["sent"]:
                notification.mark_sent("email")
                channels_sent.append("email")
            email_detail = email_result["detail"]
        if customer_phone:
            notification.mark_sent("sms")
            channels_sent.append("sms")
            logger.info(f"[SIMULATED] SMS sent to {customer_phone}")
        
        _NOTIFICATIONS[notification_id] = notification
        
        return json.loads(json.dumps({
            "success": True,
            "notification_id": notification_id,
            "notification_type": NotificationType.INSTALLATION_REMINDER,
            "channels": channels_sent,
            "status": "sent",
            "email_delivery": email_detail,
            "message": f"Installation reminder sent via {', '.join(channels_sent)}"
        }))
    
    except Exception as e:
        logger.error(f"Error sending installation reminder: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Notification error: {str(e)}"
        }))


def send_service_activated_notification(
    order_id: str,
    customer_name: str,
    customer_email: str = None,
    customer_phone: str = None,
    service_type: str = None,
    account_number: str = None,
    circuit_id: str = None
) -> Dict[str, Any]:
    """
    Send service activation notification.
    
    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone
        service_type: Type of service activated
        account_number: Customer account number
        circuit_id: Service circuit ID
    
    Returns:
        Notification result as JSON
    """
    logger.info(f"Sending service activation notification for order {order_id}")
    
    try:
        if not customer_email and not customer_phone:
            return json.loads(json.dumps({
                "success": False,
                "error": "No contact information provided"
            }))
        
        recipient = customer_email or customer_phone
        if _check_duplicate(NotificationType.SERVICE_ACTIVATED, recipient):
            return json.loads(json.dumps({
                "success": True,
                "status": "deduped",
                "message": "Duplicate notification prevented"
            }))
        
        notification_id = _generate_notification_id(NotificationType.SERVICE_ACTIVATED, recipient)
        
        subject = f"Service Activated - Welcome!"
        message = f"""
Dear {customer_name},

🎉 Great news! Your service is now active!

Service Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order ID: {order_id}
Service: {service_type or 'N/A'}
Account Number: {account_number or 'TBD'}
Circuit ID: {circuit_id or 'TBD'}
Status: ✓ ACTIVE

Your Resources:
• Customer Portal: business.comcast.com
• Technical Support: 1-800-TECH-HELP (24/7)
• Billing Questions: 1-800-BILLING

Thank you for choosing our services. We're here to support your business!

Welcome aboard! 🚀
"""
        
        notification = Notification(
            notification_id=notification_id,
            notification_type=NotificationType.SERVICE_ACTIVATED,
            recipient_email=customer_email,
            recipient_phone=customer_phone,
            subject=subject,
            message=message,
            metadata={
                "order_id": order_id,
                "service_type": service_type,
                "account_number": account_number
            }
        )
        
        channels_sent = []
        email_detail = None
        if customer_email:
            email_result = _send_email(customer_email, subject, message)
            if email_result["sent"]:
                notification.mark_sent("email")
                channels_sent.append("email")
            email_detail = email_result["detail"]
        if customer_phone:
            notification.mark_sent("sms")
            channels_sent.append("sms")
            logger.info(f"[SIMULATED] SMS sent to {customer_phone}")
        
        _NOTIFICATIONS[notification_id] = notification
        
        return json.loads(json.dumps({
            "success": True,
            "notification_id": notification_id,
            "notification_type": NotificationType.SERVICE_ACTIVATED,
            "channels": channels_sent,
            "status": "sent",
            "email_delivery": email_detail,
            "message": f"Service activation notification sent via {', '.join(channels_sent)}"
        }))
    
    except Exception as e:
        logger.error(f"Error sending service activation notification: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Notification error: {str(e)}"
        }))


def send_abandoned_cart_reminder(
    cart_id: str,
    customer_name: str,
    customer_email: str = None,
    customer_phone: str = None,
    cart_items: str = None,
    total_amount: float = None
) -> Dict[str, Any]:
    """
    Send abandoned cart recovery notification.
    
    Args:
        cart_id: Cart identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone
        cart_items: Description of cart items
        total_amount: Total cart amount
    
    Returns:
        Notification result as JSON
    """
    logger.info(f"Sending abandoned cart reminder for cart {cart_id}")
    
    try:
        if not customer_email and not customer_phone:
            return json.loads(json.dumps({
                "success": False,
                "error": "No contact information provided"
            }))
        
        recipient = customer_email or customer_phone
        if _check_duplicate(NotificationType.ABANDONED_CART, recipient):
            return json.loads(json.dumps({
                "success": True,
                "status": "deduped",
                "message": "Duplicate notification prevented"
            }))
        
        notification_id = _generate_notification_id(NotificationType.ABANDONED_CART, recipient)
        
        subject = "Complete Your Order - Your Quote is Waiting"
        message = f"""
Dear {customer_name},

You're so close! Complete your order and get started with our services.

Your Quote:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cart ID: {cart_id}
Items: {cart_items or 'Your selected services'}
Total: ${f'{total_amount:.2f}' if total_amount is not None else 'TBD'}

Don't miss out! This quote expires in 7 days.

Complete Your Order:
Visit business.comcast.com or call 1-800-BUSINESS

Questions? We're here to help!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

P.S. Need help choosing the right service? Our sales team is standing by!
"""
        
        notification = Notification(
            notification_id=notification_id,
            notification_type=NotificationType.ABANDONED_CART,
            recipient_email=customer_email,
            recipient_phone=customer_phone,
            subject=subject,
            message=message,
            metadata={
                "cart_id": cart_id,
                "cart_items": cart_items,
                "total_amount": total_amount
            }
        )
        
        channels_sent = []
        email_detail = None
        if customer_email:
            email_result = _send_email(customer_email, subject, message)
            if email_result["sent"]:
                notification.mark_sent("email")
                channels_sent.append("email")
            email_detail = email_result["detail"]
        if customer_phone:
            # SMS only if explicitly opted in for marketing
            pass  # Skip SMS for marketing messages unless opt-in
        
        _NOTIFICATIONS[notification_id] = notification
        
        return json.loads(json.dumps({
            "success": True,
            "notification_id": notification_id,
            "notification_type": NotificationType.ABANDONED_CART,
            "channels": channels_sent,
            "status": "sent",
            "email_delivery": email_detail,
            "message": f"Abandoned cart reminder sent via {', '.join(channels_sent)}" if channels_sent else "Abandoned cart reminder queued (email only)"
        }))
    
    except Exception as e:
        logger.error(f"Error sending abandoned cart reminder: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Notification error: {str(e)}"
        }))


def send_order_status_update(
    order_id: str,
    customer_name: str,
    customer_email: str = None,
    customer_phone: str = None,
    old_status: str = None,
    new_status: str = None,
    status_message: str = None
) -> Dict[str, Any]:
    """
    Send order status update notification.
    
    Args:
        order_id: Order identifier
        customer_name: Customer name
        customer_email: Customer email
        customer_phone: Customer phone
        old_status: Previous order status
        new_status: New order status
        status_message: Status update message
    
    Returns:
        Notification result as JSON
    """
    logger.info(f"Sending order status update for order {order_id}: {old_status} -> {new_status}")
    
    try:
        if not customer_email and not customer_phone:
            return json.loads(json.dumps({
                "success": False,
                "error": "No contact information provided"
            }))
        
        recipient = customer_email or customer_phone
        if _check_duplicate(NotificationType.ORDER_STATUS_UPDATE, recipient):
            return json.loads(json.dumps({
                "success": True,
                "status": "deduped",
                "message": "Duplicate notification prevented"
            }))
        
        notification_id = _generate_notification_id(NotificationType.ORDER_STATUS_UPDATE, recipient)
        
        subject = f"Order Update - {order_id}"
        message = f"""
Dear {customer_name},

Your order status has been updated.

Order Status Update:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order ID: {order_id}
Previous Status: {old_status or 'N/A'}
New Status: {new_status or 'N/A'}

{status_message or 'Your order is progressing as scheduled.'}

Track your order: business.comcast.com/orders/{order_id}

Questions? Contact us at 1-800-BUSINESS
"""
        
        notification = Notification(
            notification_id=notification_id,
            notification_type=NotificationType.ORDER_STATUS_UPDATE,
            recipient_email=customer_email,
            recipient_phone=customer_phone,
            subject=subject,
            message=message,
            metadata={
                "order_id": order_id,
                "old_status": old_status,
                "new_status": new_status
            }
        )
        
        channels_sent = []
        email_detail = None
        if customer_email:
            email_result = _send_email(customer_email, subject, message)
            if email_result["sent"]:
                notification.mark_sent("email")
                channels_sent.append("email")
            email_detail = email_result["detail"]
        if customer_phone:
            notification.mark_sent("sms")
            channels_sent.append("sms")
            logger.info(f"[SIMULATED] SMS sent to {customer_phone}")
        
        _NOTIFICATIONS[notification_id] = notification
        
        return json.loads(json.dumps({
            "success": True,
            "notification_id": notification_id,
            "notification_type": NotificationType.ORDER_STATUS_UPDATE,
            "channels": channels_sent,
            "status": "sent",
            "email_delivery": email_detail,
            "message": f"Order status update sent via {', '.join(channels_sent)}"
        }))
    
    except Exception as e:
        logger.error(f"Error sending order status update: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Notification error: {str(e)}"
        }))


def get_notification_history(
    customer_email: str = None,
    customer_phone: str = None,
    notification_type: str = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieve notification history for a customer.
    
    Args:
        customer_email: Customer email
        customer_phone: Customer phone
        notification_type: Filter by notification type
        limit: Maximum number of notifications to return
    
    Returns:
        Notification history as JSON
    """
    logger.info(f"Retrieving notification history for {customer_email or customer_phone}")
    
    try:
        if not customer_email and not customer_phone:
            return json.loads(json.dumps({
                "success": False,
                "error": "No contact information provided"
            }))
        
        # Filter notifications
        filtered = []
        for notif in _NOTIFICATIONS.values():
            if customer_email and notif.recipient_email != customer_email:
                continue
            if customer_phone and notif.recipient_phone != customer_phone:
                continue
            if notification_type and notif.notification_type != notification_type:
                continue
            filtered.append(notif.to_dict())
        
        # Sort by created_at descending
        filtered.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Limit results
        filtered = filtered[:limit]
        
        return json.loads(json.dumps({
            "success": True,
            "count": len(filtered),
            "notifications": filtered,
            "message": f"Retrieved {len(filtered)} notifications"
        }))
    
    except Exception as e:
        logger.error(f"Error retrieving notification history: {e}")
        return json.loads(json.dumps({
            "success": False,
            "error": f"Notification history error: {str(e)}"
        }))
