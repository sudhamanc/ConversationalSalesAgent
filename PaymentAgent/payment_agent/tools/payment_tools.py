"""
Payment processing tools for the Payment Agent.

These tools handle payment method validation, transaction processing,
and payment method management.
"""

import json
import sys
from typing import Dict, Any
from ..utils.logger import get_logger

logger = get_logger(__name__)


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
