"""Message templates for outbox notifications.

Each producer enqueues ``notifications.metadata_json = {"template": <type>, "args": {...}}``
(see ``sales_common.notifications``). :func:`render` turns that into a subject and
plain-text body using the wording the communication agent has always used.

Every template tolerates missing args (it prints a placeholder such as ``N/A`` or
``TBD``), so a producer that omits an optional key still gets a readable message.
The keys each template reads are listed in :data:`TEMPLATE_ARGS`.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

RULE = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

#: Args keys read by each template (``customer_name`` falls back to
#: ``company_name`` and ``order_id`` falls back to the row's ``order_id`` column).
TEMPLATE_ARGS: dict[str, tuple[str, ...]] = {
    "quote_confirmation": (
        "quote_id", "customer_name", "items_summary", "monthly_total", "term_months", "total_discount",
    ),
    "order_confirmation": ("order_id", "customer_name", "service_type", "total_amount"),
    "payment_confirmation": (
        "order_id", "customer_name", "payment_status", "amount", "currency", "payment_method",
        "transaction_id", "failure_reason",
    ),
    "installation_scheduled": (
        "order_id", "customer_name", "appointment_date", "window", "service_address",
    ),
    "installation_reminder": (
        "order_id", "customer_name", "installation_date", "installation_time", "service_address",
    ),
    "installation_complete": ("order_id", "customer_name", "equipment_installed"),
    "service_activated": (
        "order_id", "customer_name", "service_type", "account_number", "circuit_id",
    ),
    "abandoned_cart": ("cart_id", "customer_name", "cart_items", "total_amount"),
    "order_status_update": (
        "order_id", "customer_name", "old_status", "new_status", "status_message",
    ),
    "quote_expired": ("quote_id", "customer_name", "expired_at"),
    "order_cancelled": ("order_id", "customer_name", "reason"),
    "escalation": ("order_id", "customer_name", "reason", "status"),
    # Enqueued by ServiceFulfillment dispatch_technician.
    "install_dispatched": ("order_id", "customer_name", "technician_name", "technician_phone"),
    "generic": ("subject", "message", "customer_name"),
}


def _text(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _money(value: Any, default: str) -> str:
    """Format a dollar amount with 2 decimals; ``default`` when missing/unparseable."""
    if value is None or value == "":
        return default
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return default


def _name(args: Mapping[str, Any]) -> str:
    return _text(args.get("customer_name") or args.get("company_name"), "Valued Customer")


def _quote_confirmation(a: Mapping[str, Any]) -> tuple[str, str]:
    quote_id = _text(a.get("quote_id"), "N/A")
    term = a.get("term_months")
    term_display = f"{term} months" if term else "N/A"
    discount = _money(a.get("total_discount"), "")
    discount_line = f"Your Savings: ${discount}/mo\n" if discount and float(discount) else ""
    subject = f"Your Quote is Ready - {quote_id}"
    message = f"""
Dear {_name(a)},

Thank you for your interest! Your customised quote is ready.

Quote Details:
{RULE}
Quote ID: {quote_id}
Products: {_text(a.get('items_summary'), 'See attached quote')}
Contract Term: {term_display}
Monthly Total: ${_money(a.get('monthly_total'), 'TBD')}
{discount_line}
This quote is valid for 30 days.

Next Steps:
1. Review the quote details above
2. Reply to this email or call 1-800-BUSINESS to proceed
3. We'll handle installation scheduling and payment setup

Questions? Contact us at 1-800-BUSINESS

We look forward to serving your business!
"""
    return subject, message


def _order_confirmation(a: Mapping[str, Any]) -> tuple[str, str]:
    order_id = _text(a.get("order_id"), "N/A")
    subject = f"Order Confirmation - {order_id}"
    message = f"""
Dear {_name(a)},

Thank you for your order! We're excited to serve you.

Order Details:
{RULE}
Order ID: {order_id}
Service: {_text(a.get('service_type'), 'N/A')}
Total Amount: ${_money(a.get('total_amount'), '0.00')}

Your order has been confirmed and is now being processed.

Next Steps:
1. Payment validation
2. Installation scheduling
3. Service activation

You'll receive updates via email and SMS as your order progresses.

Questions? Contact us at 1-800-BUSINESS

Thank you for choosing our services!
"""
    return subject, message


def _payment_confirmation(a: Mapping[str, Any]) -> tuple[str, str]:
    order_id = _text(a.get("order_id"), "N/A")
    amount = _money(a.get("amount"), "N/A")
    currency = _text(a.get("currency"), "")
    if currency and currency.upper() != "USD" and amount != "N/A":
        amount = f"{amount} {currency.upper()}"
    txn = _text(a.get("transaction_id"), "")
    txn_line = f"Transaction ID: {txn}\n" if txn else ""
    if _text(a.get("payment_status"), "success").lower() in {"success", "succeeded", "approved", "paid"}:
        subject = f"Payment Processed - Order {order_id}"
        message = f"""
