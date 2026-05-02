"""
Payment processing tools for the Payment Agent.

Hardened with:
  Critical  #1  Idempotency keys — UUID per payment intent; retries return cached result
  Critical  #2  Duplicate-payment guard — SELECT before INSERT for completed order
  Critical  #4  State machine — initiated → processing → completed/failed/refunded
  High      #5  Cryptographically random tokens (secrets.token_hex)
  High      #6  CVV zero-out — discarded immediately after validation, never stored
  High      #7  Velocity-aware approval — amount bands + daily spend/count window
  High      #8  Threading lock — BEGIN EXCLUSIVE for concurrent request safety
  High      #9  Per-customer hourly rate limiting (max 5 attempts/hour)
  Medium   #10  Immutable payment_events audit trail
  Medium   #11  DB-backed get_payment_methods (customer_payment_methods table)
  Medium   #12  Token expiry tracking (1-year TTL on stored tokens)
  Medium   #14  failure_reason persisted on decline
"""

import json
import os
import secrets
import sqlite3
import sys
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MAX_SINGLE_AMOUNT = 100_000.00    # Hard upper bound per single transaction
_MAX_DAILY_SPEND = 500_000.00      # Daily cumulative spend limit per customer
_MAX_DAILY_COUNT = 10              # Daily transaction count limit per customer
_MAX_ATTEMPTS_PER_HOUR = 5        # Rate-limit: max payment attempts per customer/hour
_TOKEN_EXPIRY_DAYS = 365           # Stored payment tokens valid for 1 year
_VALID_CURRENCIES = frozenset({"USD", "CAD", "EUR", "GBP", "AUD"})

# Module-level lock: prevents race conditions on concurrent process_payment calls
_PAYMENT_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_db_connection() -> Optional[sqlite3.Connection]:
    """Return a WAL-enabled connection to the unified sales_agent.db, or None."""
    db_path = os.getenv("SALES_AGENT_DB_PATH")
    if not db_path:
        return None
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _record_payment_event(
    conn: sqlite3.Connection,
    payment_id: str,
    from_status: Optional[str],
    to_status: str,
    actor: str = "payment_agent",
    note: Optional[str] = None,
) -> None:
    """Append an immutable row to payment_events (audit trail — never updated)."""
    event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    conn.execute(
        """INSERT INTO payment_events
           (event_id, payment_id, from_status, to_status, actor, note, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (event_id, payment_id, from_status, to_status, actor, note, datetime.now().isoformat()),
    )


def _check_rate_limit(conn: sqlite3.Connection, customer_id: str) -> bool:
    """Return True if customer is within hourly limit, False if exceeded."""
    if not customer_id:
        return True
    window = datetime.now().strftime("%Y-%m-%dT%H")
    row = conn.execute(
        "SELECT attempt_count FROM payment_rate_limit WHERE customer_id=? AND window_start=?",
        (customer_id, window),
    ).fetchone()
    return not (row and row["attempt_count"] >= _MAX_ATTEMPTS_PER_HOUR)


def _increment_rate_limit(conn: sqlite3.Connection, customer_id: str) -> None:
    """Increment the per-hour attempt counter for a customer (upsert)."""
    if not customer_id:
        return
    window = datetime.now().strftime("%Y-%m-%dT%H")
    conn.execute(
        """INSERT INTO payment_rate_limit (customer_id, window_start, attempt_count)
           VALUES (?, ?, 1)
           ON CONFLICT(customer_id, window_start)
           DO UPDATE SET attempt_count = attempt_count + 1""",
        (customer_id, window),
    )


def _update_order_status(order_id: str, new_status: str) -> None:
    """Update an order's status in the orders table (best-effort, separate connection)."""
    conn = _get_db_connection()
    if conn is None:
        return
    try:
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE order_id = ?",
            (new_status, now, order_id),
        )
        conn.commit()
        logger.info(f"Order {order_id} status updated to '{new_status}'")
    except Exception as exc:
        logger.warning(f"Failed to update order status (non-fatal): {exc}")
    finally:
        conn.close()


def _auto_send_payment_notification(
    order_id: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    payment_status: str,
    amount: float,
    payment_method: str,
) -> Dict[str, Any]:
    """Send payment notification via CustomerCommunicationAgent (best-effort)."""
    try:
        notif_mod = sys.modules.get("customer_communication_agent.tools.notification_tools")
        if notif_mod is None:
            notif_mod = sys.modules.get("customer_communication_agent.tools")
        if notif_mod is None or not hasattr(notif_mod, "send_payment_notification"):
            logger.warning("CustomerCommunicationAgent not in sys.modules; notification skipped.")
            return {"success": False, "error": "Notification module unavailable"}
        result = notif_mod.send_payment_notification(
            order_id=order_id or "",
            customer_name=customer_name or "Valued Customer",
            customer_email=customer_email or None,
            customer_phone=customer_phone or None,
            payment_status=payment_status,
            amount=amount,
            payment_method=payment_method,
        )
        logger.info(f"Payment notification sent ({payment_status}): {result}")
        return result
    except Exception as exc:
        logger.warning(f"Payment notification failed (non-fatal): {exc}")
        return {"success": False, "error": str(exc)}


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
    logger.info(f"Validating payment method: {payment_type}")
    try:
        if payment_type == "credit_card":
            if not card_number:
                return {"valid": False, "error": "Card number is required for credit card validation"}
            clean_number = card_number.replace(" ", "").replace("-", "")
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
        elif payment_type == "ach":
            if not routing_number or not account_number:
                return {"valid": False, "error": "Routing and account numbers required for ACH validation"}
            if not routing_number.isdigit() or len(routing_number) != 9:
                return {"valid": False, "error": "Invalid routing number (must be 9 digits)"}
            return {
                "valid": True,
                "payment_type": "ach",
                "routing_number": routing_number,
                "account_last_four": account_number[-4:],
                "message": f"Valid ACH account ending in {account_number[-4:]}",
            }
        else:
            return {"valid": False, "error": f"Unsupported payment type: {payment_type}"}
    except Exception as e:
        logger.error(f"Error validating payment method: {e}")
        return {"valid": False, "error": f"Validation error: {str(e)}"}


