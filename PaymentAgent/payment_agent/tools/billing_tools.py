"""
Billing and invoice management tools for the Payment Agent.

These tools handle invoice generation, payment history, and payment plans.
"""

import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

import psycopg

from sales_common import db
from sales_common.ids import new_id

logger = logging.getLogger(__name__)


def generate_invoice(
    customer_name: str,
    line_items_json: str,
    due_date: str = None,
    tax_rate: float = 0.08
) -> Dict[str, Any]:
    """
    Generates an invoice for services.

    Args:
        customer_name: Customer/business name
        line_items_json: JSON string of line items array. Each item must have "description" (str), "quantity" (int), and "unit_price" (float). Example: '[{"description": "Fiber 5G Internet", "quantity": 1, "unit_price": 599.00}]'
        due_date: Payment due date (ISO format), defaults to 30 days from now
        tax_rate: Tax rate (default 8%)

    Returns:
        Generated invoice with totals
    """
    logger.info(f"Generating invoice for: {customer_name}")

    try:
        line_items = json.loads(line_items_json)
    except (json.JSONDecodeError, TypeError):
        return {
            "success": False,
            "error": "Invalid line_items_json format. Must be a valid JSON array string."
        }
    
    try:
        # Calculate totals
        subtotal = sum(item.get('quantity', 1) * item.get('unit_price', 0) for item in line_items)
        tax = subtotal * tax_rate
        total = subtotal + tax
        
        # Parse or set due date
        if due_date:
            due_date_obj = datetime.fromisoformat(due_date)
        else:
            due_date_obj = datetime.now() + timedelta(days=30)
        
        # Generate invoice ID
        invoice_id = new_id("INV")
        
        # Format line items with totals
        formatted_items = []
        for item in line_items:
            quantity = item.get('quantity', 1)
            unit_price = item.get('unit_price', 0)
            item_total = quantity * unit_price
            
            formatted_items.append({
                "description": item.get('description', 'Service'),
                "quantity": quantity,
                "unit_price": unit_price,
                "total": item_total
            })
        
        invoice = {
            "success": True,
            "invoice_id": invoice_id,
            "customer_name": customer_name,
            "issue_date": datetime.now().isoformat(),
            "due_date": due_date_obj.isoformat(),
            "line_items": formatted_items,
            "subtotal": subtotal,
            "tax": tax,
            "tax_rate": tax_rate,
            "total": total,
            "amount_paid": 0.0,
            "balance_due": total,
            "status": "unpaid",
            "message": f"Invoice {invoice_id} generated for ${total:.2f} (due {due_date_obj.strftime('%Y-%m-%d')})"
        }
        
        logger.info(f"Invoice generated: {invoice_id} for ${total:.2f}")
        return invoice
    
    except Exception as e:
        logger.error(f"Error generating invoice: {e}")
        return {
            "success": False,
            "error": f"Invoice generation error: {str(e)}"
        }


def _describe_method(token, payment_type=None, card_brand=None, last_four=None) -> str | None:
    """Masked, typed description of a payment method (never the full token).

    Uses the saved method (customer_payment_methods) when the token is on file,
    else the token prefix (seed tokens look like ``tok_ach_7890``).
    """
    if not token:
        return None
    token = str(token)
    kind = (payment_type or "").lower()
    if not kind:
        kind = "ach" if token.startswith("tok_ach") else "credit_card" if token.startswith(("tok_card", "tok_cc")) else ""
    if kind == "ach":
        return f"ACH bank transfer ending {last_four}" if last_four else f"ACH bank transfer (token ending {token[-4:]})"
    if kind in ("credit_card", "card", "debit_card"):
        brand = f"{card_brand.title()} " if card_brand else ""
        return f"{brand}card ending {last_four}" if last_four else f"Card (token ending {token[-4:]})"
    return f"Saved payment method (token ending {token[-4:]})"