Dear {_name(a)},

Your payment has been processed successfully!

Payment Details:
{RULE}
Order ID: {order_id}
Amount: ${amount}
Payment Method: {_text(a.get('payment_method'), 'N/A')}
{txn_line}Status: ✓ Paid

Your order is now confirmed and will proceed to fulfillment.

Next step: Installation scheduling

Thank you!
"""
    else:
        subject = f"Payment Failed - Order {order_id}"
        message = f"""
Dear {_name(a)},

We were unable to process your payment for order {order_id}.

Order ID: {order_id}
Amount: ${amount}
Status: ✗ Payment Failed
Reason: {_text(a.get('failure_reason'), 'Payment could not be processed')}

Action Required:
Please update your payment method or contact us at 1-800-BUSINESS

Your order is on hold until payment is received.
"""
    return subject, message


def _installation_scheduled(a: Mapping[str, Any]) -> tuple[str, str]:
    order_id = _text(a.get("order_id"), "N/A")
    subject = f"Installation Scheduled - Order {order_id}"
    message = f"""Dear {_name(a)},

Your installation has been scheduled!

Installation Details:
{RULE}
Order ID: {order_id}
Date: {_text(a.get('appointment_date'), 'TBD')}
Time Window: {_text(a.get('window'), 'TBD')}
Address: {_text(a.get('service_address'), 'On file')}

Our technician will call 30 minutes before arrival.

Need to reschedule? Call 1-800-BUSINESS (48-hour notice required)
"""
    return subject, message


def _installation_reminder(a: Mapping[str, Any]) -> tuple[str, str]:
    subject = "Installation Reminder - Tomorrow"
    message = f"""
Dear {_name(a)},

This is a friendly reminder about your installation appointment tomorrow.

Installation Details:
{RULE}
Order ID: {_text(a.get('order_id'), 'N/A')}
Date: {_text(a.get('installation_date'), 'TBD')}
Time: {_text(a.get('installation_time'), 'TBD')}
Address: {_text(a.get('service_address'), 'N/A')}

Preparation Checklist:
□ Business representative on-site
□ Access to telecom room available
□ Parking spot reserved for service vehicle
□ Any pets secured

Our technician will call 30 minutes before arrival.

Need to reschedule? Call 1-800-BUSINESS (48-hour notice required)

See you tomorrow!
"""
    return subject, message


def _installation_complete(a: Mapping[str, Any]) -> tuple[str, str]:
    order_id = _text(a.get("order_id"), "N/A")
    equipment = a.get("equipment_installed")
    if isinstance(equipment, (list, tuple)) and equipment:
        equipment_list = ", ".join(str(e) for e in equipment)
    else:
        equipment_list = _text(equipment if isinstance(equipment, str) else None, "Standard equipment")
    subject = f"Installation Complete - Order {order_id}"
    message = f"""Dear {_name(a)},

Your installation is complete!

{RULE}
Order ID: {order_id}
Equipment Installed: {equipment_list}
Status: ✓ Installation Complete

Next Step: Service activation (usually within 1-2 hours)

You'll receive another notification once your service is fully active.

Questions? Call 1-800-BUSINESS
"""
    return subject, message


def _service_activated(a: Mapping[str, Any]) -> tuple[str, str]:
    subject = "Service Activated - Welcome!"
    message = f"""
Dear {_name(a)},

🎉 Great news! Your service is now active!

Service Details:
{RULE}
Order ID: {_text(a.get('order_id'), 'N/A')}
Service: {_text(a.get('service_type'), 'N/A')}
Account Number: {_text(a.get('account_number') or a.get('account_id'), 'TBD')}
Circuit ID: {_text(a.get('circuit_id'), 'TBD')}
Status: ✓ ACTIVE

Your Resources:
• Customer Portal: business.comcast.com
• Technical Support: 1-800-TECH-HELP (24/7)
• Billing Questions: 1-800-BILLING

Thank you for choosing our services. We're here to support your business!

Welcome aboard! 🚀
"""
    return subject, message


def _abandoned_cart(a: Mapping[str, Any]) -> tuple[str, str]:
    subject = "Complete Your Order - Your Quote is Waiting"
    message = f"""
Dear {_name(a)},

You're so close! Complete your order and get started with our services.

Your Quote:
{RULE}
Cart ID: {_text(a.get('cart_id'), 'N/A')}
Items: {_text(a.get('cart_items'), 'Your selected services')}
Total: ${_money(a.get('total_amount'), 'TBD')}

Don't miss out! This quote expires in 7 days.

Complete Your Order:
Visit business.comcast.com or call 1-800-BUSINESS

Questions? We're here to help!
{RULE}