# ---------------------------------------------------------------------------
# Core payment processing
# Critical #1 #2 #4 | High #7 #8 #9 | Medium #10 #14
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
    idempotency_key: str = None,  # Critical #1: caller-supplied UUID
    currency: str = "USD",
) -> Dict[str, Any]:
    """
    Processes a payment transaction with idempotency, dedup guard, state machine,
    rate limiting, and immutable audit trail.

    Args:
        amount: Payment amount (positive float, USD by default)
        payment_method_token: Secure token from tokenize_payment_method
        description: Transaction description
        invoice_id: Associated invoice ID
        order_id: Associated order ID
        customer_name: Customer name (for notification)
        customer_email: Customer email (for notification)
        customer_phone: Customer phone (for notification)
        idempotency_key: Client-generated UUID; retries with same key return cached result
        currency: ISO 4217 currency code (default USD)

    Returns:
        dict with success, payment_id, transaction_id, status, and message
    """
    logger.info(
        f"Processing payment: ${amount} token=...{str(payment_method_token)[-8:]} order={order_id}"
    )

    # ── Input validation ──────────────────────────────────────────────────
    if not isinstance(amount, (int, float)) or amount <= 0:
        return {"success": False, "error": "Payment amount must be greater than $0"}
    if amount > _MAX_SINGLE_AMOUNT:
        return {
            "success": False,
            "error": f"Amount ${amount:,.2f} exceeds single-transaction limit of ${_MAX_SINGLE_AMOUNT:,.2f}",
        }
    currency = str(currency).upper()
    if currency not in _VALID_CURRENCIES:
        return {
            "success": False,
            "error": f"Unsupported currency '{currency}'. Allowed: {sorted(_VALID_CURRENCIES)}",
        }
    if not payment_method_token:
        return {"success": False, "error": "payment_method_token is required"}

    # Auto-generate idempotency key if caller did not provide one (Critical #1)
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())

    conn = _get_db_connection()
    if conn is None:
        # No DB configured — fall back to in-memory simulation (standalone testing)
        return _simulate_payment_no_db(amount, payment_method_token, idempotency_key, order_id, description)

    try:
        # ── High #8: Exclusive lock — prevents concurrent double-charge ──────
        with _PAYMENT_LOCK:
            conn.execute("BEGIN EXCLUSIVE")

            # ── Critical #1: Idempotency — return cached result if key seen ──
            existing_by_key = conn.execute(
                "SELECT payment_id, transaction_id, status, amount FROM payments WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if existing_by_key:
                conn.execute("ROLLBACK")
                logger.info(
                    f"Idempotent replay: key={idempotency_key} → payment={existing_by_key['payment_id']}"
                )
                return {
                    "success": existing_by_key["status"] == "completed",
                    "idempotent": True,
                    "payment_id": existing_by_key["payment_id"],
                    "transaction_id": existing_by_key["transaction_id"],
                    "amount": existing_by_key["amount"],
                    "status": existing_by_key["status"],
                    "message": f"Idempotent response: payment already {existing_by_key['status']}",
                }

            # ── Critical #2: Duplicate order guard ───────────────────────────
            if order_id:
                existing_for_order = conn.execute(
                    "SELECT payment_id, transaction_id FROM payments WHERE order_id=? AND status='completed'",
                    (order_id,),
                ).fetchone()
                if existing_for_order:
                    conn.execute("ROLLBACK")
                    logger.warning(f"Duplicate payment attempt for already-completed order {order_id}")
                    return {
                        "success": True,
                        "idempotent": True,
                        "payment_id": existing_for_order["payment_id"],
                        "transaction_id": existing_for_order["transaction_id"],
                        "status": "completed",
                        "message": f"Payment for order {order_id} was already processed successfully.",
                    }

            # ── Resolve customer_id from orders table ─────────────────────────
            resolved_customer_id = ""
            if order_id:
                row = conn.execute(
                    "SELECT customer_id FROM orders WHERE order_id=?", (order_id,)
                ).fetchone()
                if row:
                    resolved_customer_id = row["customer_id"] or ""

            # ── High #9: Per-customer hourly rate limiting ────────────────────
            if not _check_rate_limit(conn, resolved_customer_id):
                conn.execute("ROLLBACK")
                logger.warning(f"Rate limit exceeded for customer {resolved_customer_id}")
                return {
                    "success": False,
                    "error": (
                        f"Too many payment attempts. "
                        f"Maximum {_MAX_ATTEMPTS_PER_HOUR} per hour. Please try again later."
                    ),
                }

            # ── Critical #4: State machine — insert in 'initiated' state ─────
            now = datetime.now().isoformat()
            payment_id = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4).upper()}"
            conn.execute(
                """INSERT INTO payments
                   (payment_id, order_id, customer_id, transaction_id, idempotency_key,
                    amount, currency, status, payment_method, created_at, updated_at)
                   VALUES (?, ?, ?, NULL, ?, ?, ?, 'initiated', ?, ?, ?)""",
                (
                    payment_id,
                    order_id or invoice_id or "",
                    resolved_customer_id,
                    idempotency_key,
                    amount,
                    currency,
                    payment_method_token,
                    now,
                    now,
                ),
            )
            _record_payment_event(conn, payment_id, None, "initiated", note="Payment intent created")
            _increment_rate_limit(conn, resolved_customer_id)

            # ── State: initiated → processing ─────────────────────────────────
            conn.execute(
                "UPDATE payments SET status='processing', updated_at=? WHERE payment_id=?",
                (datetime.now().isoformat(), payment_id),
            )
            _record_payment_event(
                conn, payment_id, "initiated", "processing", note="Gateway call started"
            )

            # ── High #7: Velocity-aware approval simulation ───────────────────
            # Production: replace this block with a real payment gateway call.
            # Simulation checks: single amount cap + daily count + daily spend velocity.
            failure_reason = None
            approved = True

            if resolved_customer_id:
                since = (datetime.now() - timedelta(hours=24)).isoformat()
                recent = conn.execute(
                    """SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total
                       FROM payments
                       WHERE customer_id=? AND status='completed' AND created_at >= ? AND payment_id != ?""",
                    (resolved_customer_id, since, payment_id),
                ).fetchone()
                daily_count = recent["cnt"] or 0
                daily_total = recent["total"] or 0.0

                if daily_count >= _MAX_DAILY_COUNT:
                    approved = False
                    failure_reason = f"Daily transaction count limit exceeded ({_MAX_DAILY_COUNT}/day)"
                elif (daily_total + amount) > _MAX_DAILY_SPEND:
                    approved = False
                    failure_reason = f"Daily cumulative spend limit exceeded (${_MAX_DAILY_SPEND:,.0f}/day)"

            # ── State: processing → completed or failed ────────────────────────
            if approved:
                transaction_id = f"TXN-{secrets.token_hex(8).upper()}"
                conn.execute(
                    """UPDATE payments SET status='completed', transaction_id=?, updated_at=?
                       WHERE payment_id=?""",
                    (transaction_id, datetime.now().isoformat(), payment_id),
                )
                _record_payment_event(
                    conn, payment_id, "processing", "completed",
                    note=f"Transaction {transaction_id} approved",
                )
            else:
                conn.execute(
                    """UPDATE payments SET status='failed', failure_reason=?, updated_at=?
                       WHERE payment_id=?""",
                    (failure_reason, datetime.now().isoformat(), payment_id),
                )
                _record_payment_event(
                    conn, payment_id, "processing", "failed", note=failure_reason
                )

            conn.execute("COMMIT")

        # ── Post-commit side effects (outside lock) ──────────────────────────
        if approved:
            if order_id:
                _update_order_status(order_id, "paid")
            notif_result = {}
            if customer_email or customer_phone:
                notif_result = _auto_send_payment_notification(
                    order_id=order_id or invoice_id or "",
                    customer_name=customer_name or "",
                    customer_email=customer_email or "",
                    customer_phone=customer_phone or "",
                    payment_status="success",
                    amount=amount,
                    payment_method=payment_method_token,
                )
            logger.info(f"Payment {payment_id} completed: TXN={transaction_id}")
            return {
                "success": True,
                "payment_id": payment_id,
                "transaction_id": transaction_id,
                "idempotency_key": idempotency_key,
                "amount": amount,
                "currency": currency,
                "status": "completed",
                "payment_method_token": payment_method_token,
                "description": description,
                "invoice_id": invoice_id,
                "email_confirmation_sent": bool(notif_result.get("success")),
                "email_notification_id": notif_result.get("notification_id"),
                "message": (
                    f"Payment of ${amount:,.2f} {currency} approved. "
                    f"Transaction ID: {transaction_id}"
                ),
            }
        else:
            if customer_email or customer_phone:
                _auto_send_payment_notification(
                    order_id=order_id or invoice_id or "",
                    customer_name=customer_name or "",
                    customer_email=customer_email or "",
                    customer_phone=customer_phone or "",
                    payment_status="failed",
                    amount=amount,
                    payment_method=payment_method_token,
                )
            return {
                "success": False,
                "payment_id": payment_id,
                "idempotency_key": idempotency_key,
                "status": "failed",
                "failure_reason": failure_reason,
                "error": failure_reason,
            }

    except Exception as exc:
        logger.error(f"Payment processing error: {exc}")
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return {"success": False, "error": f"Payment processing error: {str(exc)}"}
    finally:
        conn.close()


