"""
Payment processing tools for the Payment Agent (PostgreSQL via ``sales_common.db``).

Hardened with:
  Critical  #1  Idempotency keys - UUID per payment intent; retries return the stored result
  Critical  #2  Duplicate-payment guard - completed payment for the order is returned, not re-charged
  Critical  #4  State machine - initiated -> processing -> completed/failed
  High      #7  Velocity-aware approval - amount bands + daily spend/count window
  High      #8  Concurrency - order row lock (SELECT ... FOR UPDATE) + advisory lock on the
                idempotency key, plus the ``uq_payments_order`` partial unique index
  High      #9  Per-customer hourly rate limiting (max 5 attempts/hour)
  Medium   #10  Immutable payment_events audit trail
  Medium   #14  failure_reason persisted on decline

Everything (payment row, audit events, rate-limit counter, ``orders.status='paid'`` and the
``payment_confirmation`` notification outbox row) is written in ONE database transaction.
There is no in-memory fallback: when ``DATABASE_URL`` is unset ``sales_common.db`` raises.

``tokenize_payment_method`` issues opaque random tokens (``tok_...``) and, like
``add_payment_method``, stores only masked method data in ``customer_payment_methods``;
``get_payment_methods`` reads the customer's active methods from there.
"""

import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import psycopg
from google.adk.tools.tool_context import ToolContext

from sales_common import db, notifications
from sales_common.ids import new_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MAX_SINGLE_AMOUNT = 100_000.00    # Hard upper bound per single transaction
_MAX_DAILY_SPEND = 500_000.00      # Daily cumulative spend limit per customer
_MAX_DAILY_COUNT = 10              # Daily transaction count limit per customer
_MAX_ATTEMPTS_PER_HOUR = 5         # Rate-limit: max payment attempts per customer/hour
_VALID_CURRENCIES = frozenset({"USD", "CAD", "EUR", "GBP", "AUD"})
_PAYABLE_ORDER_STATUSES = frozenset({"pending_payment", "draft"})