P.S. Need help choosing the right service? Our sales team is standing by!
"""
    return subject, message


def _order_status_update(a: Mapping[str, Any]) -> tuple[str, str]:
    order_id = _text(a.get("order_id"), "N/A")
    subject = f"Order Update - {order_id}"
    message = f"""
Dear {_name(a)},

Your order status has been updated.

Order Status Update:
{RULE}
Order ID: {order_id}
Previous Status: {_text(a.get('old_status'), 'N/A')}
New Status: {_text(a.get('new_status'), 'N/A')}

{_text(a.get('status_message'), 'Your order is progressing as scheduled.')}

Track your order: business.comcast.com/orders/{order_id}

Questions? Contact us at 1-800-BUSINESS
"""
    return subject, message


def _quote_expired(a: Mapping[str, Any]) -> tuple[str, str]:
    quote_id = _text(a.get("quote_id"), "N/A")
    expired = _text(a.get("expired_at"), "")
    expired_line = f"Expired On: {expired}\n" if expired else ""
    subject = f"Your Quote Has Expired - {quote_id}"
    message = f"""Dear {_name(a)},

Your quote has expired.

{RULE}
Quote ID: {quote_id}
{expired_line}
Pricing and availability may have changed since this quote was issued.
We're happy to prepare a fresh quote for you.

Contact: 1-800-BUSINESS
"""
    return subject, message


def _order_cancelled(a: Mapping[str, Any]) -> tuple[str, str]:
    order_id = _text(a.get("order_id"), "N/A")
    subject = f"Order Cancelled - {order_id}"
    message = f"""Dear {_name(a)},

Your order has been cancelled.

{RULE}
Order ID: {order_id}
Reason: {_text(a.get('reason'), 'Payment not received within required timeframe')}

If this was unintentional, please contact us to place a new order.
We're happy to help you get started again.

Contact: 1-800-BUSINESS
"""
    return subject, message


def _escalation(a: Mapping[str, Any]) -> tuple[str, str]:
    order_id = _text(a.get("order_id"), "N/A")
    subject = f"We're Looking Into Your Order - {order_id}"
    message = f"""Dear {_name(a)},

Your order needs attention from our support team, and a specialist has been assigned.

{RULE}
Order ID: {order_id}
Current Status: {_text(a.get('status'), 'In review')}
Reason: {_text(a.get('reason'), 'Order has not progressed within the expected timeframe')}

A member of our team will contact you shortly.

Questions? Call 1-800-BUSINESS
"""
    return subject, message


def _install_dispatched(a: Mapping[str, Any]) -> tuple[str, str]:
    order_id = _text(a.get("order_id"), "N/A")
    subject = f"Technician Dispatched - Order {order_id}"
    message = f"""Dear {_name(a)},

Your technician is on the way!

Dispatch Details:
{RULE}
Order ID: {order_id}
Technician: {_text(a.get('technician_name'), 'Assigned')}
Technician Phone: {_text(a.get('technician_phone'), 'Will call on arrival')}

The technician will call 30 minutes before arrival.
Please ensure access to the installation area is available.

Questions? Call 1-800-BUSINESS
"""
    return subject, message


def _generic(a: Mapping[str, Any]) -> tuple[str, str]:
    subject = _text(a.get("subject"), "Update on Your Account")
    body = _text(a.get("message"), "")
    if not body:
        details = [
            f"{k.replace('_', ' ').title()}: {v}"
            for k, v in a.items()
            if k not in {"subject", "message", "customer_name", "company_name"} and v not in (None, "")
        ]
        body = "\n".join(details) or "There is an update on your account."
    message = f"""Dear {_name(a)},

{body}

Questions? Contact us at 1-800-BUSINESS
"""
    return subject, message


TEMPLATES: dict[str, Callable[[Mapping[str, Any]], tuple[str, str]]] = {
    "quote_confirmation": _quote_confirmation,
    "order_confirmation": _order_confirmation,
    "payment_confirmation": _payment_confirmation,
    "installation_scheduled": _installation_scheduled,
    "installation_reminder": _installation_reminder,
    "installation_complete": _installation_complete,
    "service_activated": _service_activated,
    "abandoned_cart": _abandoned_cart,
    "order_status_update": _order_status_update,
    "quote_expired": _quote_expired,
    "order_cancelled": _order_cancelled,
    "escalation": _escalation,
    "install_dispatched": _install_dispatched,
    "generic": _generic,
}


def render(
    template: str,
    args: Optional[Mapping[str, Any]] = None,
    *,
    order_id: Optional[str] = None,
) -> tuple[str, str]:
    """Return ``(subject, message)`` for ``template``; unknown templates use ``generic``."""
    merged = dict(args or {})
    if order_id and not merged.get("order_id"):
        merged["order_id"] = order_id
    return TEMPLATES.get(template, _generic)(merged)