def _simulate_payment_no_db(
    amount: float,
    payment_method_token: str,
    idempotency_key: str,
    order_id: Optional[str],
    description: Optional[str],
) -> Dict[str, Any]:
    """Fallback simulation when SALES_AGENT_DB_PATH is not configured."""
    if amount <= _MAX_SINGLE_AMOUNT:
        transaction_id = f"TXN-{secrets.token_hex(8).upper()}"
        return {
            "success": True,
            "payment_id": f"PAY-NODB-{secrets.token_hex(4).upper()}",
            "transaction_id": transaction_id,
            "idempotency_key": idempotency_key,
            "amount": amount,
            "currency": "USD",
            "status": "completed",
            "message": f"Payment of ${amount:,.2f} approved (no-DB mode). TXN: {transaction_id}",
        }
    return {
        "success": False,
        "status": "declined",
        "idempotency_key": idempotency_key,
        "failure_reason": "Amount exceeds single-transaction limit",
        "error": "Amount exceeds single-transaction limit",
    }


# ---------------------------------------------------------------------------
# Tokenization — High #5 #6 | Medium #12
# ---------------------------------------------------------------------------

def tokenize_payment_method(
    payment_type: str,
    card_number: str = None,
    expiry_month: int = None,
    expiry_year: int = None,
    cvv: str = None,
    routing_number: str = None,
    account_number: str = None,
    account_type: str = None,
) -> Dict[str, Any]:
    """
    Tokenizes a payment method for secure storage.

    Security:
    - Token is cryptographically random (secrets.token_hex) — not derived from card data (High #5)
    - CVV is validated then immediately zeroed — never stored or logged (High #6)
    - Card expiry validated against current date

    Args:
        payment_type: 'credit_card' or 'ach'
        card_number: Card number (credit cards only)
        expiry_month: Expiry month 1–12 (credit cards only)
        expiry_year: 4-digit expiry year (credit cards only)
        cvv: CVV/CVC — validated then discarded, never stored
        routing_number: Bank routing number (ACH only)
        account_number: Bank account number (ACH only)
        account_type: 'checking' or 'savings' (ACH only)

    Returns:
        dict with secure token, token_expiry, and masked display metadata
    """
    logger.info(f"Tokenizing payment method: {payment_type}")
    try:
        if payment_type == "credit_card":
            if not all([card_number, expiry_month, expiry_year, cvv]):
                return {"success": False, "error": "Missing required fields for credit card tokenization"}

            # High #6: Validate CVV format, then immediately zero out — never log or store
            cvv_str = str(cvv).strip()
            if not cvv_str.isdigit() or len(cvv_str) not in (3, 4):
                cvv_str = None  # zero out before returning
                return {"success": False, "error": "Invalid CVV (must be 3 or 4 digits)"}
            cvv_str = None  # zero out immediately after format check

            # Validate expiry is not in the past
            try:
                now = datetime.now()
                if expiry_year < now.year or (expiry_year == now.year and expiry_month < now.month):
                    return {"success": False, "error": "Card has expired"}
                if not (1 <= expiry_month <= 12):
                    return {"success": False, "error": "Invalid expiry month (must be 1–12)"}
            except (TypeError, ValueError):
                return {"success": False, "error": "Invalid expiry date values"}

            # Validate card number
            validation = validate_payment_method("credit_card", card_number=card_number)
            if not validation.get("valid"):
                return {"success": False, "error": validation.get("error")}

            # High #5: Cryptographically random token — NOT derived from card data
            token = f"tok_{validation['card_brand']}_{secrets.token_hex(16)}"
            last_four = card_number.replace(" ", "").replace("-", "")[-4:]
            token_expiry = (datetime.now() + timedelta(days=_TOKEN_EXPIRY_DAYS)).strftime("%Y-%m-%d")

            return {
                "success": True,
                "token": token,
                "payment_type": "credit_card",
                "card_brand": validation["card_brand"],
                "last_four": last_four,       # display-only, not encoded in token
                "expiry": f"{expiry_month:02d}/{expiry_year}",
                "token_expiry": token_expiry,  # Medium #12
                "message": "Payment method tokenized successfully",
            }

        elif payment_type == "ach":
            if not all([routing_number, account_number, account_type]):
                return {"success": False, "error": "Missing required fields for ACH tokenization"}
            if account_type not in ("checking", "savings"):
                return {"success": False, "error": "account_type must be 'checking' or 'savings'"}

            validation = validate_payment_method(
                "ach", routing_number=routing_number, account_number=account_number
            )
            if not validation.get("valid"):
                return {"success": False, "error": validation.get("error")}

            # High #5: Cryptographically random ACH token
            token = f"tok_ach_{secrets.token_hex(16)}"
            token_expiry = (datetime.now() + timedelta(days=_TOKEN_EXPIRY_DAYS)).strftime("%Y-%m-%d")

            return {
                "success": True,
                "token": token,
                "payment_type": "ach",
                "account_type": account_type,
                "account_last_four": account_number[-4:],
                "routing_number": routing_number,
                "token_expiry": token_expiry,  # Medium #12
                "message": "ACH account tokenized successfully",
            }

        else:
            return {"success": False, "error": f"Unsupported payment type: {payment_type}"}

    except Exception as e:
        logger.error(f"Error tokenizing payment method: {e}")
        return {"success": False, "error": f"Tokenization error: {str(e)}"}