# ---------------------------------------------------------------------------
# DB helpers (all take the caller's transaction connection)
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _record_payment_event(
    conn: psycopg.Connection,
    payment_id: str,
    from_status: Optional[str],
    to_status: str,
    actor: str = "payment_agent",
    note: Optional[str] = None,
) -> None:
    """Append an immutable row to payment_events (audit trail - never updated)."""
    event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    conn.execute(
        """INSERT INTO payment_events
           (event_id, payment_id, from_status, to_status, actor, note, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (event_id, payment_id, from_status, to_status, actor, note, db.now_iso()),
    )


def _rate_limit_window() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H")


def _check_rate_limit(conn: psycopg.Connection, customer_id: str) -> bool:
    """Return True if customer is within the hourly limit, False if exceeded."""
    if not customer_id:
        return True
    row = conn.execute(
        "SELECT attempt_count FROM payment_rate_limit WHERE customer_id=%s AND window_start=%s",
        (customer_id, _rate_limit_window()),
    ).fetchone()
    return not (row and row["attempt_count"] >= _MAX_ATTEMPTS_PER_HOUR)


def _increment_rate_limit(conn: psycopg.Connection, customer_id: str) -> None:
    """Increment the per-hour attempt counter for a customer (upsert)."""
    if not customer_id:
        return
    conn.execute(
        """INSERT INTO payment_rate_limit (customer_id, window_start, attempt_count)
           VALUES (%s, %s, 1)
           ON CONFLICT (customer_id, window_start)
           DO UPDATE SET attempt_count = payment_rate_limit.attempt_count + 1""",
        (customer_id, _rate_limit_window()),
    )


def _enqueue_payment_notification(
    conn: psycopg.Connection,
    *,
    order_id: str,
    customer_id: str,
    customer_name: Optional[str],
    customer_email: Optional[str],
    customer_phone: Optional[str],
    payment_status: str,
    amount: float,
    currency: str,
    payment_method: str,
    transaction_id: Optional[str],
    failure_reason: Optional[str] = None,
) -> Optional[str]:
    """Insert a ``payment_confirmation`` outbox row in the payment transaction."""
    return notifications.enqueue(
        "payment_confirmation",
        recipient_email=customer_email,
        recipient_phone=customer_phone,
        customer_id=customer_id or None,
        order_id=order_id or None,
        args={
            "order_id": order_id,
            "customer_name": customer_name or "Valued Customer",
            "payment_status": payment_status,  # "success" | "failed"
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "transaction_id": transaction_id,
            "failure_reason": failure_reason,
        },
        conn=conn,
    )


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def validate_payment_method(
    payment_type: str,
    card_number: str = None,
    routing_number: str = None,
    account_number: str = None,
) -> Dict[str, Any]:
    """
    Validates a payment method (credit card or ACH).

    Args:
        payment_type: 'credit_card' or 'ach'
        card_number: Credit card number (credit_card only)
        routing_number: Bank routing number (ach only)
        account_number: Bank account number (ach only)

    Returns:
        dict with 'valid' bool and details or 'error' message
    """
    logger.info("Validating payment method: %s", payment_type)
    if payment_type == "credit_card":
        if not card_number:
            return {"valid": False, "error": "Card number is required for credit card validation"}
        clean_number = str(card_number).replace(" ", "").replace("-", "")
        if not _luhn_check(clean_number):
            return {"valid": False, "error": "Invalid card number (failed Luhn check)"}
        card_brand = _get_card_brand(clean_number)
        return {
            "valid": True,
            "payment_type": "credit_card",
            "card_brand": card_brand,
            "last_four": clean_number[-4:],
            "message": f"Valid {card_brand} card ending in {clean_number[-4:]}",
        }
    if payment_type == "ach":
        if not routing_number or not account_number:
            return {"valid": False, "error": "Routing and account numbers required for ACH validation"}
        routing_number = str(routing_number)
        account_number = str(account_number)
        if not routing_number.isdigit() or len(routing_number) != 9:
            return {"valid": False, "error": "Invalid routing number (must be 9 digits)"}
        return {
            "valid": True,
            "payment_type": "ach",
            "routing_number": routing_number,
            "account_last_four": account_number[-4:],
            "message": f"Valid ACH account ending in {account_number[-4:]}",
        }
    return {"valid": False, "error": f"Unsupported payment type: {payment_type}"}


# ---------------------------------------------------------------------------
# Core payment processing
# ---------------------------------------------------------------------------

def process_payment(
    amount: float,
    payment_method_token: str,
    description: str = None,
    invoice_id: str = None,
    order_id: str = None,
    customer_name: str = None,
    customer_email: str = None,
    customer_phone: str = None,
    idempotency_key: str = None,
    currency: str = "USD",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """
    Processes a payment for an order with idempotency, duplicate guard, state machine,
    rate limiting and an immutable audit trail. On success the order status becomes
    'paid' and a payment confirmation notification is queued.

    Args:
        amount: Payment amount (positive number)
        payment_method_token: Secure token from tokenize_payment_method
        description: Transaction description
        invoice_id: Associated invoice ID (informational)
        order_id: Order being paid (defaults to order_context.order_id)
        customer_name: Customer name (for the notification)
        customer_email: Customer email (for the notification)
        customer_phone: Customer phone (for the notification)
        idempotency_key: Client-generated UUID; retries with the same key return the stored result
        currency: ISO 4217 currency code (default USD)

    Returns:
        dict with success, payment_id, transaction_id, status and message
    """
    if tool_context is not None:
        order_ctx = tool_context.state.get("order_context") or {}
        if not order_id and isinstance(order_ctx.get("order_id"), str):
            order_id = order_ctx["order_id"]
        if not customer_name and isinstance(order_ctx.get("customer_name"), str):
            customer_name = order_ctx["customer_name"]
        if not customer_email and isinstance(order_ctx.get("contact_email"), str):
            customer_email = order_ctx["contact_email"]
        if not customer_phone and isinstance(order_ctx.get("contact_phone"), str):
            customer_phone = order_ctx["contact_phone"]

    logger.info(
        "Processing payment: amount=%s token=...%s order=%s",
        amount, str(payment_method_token)[-8:], order_id,
    )

    # -- Input validation -----------------------------------------------------
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
        return {"success": False, "error": "Payment amount must be greater than $0"}
    amount = float(amount)
    if amount > _MAX_SINGLE_AMOUNT:
        return {
            "success": False,
            "error": f"Amount ${amount:,.2f} exceeds single-transaction limit of ${_MAX_SINGLE_AMOUNT:,.2f}",
        }
    currency = str(currency or "USD").upper()
    if currency not in _VALID_CURRENCIES:
        return {
            "success": False,
            "error": f"Unsupported currency '{currency}'. Allowed: {sorted(_VALID_CURRENCIES)}",
        }
    if not payment_method_token:
        return {"success": False, "error": "payment_method_token is required"}
    if not order_id:
        return {
            "success": False,
            "error": "order_id is required (no order in context). Ask the customer for the order ID.",
        }

    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())

    try:
        with db.transaction() as conn:
            # High #8: serialize concurrent attempts for the same idempotency key.
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (idempotency_key,))

            # Critical #1: idempotent replay
            existing = conn.execute(
                "SELECT payment_id, transaction_id, status, amount FROM payments WHERE idempotency_key=%s",
                (idempotency_key,),
            ).fetchone()
            if existing:
                logger.info("Idempotent replay: key=%s -> %s", idempotency_key, existing["payment_id"])
                return {
                    "success": existing["status"] == "completed",
                    "idempotent": True,
                    "payment_id": existing["payment_id"],
                    "transaction_id": existing["transaction_id"],
                    "amount": existing["amount"],
                    "status": existing["status"],
                    "message": f"Idempotent response: payment already {existing['status']}",
                }

            # High #8: lock the order row; serializes payments for the same order.
            order = conn.execute(
                "SELECT order_id, customer_id, status FROM orders WHERE order_id=%s FOR UPDATE",
                (order_id,),
            ).fetchone()
            if order is None:
                return {"success": False, "error": f"Order {order_id} not found"}
            resolved_customer_id = order["customer_id"] or ""

            # Critical #2: duplicate order guard
            done = conn.execute(
                "SELECT payment_id, transaction_id FROM payments WHERE order_id=%s AND status='completed'",
                (order_id,),
            ).fetchone()
            if done:
                logger.warning("Duplicate payment attempt for already-completed order %s", order_id)
                return {
                    "success": True,
                    "idempotent": True,
                    "payment_id": done["payment_id"],
                    "transaction_id": done["transaction_id"],
                    "status": "completed",
                    "message": f"Payment for order {order_id} was already processed successfully.",
                }

            # Only open orders can be charged. Checked under the row lock, after the
            # duplicate guard (a completed payment is returned, never re-charged) and
            # before any rate-limit counter, payments row or notification is written.
            order_status = order["status"]
            if order_status not in _PAYABLE_ORDER_STATUSES:
                logger.warning("Refusing payment for order %s in status %s", order_id, order_status)
                return {
                    "success": False,
                    "order_id": order_id,
                    "order_status": order_status,
                    "error": f"Order {order_id} cannot be paid in status {order_status}",
                }

            # High #9: per-customer hourly rate limit
            if not _check_rate_limit(conn, resolved_customer_id):
                logger.warning("Rate limit exceeded for customer %s", resolved_customer_id)
                return {
                    "success": False,
                    "error": (
                        "Too many payment attempts. "
                        f"Maximum {_MAX_ATTEMPTS_PER_HOUR} per hour. Please try again later."
                    ),
                }

            # Critical #4: state machine - initiated
            now = db.now_iso()
            payment_id = f"PAY-{_utc_now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4).upper()}"
            conn.execute(
                """INSERT INTO payments
                   (payment_id, order_id, customer_id, transaction_id, idempotency_key,
                    amount, currency, status, payment_method, created_at, updated_at, expires_at)
                   VALUES (%s, %s, %s, NULL, %s, %s, %s, 'initiated', %s, %s, %s, %s)""",
                (
                    payment_id, order_id, resolved_customer_id, idempotency_key,
                    amount, currency, payment_method_token, now, now,
                    db.compute_expires_at(now, "payment"),
                ),
            )
            _record_payment_event(conn, payment_id, None, "initiated", note="Payment intent created")
            _increment_rate_limit(conn, resolved_customer_id)

            # initiated -> processing
            conn.execute(
                "UPDATE payments SET status='processing', updated_at=%s WHERE payment_id=%s",
                (db.now_iso(), payment_id),
            )
            _record_payment_event(conn, payment_id, "initiated", "processing", note="Gateway call started")

            # High #7: velocity-aware approval simulation (replace with a real gateway call)
            failure_reason = None
            approved = True
            if resolved_customer_id:
                since = (_utc_now() - timedelta(hours=24)).isoformat(timespec="seconds")
                recent = conn.execute(
                    """SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total
                       FROM payments
                       WHERE customer_id=%s AND status='completed' AND created_at >= %s
                         AND payment_id <> %s""",
                    (resolved_customer_id, since, payment_id),
                ).fetchone()
                daily_count = recent["cnt"] or 0
                daily_total = float(recent["total"] or 0.0)
                if daily_count >= _MAX_DAILY_COUNT:
                    approved = False
                    failure_reason = f"Daily transaction count limit exceeded ({_MAX_DAILY_COUNT}/day)"
                elif (daily_total + amount) > _MAX_DAILY_SPEND:
                    approved = False
                    failure_reason = f"Daily cumulative spend limit exceeded (${_MAX_DAILY_SPEND:,.0f}/day)"

            transaction_id = None
            if approved:
                transaction_id = f"TXN-{secrets.token_hex(8).upper()}"
                conn.execute(
                    """UPDATE payments SET status='completed', transaction_id=%s, updated_at=%s
                       WHERE payment_id=%s""",
                    (transaction_id, db.now_iso(), payment_id),
                )
                _record_payment_event(
                    conn, payment_id, "processing", "completed",
                    note=f"Transaction {transaction_id} approved",
                )
                conn.execute(
                    "UPDATE orders SET status='paid', updated_at=%s WHERE order_id=%s",
                    (db.now_iso(), order_id),
                )
            else:
                conn.execute(
                    """UPDATE payments SET status='failed', failure_reason=%s, updated_at=%s
                       WHERE payment_id=%s""",
                    (failure_reason, db.now_iso(), payment_id),
                )
                _record_payment_event(conn, payment_id, "processing", "failed", note=failure_reason)

            notification_id = _enqueue_payment_notification(
                conn,
                order_id=order_id,
                customer_id=resolved_customer_id,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                payment_status="success" if approved else "failed",
                amount=amount,
                currency=currency,
                payment_method=payment_method_token,
                transaction_id=transaction_id,
                failure_reason=failure_reason,
            )
    except psycopg.Error as exc:
        logger.error("Payment processing database error: %s", exc)
        return {"success": False, "error": f"Payment processing error: {type(exc).__name__}"}

    if not approved:
        return {
            "success": False,
            "payment_id": payment_id,
            "idempotency_key": idempotency_key,
            "status": "failed",
            "failure_reason": failure_reason,
            "error": failure_reason,
        }

    if tool_context is not None:
        tool_context.state["payment_context"] = {
            "transaction_id": transaction_id,
            "order_id": order_id,
            "customer_id": resolved_customer_id,
            "amount": amount,
            "status": "completed",
            "payment_method": payment_method_token,
        }
    logger.info("Payment %s completed: TXN=%s order=%s", payment_id, transaction_id, order_id)
    return {
        "success": True,
        "payment_id": payment_id,
        "transaction_id": transaction_id,
        "idempotency_key": idempotency_key,
        "order_id": order_id,
        "amount": amount,
        "currency": currency,
        "status": "completed",
        "payment_method_token": payment_method_token,
        "description": description,
        "invoice_id": invoice_id,
        "order_status": "paid",
        "email_confirmation_queued": notification_id is not None,
        "notification_id": notification_id,
        "message": f"Payment of ${amount:,.2f} {currency} approved. Transaction ID: {transaction_id}",
    }


# ---------------------------------------------------------------------------
# Tokenization / saved methods (customer_payment_methods)
# ---------------------------------------------------------------------------
# Tokens are opaque random values (``tok_`` + ``secrets.token_urlsafe``); they are
# never derived from card or account data. Only masked data is stored: brand,
# last four, payment type, account type, card expiry. Full card/account numbers
# and CVV are never stored, logged or returned.

_TOKEN_PREFIX = "tok_"
_LEGACY_TOKEN_RE = re.compile(r"^tok_([a-z]+)_(\d{4})$")  # legacy tok_{brand}_{last4}

SUPPORTED_PAYMENT_METHODS = [
    {"type": "credit_card", "brands": ["visa", "mastercard", "amex", "discover"],
     "description": "Credit and debit cards"},
    {"type": "ach", "account_types": ["checking", "savings"], "description": "ACH bank transfer"},
]


def _new_token() -> str:
    return _TOKEN_PREFIX + secrets.token_urlsafe(24)


def _mask_token(token: Optional[str]) -> str:
    return f"...{str(token)[-6:]}" if token else ""


def _resolve_customer_id(customer_id: Optional[str], tool_context: Optional[ToolContext]) -> Optional[str]:
    """``customer_id`` argument, else ``customer_context`` / ``order_context`` from state."""
    if customer_id:
        return customer_id
    if tool_context is None:
        return None
    for key in ("customer_context", "order_context"):
        ctx = tool_context.state.get(key) or {}
        cid = ctx.get("customer_id") if isinstance(ctx, dict) else None
        if isinstance(cid, str) and cid:
            return cid
    return None


def _method_view(row: Dict[str, Any]) -> Dict[str, Any]:
    """Masked, JSON-safe view of a ``customer_payment_methods`` row."""
    return {
        "method_id": row["method_id"],
        "customer_id": row["customer_id"],
        "token": row["token"],
        "payment_type": row["payment_type"],
        "card_brand": row["card_brand"],
        "last_four": row["last_four"],
        "account_type": row["account_type"],
        "expiry": row["token_expiry"],
        "is_default": bool(row["is_default"]),
        "nickname": row["nickname"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def _save_payment_method(
    *,
    customer_id: str,
    payment_type: str,
    token: str,
    card_brand: Optional[str] = None,
    last_four: Optional[str] = None,
    account_type: Optional[str] = None,
    token_expiry: Optional[str] = None,
    is_default: bool = False,
    nickname: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Upsert a masked method by token. Returns the stored row, or None when the
    token already belongs to another customer."""
    with db.transaction() as conn:
        if is_default:
            conn.execute(
                "UPDATE customer_payment_methods SET is_default = 0 WHERE customer_id = %s AND token <> %s",
                (customer_id, token),
            )
        return conn.execute(
            """INSERT INTO customer_payment_methods
                   (method_id, customer_id, payment_type, token, card_brand, last_four,
                    account_type, is_default, nickname, token_expiry, status, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s)
               ON CONFLICT (token) DO UPDATE SET
                   is_default   = GREATEST(customer_payment_methods.is_default, EXCLUDED.is_default),
                   nickname     = COALESCE(EXCLUDED.nickname, customer_payment_methods.nickname),
                   card_brand   = COALESCE(customer_payment_methods.card_brand, EXCLUDED.card_brand),
                   last_four    = COALESCE(customer_payment_methods.last_four, EXCLUDED.last_four),
                   account_type = COALESCE(customer_payment_methods.account_type, EXCLUDED.account_type),
                   token_expiry = COALESCE(customer_payment_methods.token_expiry, EXCLUDED.token_expiry),
                   status       = 'active'
               WHERE customer_payment_methods.customer_id = EXCLUDED.customer_id
               RETURNING *""",
            (
                new_id("PM", timestamp_format="%Y%m%d%H%M%S"), customer_id, payment_type, token,
                card_brand, last_four, account_type, 1 if is_default else 0, nickname,
                token_expiry, db.now_iso(),
            ),
        ).fetchone()


def tokenize_payment_method(
    payment_type: str,
    card_number: str = None,
    expiry_month: int = None,
    expiry_year: int = None,
    cvv: str = None,
    routing_number: str = None,
    account_number: str = None,
    account_type: str = None,
    customer_id: str = None,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """
    Tokenizes a payment method (simulated gateway tokenization) and saves the masked
    method to the customer's account when a customer is known.

    The token is an opaque random value (``tok_...``); it is never derived from the
    card or account number. CVV and full numbers are never stored.

    Args:
        payment_type: 'credit_card' or 'ach'
        card_number: Card number (for credit cards)
        expiry_month: Expiry month (for credit cards)
        expiry_year: Expiry year (for credit cards)
        cvv: CVV code (for credit cards; never stored)
        routing_number: Routing number (for ACH)
        account_number: Account number (for ACH)
        account_type: 'checking' or 'savings' (for ACH)
        customer_id: Customer to save the method for (defaults to customer_context / order_context)

    Returns:
        Tokenization result with the secure token and masked details
    """
    logger.info("Tokenizing payment method: %s", payment_type)
    card_brand = None
    token_expiry = None
    if payment_type == "credit_card":
        if not all([card_number, expiry_month, expiry_year, cvv]):
            return {"success": False, "error": "Missing required fields for credit card tokenization"}
        validation = validate_payment_method("credit_card", card_number=card_number)
        if not validation.get("valid"):
            return {"success": False, "error": validation.get("error")}
        try:
            month = int(expiry_month)
            year = int(expiry_year)
        except (TypeError, ValueError):
            return {"success": False, "error": "Invalid expiry date values"}
        if not 1 <= month <= 12:
            return {"success": False, "error": "Invalid expiry date values"}
        if year < 100:
            year += 2000
        card_brand = validation["card_brand"]
        last_four = validation["last_four"]
        token_expiry = f"{month:02d}/{year}"
        result: Dict[str, Any] = {
            "success": True,
            "payment_type": "credit_card",
            "card_brand": card_brand,
            "last_four": last_four,
            "expiry": token_expiry,
            "message": "Payment method tokenized successfully",
        }
    elif payment_type == "ach":
        if not all([routing_number, account_number, account_type]):
            return {"success": False, "error": "Missing required fields for ACH tokenization"}
        validation = validate_payment_method(
            "ach", routing_number=routing_number, account_number=account_number
        )
        if not validation.get("valid"):
            return {"success": False, "error": validation.get("error")}
        last_four = validation["account_last_four"]
        result = {
            "success": True,
            "payment_type": "ach",
            "account_type": account_type,
            "account_last_four": last_four,
            "last_four": last_four,
            "routing_number": validation["routing_number"],
            "message": "ACH account tokenized successfully",
        }
    else:
        return {"success": False, "error": f"Unsupported payment type: {payment_type}"}

    token = _new_token()
    result["token"] = token

    resolved_customer_id = _resolve_customer_id(customer_id, tool_context)
    result["customer_id"] = resolved_customer_id
    result["saved"] = False
    if resolved_customer_id:
        try:
            row = _save_payment_method(
                customer_id=resolved_customer_id,
                payment_type=payment_type,
                token=token,
                card_brand=card_brand,
                last_four=last_four,
                account_type=account_type if payment_type == "ach" else None,
                token_expiry=token_expiry,
            )
        except psycopg.Error as exc:
            logger.error("Saving payment method failed: %s", type(exc).__name__)
            result["warning"] = "Token created but the payment method could not be saved"
        else:
            if row is not None:
                result["saved"] = True
                result["method_id"] = row["method_id"]
    logger.info("Tokenized %s ending %s (token %s, saved=%s)",
                payment_type, last_four, _mask_token(token), result["saved"])
    return result


def get_payment_methods(customer_id: str = None, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """
    Retrieves the customer's saved (active) payment methods, masked, plus the payment
    method types this service supports.

    Args:
        customer_id: Unique customer identifier (defaults to customer_context / order_context)

    Returns:
        Saved payment methods (token, type, brand, last four, expiry, default flag, nickname)
    """
    customer_id = _resolve_customer_id(customer_id, tool_context)
    logger.info("Retrieving payment methods for customer: %s", customer_id)
    if not customer_id:
        return {"success": False, "error": "customer_id is required",
                "supported_methods": SUPPORTED_PAYMENT_METHODS}
    try:
        rows = db.fetch_all(
            """SELECT * FROM customer_payment_methods
               WHERE customer_id = %s AND status = 'active'
               ORDER BY is_default DESC, created_at DESC, method_id""",
            (customer_id,),
        )
    except psycopg.Error as exc:
        logger.error("Loading payment methods failed: %s", type(exc).__name__)
        return {"success": False, "error": f"Payment method lookup error: {type(exc).__name__}"}
    payment_methods = [_method_view(r) for r in rows]
    return {
        "success": True,
        "customer_id": customer_id,
        "payment_methods": payment_methods,
        "count": len(payment_methods),
        "supported_methods": SUPPORTED_PAYMENT_METHODS,
    }


def add_payment_method(
    customer_id: str,
    payment_type: str,
    payment_token: str,
    is_default: bool = False,
    nickname: str = None,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """
    Saves a tokenized payment method to a customer's account (customer_payment_methods).

    ALWAYS call tokenize_payment_method first to get a secure token before calling this.
    A token already saved by tokenize_payment_method is updated (default flag, nickname).

    Args:
        customer_id: Customer identifier (defaults to customer_context / order_context)
        payment_type: 'credit_card' or 'ach'
        payment_token: Secure token from tokenize_payment_method
        is_default: Whether to set as default payment method (default: False)
        nickname: Optional friendly name for the payment method

    Returns:
        Success confirmation and the saved (masked) payment method
    """
    customer_id = _resolve_customer_id(customer_id, tool_context)
    logger.info("Adding payment method for customer: %s", customer_id)
    if not customer_id or not payment_token:
        return {"success": False, "error": "customer_id and payment_token are required"}
    if payment_type not in ("credit_card", "ach"):
        return {
            "success": False,
            "error": f"Invalid payment_type: {payment_type}. Must be 'credit_card' or 'ach'",
        }
    if not str(payment_token).startswith(_TOKEN_PREFIX):
        return {"success": False, "error": "payment_token must come from tokenize_payment_method"}

    # Legacy tokens (tok_{brand}_{last4}) carry masked details; opaque tokens do not.
    card_brand = last_four = None
    legacy = _LEGACY_TOKEN_RE.match(payment_token)
    if legacy:
        brand, last_four = legacy.groups()
        card_brand = brand if payment_type == "credit_card" else None
    try:
        row = _save_payment_method(
            customer_id=customer_id,
            payment_type=payment_type,
            token=payment_token,
            card_brand=card_brand,
            last_four=last_four,
            is_default=bool(is_default),
            nickname=nickname,
        )
    except psycopg.Error as exc:
        logger.error("Saving payment method failed: %s", type(exc).__name__)
        return {"success": False, "error": f"Payment method save error: {type(exc).__name__}"}
    if row is None:
        return {"success": False, "error": "payment_token is registered to a different customer"}
    if not row["nickname"]:
        ending = row["last_four"] or _mask_token(payment_token)
        row = dict(row, nickname=f"Payment method ending in {ending}")
    return {
        "success": True,
        "message": f"Payment method saved for customer {customer_id}",
        "payment_method": _method_view(row),
    }


# ---------------------------------------------------------------------------
# Luhn / card-brand helpers
# ---------------------------------------------------------------------------

def _luhn_check(card_number: str) -> bool:
    """Validates card number using the Luhn algorithm."""
    if not card_number.isdigit():
        return False
    digits = [int(d) for d in card_number]
    checksum = 0
    for i in range(len(digits) - 2, -1, -2):
        doubled = digits[i] * 2
        checksum += doubled if doubled < 10 else doubled - 9
    for i in range(len(digits) - 1, -1, -2):
        checksum += digits[i]
    return checksum % 10 == 0


def _get_card_brand(card_number: str) -> str:
    """Determines card brand from card number prefix."""
    if card_number.startswith("4"):
        return "visa"
    if card_number.startswith(("51", "52", "53", "54", "55")):
        return "mastercard"
    if card_number.startswith(("34", "37")):
        return "amex"
    if card_number.startswith("6011") or card_number.startswith("65"):
        return "discover"
    return "unknown"