def get_payment_history(
    customer_id: str,
    start_date: str = None,
    end_date: str = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieves a customer's payment history from the payments table, newest first.

    A payment belongs to the customer when its own customer_id matches or, for
    older rows without one, when its order's customer_id matches.

    Args:
        customer_id: Unique customer identifier (CUST-...)
        start_date: Only payments created on or after this date (YYYY-MM-DD, optional)
        end_date: Only payments created on or before this date (YYYY-MM-DD, optional)
        limit: Maximum number of transactions to return (1-100, default 10)

    Returns:
        Payment history: transactions (payment_id, transaction_id, order_id, date,
        amount, currency, status, payment_method masked, failure_reason), count and
        total_amount of completed payments
    """
    logger.info(f"Retrieving payment history for customer: {customer_id}")
    if not customer_id or not str(customer_id).strip():
        return {"success": False, "error": "customer_id is required"}
    try:
        limit = max(1, min(int(limit or 10), 100))
        for label, value in (("start_date", start_date), ("end_date", end_date)):
            if value:
                datetime.fromisoformat(str(value))
    except ValueError:
        return {"success": False, "error": "start_date/end_date must be ISO dates (YYYY-MM-DD) and limit a number"}

    sql = [
        """SELECT p.payment_id, p.transaction_id, p.order_id, p.amount, p.currency, p.status,
                  p.payment_method, p.failure_reason, p.created_at,
                  m.payment_type, m.card_brand, m.last_four
           FROM payments p
           LEFT JOIN orders o ON o.order_id = p.order_id
           LEFT JOIN customer_payment_methods m ON m.token = p.payment_method
           WHERE COALESCE(NULLIF(p.customer_id, ''), o.customer_id) = %s"""
    ]
    params: list = [customer_id.strip()]
    if start_date:
        sql.append("AND p.created_at >= %s")
        params.append(str(start_date))
    if end_date:
        sql.append("AND p.created_at < %s")
        params.append((datetime.fromisoformat(str(end_date)) + timedelta(days=1)).date().isoformat())
    sql.append("ORDER BY p.created_at DESC LIMIT %s")
    params.append(limit)
    try:
        rows = db.fetch_all(" ".join(sql), tuple(params))
    except psycopg.Error as exc:
        logger.error(f"Error retrieving payment history: {type(exc).__name__}")
        return {"success": False, "error": f"Error retrieving payment history: {type(exc).__name__}"}

    transactions = [
        {
            "payment_id": r["payment_id"],
            "transaction_id": r["transaction_id"],
            "order_id": r["order_id"],
            "date": r["created_at"],
            "amount": float(r["amount"]) if r["amount"] is not None else None,
            "currency": r["currency"] or "USD",
            "status": r["status"],
            "payment_method": _describe_method(r["payment_method"], r["payment_type"], r["card_brand"], r["last_four"]),
            "failure_reason": r["failure_reason"],
        }
        for r in rows
    ]
    total_paid = round(sum(t["amount"] or 0 for t in transactions if str(t["status"]).lower() == "completed"), 2)
    return {
        "success": True,
        "customer_id": customer_id.strip(),
        "transactions": transactions,
        "count": len(transactions),
        "total_amount": total_paid,
        "start_date": start_date,
        "end_date": end_date,
        "message": None if transactions else "No payments found for this customer",
    }


def setup_payment_plan(
    total_amount: float,
    num_installments: int,
    start_date: str = None,
    frequency: str = "monthly"
) -> Dict[str, Any]:
    """
    Sets up an installment payment plan.
    
    Args:
        total_amount: Total amount to be paid
        num_installments: Number of installments
        start_date: Start date for first payment (ISO format)
        frequency: Payment frequency (monthly, biweekly, weekly)
    
    Returns:
        Payment plan with installment schedule
    """
    logger.info(f"Setting up payment plan: ${total_amount} over {num_installments} installments")
    
    try:
        if total_amount <= 0:
            return {
                "success": False,
                "error": "Total amount must be greater than $0"
            }
        
        if num_installments < 2:
            return {
                "success": False,
                "error": "Number of installments must be at least 2"
            }
        
        # Calculate installment amount
        installment_amount = total_amount / num_installments
        
        # Parse or set start date (never in the past)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date:
            try:
                start_date_obj = datetime.fromisoformat(str(start_date))
            except ValueError:
                return {"success": False, "error": "start_date must be an ISO date (YYYY-MM-DD)"}
            if start_date_obj < today:
                return {
                    "success": False,
                    "error": f"start_date {start_date} is in the past; today is {today.date().isoformat()}. "
                    "Use today or a later date, or omit it to start in 30 days.",
                }
        else:
            start_date_obj = today + timedelta(days=30)
        
        # Determine interval
        interval_days = {
            "monthly": 30,
            "biweekly": 14,
            "weekly": 7
        }.get(frequency, 30)
        
        # Generate installment schedule
        installments = []
        for i in range(num_installments):
            due_date = start_date_obj + timedelta(days=interval_days * i)
            installments.append({
                "installment_number": i + 1,
                "due_date": due_date.isoformat(),
                "amount": installment_amount,
                "status": "pending"
            })
        
        plan_id = new_id("PLAN")
        
        plan = {
            "success": True,
            "plan_id": plan_id,
            "total_amount": total_amount,
            "num_installments": num_installments,
            "installment_amount": installment_amount,
            "frequency": frequency,
            "start_date": start_date_obj.isoformat(),
            "installments": installments,
            "message": f"Payment plan created: {num_installments} payments of ${installment_amount:.2f} {frequency}"
        }
        
        logger.info(f"Payment plan created: {plan_id}")
        return plan
    
    except Exception as e:
        logger.error(f"Error setting up payment plan: {e}")
        return {
            "success": False,
            "error": f"Payment plan setup error: {str(e)}"
        }