# ---------------------------------------------------------------------------
# Payment method management — Medium #11
# ---------------------------------------------------------------------------

def get_payment_methods(customer_id: str) -> Dict[str, Any]:
    """
    Retrieves active saved payment methods for a customer from the database.

    Args:
        customer_id: Customer identifier

    Returns:
        dict with list of active, non-expired payment methods
    """
    logger.info(f"Retrieving payment methods for customer: {customer_id}")
    if not customer_id:
        return {"success": False, "error": "customer_id is required"}

    conn = _get_db_connection()
    if conn is None:
        return {"success": True, "customer_id": customer_id, "payment_methods": [], "count": 0}

    try:
        rows = conn.execute(
            """SELECT token, payment_type, card_brand, last_four, account_type,
                      is_default, nickname, token_expiry, created_at
               FROM customer_payment_methods
               WHERE customer_id=? AND status='active'
               ORDER BY is_default DESC, created_at DESC""",
            (customer_id,),
        ).fetchall()

        now_date = datetime.now().strftime("%Y-%m-%d")
        methods = []
        for row in rows:
            # Medium #12: skip expired tokens
            if row["token_expiry"] and row["token_expiry"] < now_date:
                continue
            methods.append({
                "token": row["token"],
                "type": row["payment_type"],
                "card_brand": row["card_brand"],
                "last_four": row["last_four"],
                "account_type": row["account_type"],
                "is_default": bool(row["is_default"]),
                "nickname": row["nickname"],
                "token_expiry": row["token_expiry"],
            })

        return {
            "success": True,
            "customer_id": customer_id,
            "payment_methods": methods,
            "count": len(methods),
        }
    except Exception as e:
        logger.error(f"Error retrieving payment methods: {e}")
        return {"success": False, "error": f"Error retrieving payment methods: {str(e)}"}
    finally:
        conn.close()


def add_payment_method(
    customer_id: str,
    payment_type: str,
    payment_token: str,
    is_default: bool = False,
    nickname: str = None,
    card_brand: str = None,
    last_four: str = None,
    account_type: str = None,
    token_expiry: str = None,
) -> str:
    """
    Saves a tokenized payment method to the customer's account in the database.

    ALWAYS call tokenize_payment_method first to obtain a secure token, then pass
    the token and metadata returned by that call into this function.

    Args:
        customer_id: Customer identifier
        payment_type: 'credit_card' or 'ach'
        payment_token: Secure token from tokenize_payment_method
        is_default: Set as default payment method
        nickname: Friendly display name
        card_brand: Card brand from tokenize result (visa/mastercard/amex/discover)
        last_four: Last 4 digits for display (from tokenize result)
        account_type: 'checking'/'savings' for ACH (from tokenize result)
        token_expiry: Token expiry YYYY-MM-DD (from tokenize result)

    Returns:
        JSON string with confirmation
    """
    logger.info(f"Adding payment method for customer: {customer_id}")
    try:
        if not customer_id or not payment_token:
            return json.dumps({"success": False, "error": "customer_id and payment_token are required"})
        if payment_type not in ("credit_card", "ach"):
            return json.dumps({"success": False, "error": f"Invalid payment_type: {payment_type}"})

        if not nickname:
            suffix = last_four or payment_token[-4:]
            nickname = f"{'Card' if payment_type == 'credit_card' else 'Bank account'} ending in {suffix}"

        conn = _get_db_connection()
        if conn is None:
            return json.dumps({
                "success": True,
                "message": f"Payment method saved for customer {customer_id} (no-DB mode)",
                "payment_method": {"token": payment_token, "customer_id": customer_id, "status": "active"},
            })

        try:
            now = datetime.now().isoformat()
            method_id = f"PM-{uuid.uuid4().hex[:12].upper()}"

            # Clear existing defaults if this is being set as default
            if is_default:
                conn.execute(
                    "UPDATE customer_payment_methods SET is_default=0 WHERE customer_id=?",
                    (customer_id,),
                )

            conn.execute(
                """INSERT OR REPLACE INTO customer_payment_methods
                   (method_id, customer_id, payment_type, token, card_brand, last_four,
                    account_type, is_default, nickname, token_expiry, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
                (
                    method_id, customer_id, payment_type, payment_token,
                    card_brand, last_four, account_type, int(is_default),
                    nickname, token_expiry, now,
                ),
            )
            conn.commit()

            return json.dumps({
                "success": True,
                "message": f"Payment method added successfully for customer {customer_id}",
                "payment_method": {
                    "method_id": method_id,
                    "customer_id": customer_id,
                    "payment_type": payment_type,
                    "token": payment_token,
                    "is_default": is_default,
                    "nickname": nickname,
                    "last_four": last_four,
                    "status": "active",
                },
            })
        except Exception as exc:
            logger.error(f"Error saving payment method: {exc}")
            return json.dumps({"success": False, "error": str(exc)})
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error adding payment method: {e}")
        return json.dumps({"success": False, "error": f"Error adding payment method: {str(e)}"})


# ---------------------------------------------------------------------------
# Luhn / card-brand helpers (unchanged)
# ---------------------------------------------------------------------------

def _luhn_check(card_number: str) -> bool:
    """Validates card number using Luhn algorithm."""
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
    elif card_number.startswith(("51", "52", "53", "54", "55")):
        return "mastercard"
    elif card_number.startswith(("34", "37")):
        return "amex"
    elif card_number.startswith("6011") or card_number.startswith("65"):
        return "discover"
    return "unknown"



def _get_db_connection():
    """Return a connection to the unified sales_agent.db, or None if not configured."""
    db_path = os.getenv("SALES_AGENT_DB_PATH")
    if not db_path:
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _persist_payment(
    order_id: str,
    customer_id: str,
    transaction_id: str | None,
    amount: float,
    status: str,
    payment_method: str | None,
    credit_score: int | None,
) -> None:
    """Write a payment record to the payments table (best-effort)."""
    conn = _get_db_connection()
    if conn is None:
        return
    try:
        now = datetime.now().isoformat()
        expires = (datetime.now() + timedelta(minutes=15)).isoformat() if status == "pending" else None
        payment_id = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(order_id) % 10000:04d}"
        conn.execute(
            """INSERT OR REPLACE INTO payments
               (payment_id, order_id, customer_id, transaction_id, amount,
                status, credit_score, payment_method, created_at, updated_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (payment_id, order_id, customer_id, transaction_id, amount,
             status, credit_score, payment_method, now, now, expires),
        )
        conn.commit()
        logger.info(f"Payment {payment_id} persisted: status={status}, amount={amount}")
    except Exception as exc:
        logger.warning(f"Failed to persist payment (non-fatal): {exc}")
    finally:
        conn.close()


def _update_order_status(order_id: str, new_status: str) -> None:
    """Update an order's status in the orders table (best-effort)."""
    conn = _get_db_connection()
    if conn is None:
        return
    try:
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE order_id = ?",
            (new_status, now, order_id),
        )
        conn.commit()
        logger.info(f"Order {order_id} status updated to '{new_status}'")
    except Exception as exc:
        logger.warning(f"Failed to update order status (non-fatal): {exc}")
    finally:
        conn.close()


def validate_payment_method(
    payment_type: str,
    card_number: str = None,
    routing_number: str = None,
    account_number: str = None
) -> Dict[str, Any]:
    """
    Validates a payment method (credit card or ACH).
    
    For production: Integrates with payment gateway (Stripe, Braintree, etc.)
    For testing: Simulates validation logic
    
    Args:
        payment_type: Type of payment ('credit_card' or 'ach')
        card_number: Credit card number (for credit_card type)
        routing_number: Bank routing number (for ach type)
        account_number: Bank account number (for ach type)
    
    Returns:
        Validation result with status and details
    """
    logger.info(f"Validating payment method: {payment_type}")
    
    try:
        if payment_type == "credit_card":
            if not card_number:
                return {
                    "valid": False,
                    "error": "Card number is required for credit card validation"
                }
            
            # Simulate validation (in production, use payment gateway API)
            # Remove spaces and hyphens
            clean_number = card_number.replace(" ", "").replace("-", "")
            
            # Basic Luhn algorithm check
            if not _luhn_check(clean_number):
                return {
                    "valid": False,
                    "error": "Invalid card number (failed Luhn check)"
                }
            
            # Determine card brand
            card_brand = _get_card_brand(clean_number)
            
            return {
                "valid": True,
                "payment_type": "credit_card",
                "card_brand": card_brand,
                "last_four": clean_number[-4:],
                "message": f"Valid {card_brand} card ending in {clean_number[-4:]}"
            }
        
        elif payment_type == "ach":
            if not routing_number or not account_number:
                return {
                    "valid": False,
                    "error": "Routing and account numbers required for ACH validation"
                }
            
            # Validate routing number (9 digits)
            if not routing_number.isdigit() or len(routing_number) != 9:
                return {
                    "valid": False,
                    "error": "Invalid routing number (must be 9 digits)"
                }
            
            return {
                "valid": True,
                "payment_type": "ach",
                "routing_number": routing_number,
                "account_last_four": account_number[-4:],
                "message": f"Valid ACH account ending in {account_number[-4:]}"
            }
        
        else:
            return {
                "valid": False,
                "error": f"Unsupported payment type: {payment_type}"
            }
    
    except Exception as e:
        logger.error(f"Error validating payment method: {e}")
        return {
            "valid": False,
            "error": f"Validation error: {str(e)}"
        }


def _auto_send_payment_notification(
    order_id: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    payment_status: str,
    amount: float,
    payment_method: str,
) -> Dict[str, Any]:
    """
    Automatically send a payment success/failure notification immediately after
    payment processing.  Uses sys.modules to call the already-loaded
    CustomerCommunicationAgent notification tools without a hard cross-package
    import dependency.
    """
    try:
        notif_mod = sys.modules.get("customer_communication_agent.tools.notification_tools")
        if notif_mod is None:
            notif_mod = sys.modules.get("customer_communication_agent.tools")

        if notif_mod is None or not hasattr(notif_mod, "send_payment_notification"):
            logger.warning(
                "CustomerCommunicationAgent notification tools not found in sys.modules; "
                "payment notification will not be sent automatically."
            )
            return {"success": False, "error": "Notification module unavailable"}

        result = notif_mod.send_payment_notification(
            order_id=order_id or "",
            customer_name=customer_name or "Valued Customer",
            customer_email=customer_email or None,
            customer_phone=customer_phone or None,
            payment_status=payment_status,
            amount=amount,
            payment_method=payment_method,
        )
        logger.info(f"Auto payment notification triggered ({payment_status}): {result}")
        return result
    except Exception as exc:
        logger.warning(f"Auto payment notification failed (non-fatal): {exc}")
        return {"success": False, "error": str(exc)}


def process_payment(
    amount: float,
    payment_method_token: str,
    description: str = None,
    invoice_id: str = None,
    order_id: str = None,
    customer_name: str = None,
    customer_email: str = None,
    customer_phone: str = None,
) -> Dict[str, Any]:
    """
    Processes a payment transaction.
    
    For production: Integrates with payment gateway API
    For testing: Simulates payment processing
    
    Args:
        amount: Payment amount in USD
        payment_method_token: Tokenized payment method reference
        description: Transaction description
        invoice_id: Associated invoice ID
        order_id: Associated order ID (for notification)
        customer_name: Customer name (for notification)
        customer_email: Customer email (for notification)
        customer_phone: Customer phone (for notification)
    
    Returns:
        Transaction result with status and details
    """
    logger.info(f"Processing payment: ${amount} using token {payment_method_token}")
    
    try:
        if amount <= 0:
            return {
                "success": False,
                "error": "Payment amount must be greater than $0"
            }
        
        # Simulate payment processing
        # In production: Call payment gateway API (Stripe, Braintree, etc.)
        
        # For testing: simulate approval for amounts < $10000
        if amount < 10000:
            transaction_id = f"TXN-{payment_method_token[-4:]}-{int(amount)}"
            
            # Look up customer_id from the order record
            resolved_customer_id = ""
            if order_id:
                try:
                    _conn = _get_db_connection()
                    if _conn:
                        _row = _conn.execute(
                            "SELECT customer_id FROM orders WHERE order_id = ?",
                            (order_id,),
                        ).fetchone()
                        if _row:
                            resolved_customer_id = _row["customer_id"] or ""
                        _conn.close()
                except Exception:
                    pass  # best-effort lookup

            # Persist payment record to unified DB
            _persist_payment(
                order_id=order_id or invoice_id or "",
                customer_id=resolved_customer_id,
                transaction_id=transaction_id,
                amount=amount,
                status="completed",
                payment_method=payment_method_token,
                credit_score=None,
            )

            # Update order status to 'paid' if order_id is present
            if order_id:
                _update_order_status(order_id, "paid")

            # Automatically send payment success notification
            notif_result = {}
            if customer_email or customer_phone:
                notif_result = _auto_send_payment_notification(
                    order_id=order_id or invoice_id or "",
                    customer_name=customer_name or "",
                    customer_email=customer_email or "",
                    customer_phone=customer_phone or "",
                    payment_status="success",
                    amount=amount,
                    payment_method=payment_method_token,
                )

            return {
                "success": True,
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": "USD",
                "status": "approved",
                "payment_method_token": payment_method_token,
                "description": description,
                "invoice_id": invoice_id,
                "email_confirmation_sent": bool(notif_result.get("success")),
                "email_notification_id": notif_result.get("notification_id"),
                "message": f"Payment of ${amount:.2f} approved. Transaction ID: {transaction_id}"
            }
        else:
            # Persist failed payment record
            _persist_payment(
                order_id=order_id or invoice_id or "",
                customer_id="",
                transaction_id=None,
                amount=amount,
                status="failed",
                payment_method=payment_method_token,
                credit_score=None,
            )

            # Automatically send payment failure notification
            if customer_email or customer_phone:
                _auto_send_payment_notification(
                    order_id=order_id or invoice_id or "",
                    customer_name=customer_name or "",
                    customer_email=customer_email or "",
                    customer_phone=customer_phone or "",
                    payment_status="failed",
                    amount=amount,
                    payment_method=payment_method_token,
                )

            return {
                "success": False,
                "status": "declined",
                "error": "Amount exceeds transaction limit. Please contact support."
            }
    
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        return {
            "success": False,
            "error": f"Payment processing error: {str(e)}"
        }


def get_payment_methods(customer_id: str) -> Dict[str, Any]:
    """
    Retrieves saved payment methods for a customer.
    
    Args:
        customer_id: Unique customer identifier
    
    Returns:
        List of saved payment methods
    """
    logger.info(f"Retrieving payment methods for customer: {customer_id}")
    
    try:
        # Simulate retrieving saved payment methods
        # In production: Query from database or payment gateway
        
        payment_methods = [
            {
                "token": "tok_visa_1234",
                "type": "credit_card",
                "brand": "visa",
                "last_four": "1234",
                "expiry": "12/2026",
                "is_default": True,
                "nickname": "Business Visa"
            },
            {
                "token": "tok_ach_5678",
                "type": "ach",
                "bank_name": "Chase Bank",
                "account_last_four": "5678",
                "is_default": False,
                "nickname": "Business Checking"
            }
        ]
        
        return {
            "success": True,
            "customer_id": customer_id,
            "payment_methods": payment_methods,
            "count": len(payment_methods)
        }
    
    except Exception as e:
        logger.error(f"Error retrieving payment methods: {e}")
        return {
            "success": False,
            "error": f"Error retrieving payment methods: {str(e)}"
        }


def tokenize_payment_method(
    payment_type: str,
    card_number: str = None,
    expiry_month: int = None,
    expiry_year: int = None,
    cvv: str = None,
    routing_number: str = None,
    account_number: str = None,
    account_type: str = None
) -> Dict[str, Any]:
    """
    Tokenizes a payment method for secure storage.
    
    For production: Uses payment gateway tokenization API
    For testing: Simulates token generation
    
    Args:
        payment_type: 'credit_card' or 'ach'
        card_number: Card number (for credit cards)
        expiry_month: Expiry month (for credit cards)
        expiry_year: Expiry year (for credit cards)
        cvv: CVV code (for credit cards)
        routing_number: Routing number (for ACH)
        account_number: Account number (for ACH)
        account_type: 'checking' or 'savings' (for ACH)
    
    Returns:
        Tokenization result with secure token
    """
    logger.info(f"Tokenizing payment method: {payment_type}")
    
    try:
        if payment_type == "credit_card":
            if not all([card_number, expiry_month, expiry_year, cvv]):
                return {
                    "success": False,
                    "error": "Missing required fields for credit card tokenization"
                }
            
            # Validate first
            validation = validate_payment_method("credit_card", card_number=card_number)
            if not validation.get("valid"):
                return {
                    "success": False,
                    "error": validation.get("error")
                }
            
            # Generate token (simulated)
            last_four = card_number.replace(" ", "").replace("-", "")[-4:]
            token = f"tok_{validation['card_brand']}_{last_four}"
            
            return {
                "success": True,
                "token": token,
                "payment_type": "credit_card",
                "card_brand": validation["card_brand"],
                "last_four": last_four,
                "expiry": f"{expiry_month:02d}/{expiry_year}",
                "message": "Payment method tokenized successfully"
            }
        
        elif payment_type == "ach":
            if not all([routing_number, account_number, account_type]):
                return {
                    "success": False,
                    "error": "Missing required fields for ACH tokenization"
                }
            
            # Validate first
            validation = validate_payment_method(
                "ach",
                routing_number=routing_number,
                account_number=account_number
            )
            if not validation.get("valid"):
                return {
                    "success": False,
                    "error": validation.get("error")
                }
            
            # Generate token (simulated)
            last_four = account_number[-4:]
            token = f"tok_ach_{last_four}"
            
            return {
                "success": True,
                "token": token,
                "payment_type": "ach",
                "account_type": account_type,
                "account_last_four": last_four,
                "routing_number": routing_number,
                "message": "ACH account tokenized successfully"
            }
        
        else:
            return {
                "success": False,
                "error": f"Unsupported payment type: {payment_type}"
            }
    
    except Exception as e:
        logger.error(f"Error tokenizing payment method: {e}")
        return {
            "success": False,
            "error": f"Tokenization error: {str(e)}"
        }


# Helper functions

def _luhn_check(card_number: str) -> bool:
    """
    Validates credit card number using Luhn algorithm.
    
    Args:
        card_number: Card number string (digits only)
    
    Returns:
        True if valid, False otherwise
    """
    if not card_number.isdigit():
        return False
    
    digits = [int(d) for d in card_number]
    checksum = 0
    
    # Process digits from right to left
    for i in range(len(digits) - 2, -1, -2):
        doubled = digits[i] * 2
        checksum += doubled if doubled < 10 else doubled - 9
    
    for i in range(len(digits) - 1, -1, -2):
        checksum += digits[i]
    
    return checksum % 10 == 0


def _get_card_brand(card_number: str) -> str:
    """
    Determines card brand from card number.
    
    Args:
        card_number: Card number (digits only)
    
    Returns:
        Card brand name
    """
    if card_number.startswith('4'):
        return 'visa'
    elif card_number.startswith(('51', '52', '53', '54', '55')):
        return 'mastercard'
    elif card_number.startswith(('34', '37')):
        return 'amex'
    elif card_number.startswith('6011') or card_number.startswith('65'):
        return 'discover'
    else:
        return 'unknown'


def add_payment_method(
    customer_id: str,
    payment_type: str,
    payment_token: str,
    is_default: bool = False,
    nickname: str = None
) -> str:
    """
    Adds a tokenized payment method to a customer's account.
    
    This tool saves a validated and tokenized payment method for future use.
    ALWAYS call tokenize_payment_method first to get a secure token before calling this.
    
    Args:
        customer_id: Customer identifier
        payment_type: 'credit_card' or 'ach'
        payment_token: Secure token from tokenize_payment_method
        is_default: Whether to set as default payment method (default: False)
        nickname: Optional friendly name for the payment method
    
    Returns:
        JSON string with success confirmation and saved payment method details
    """
    logger.info(f"Adding payment method for customer: {customer_id}")
    
    try:
        # Simulate saving to database
        # In production: Store in database with customer_id as foreign key
        
        if not customer_id or not payment_token:
            return json.dumps({
                "success": False,
                "error": "customer_id and payment_token are required"
            })
        
        if payment_type not in ["credit_card", "ach"]:
            return json.dumps({
                "success": False,
                "error": f"Invalid payment_type: {payment_type}. Must be 'credit_card' or 'ach'"
            })
        
        # Generate a friendly display name
        if not nickname:
            token_last_four = payment_token[-4:] if len(payment_token) >= 4 else payment_token
            nickname = f"Payment method ending in {token_last_four}"
        
        result = {
            "success": True,
            "message": f"Payment method added successfully for customer {customer_id}",
            "payment_method": {
                "customer_id": customer_id,
                "payment_type": payment_type,
                "token": payment_token,
                "is_default": is_default,
                "nickname": nickname,
                "last_four": payment_token[-4:] if len(payment_token) >= 4 else payment_token,
                "status": "active"
            }
        }
        
        logger.info(f"Payment method added successfully: {nickname}")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error adding payment method: {e}")
        return json.dumps({
            "success": False,
            "error": f"Error adding payment method: {str(e)}"
        })
