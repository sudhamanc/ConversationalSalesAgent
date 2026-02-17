"""
Billing and invoice management tools for the Payment Agent.

These tools handle invoice generation, payment history, and payment plans.
"""

import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from ..utils.logger import get_logger

logger = get_logger(__name__)


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
        invoice_id = f"INV-{datetime.now().strftime('%Y%m%d')}-{hash(customer_name) % 1000:03d}"
        
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


def get_payment_history(
    customer_id: str,
    start_date: str = None,
    end_date: str = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieves payment history for a customer.
    
    Args:
        customer_id: Unique customer identifier
        start_date: Start date for history (ISO format)
        end_date: End date for history (ISO format)
        limit: Maximum number of transactions to return
    
    Returns:
        Payment history with transactions
    """
    logger.info(f"Retrieving payment history for customer: {customer_id}")
    
    try:
        # Simulate fetching payment history
        # In production: Query from database
        
        # Generate sample transactions
        transactions = []
        for i in range(min(limit, 5)):
            date = datetime.now() - timedelta(days=30 * i)
            transactions.append({
                "transaction_id": f"TXN-{date.strftime('%Y%m%d')}-{i:03d}",
                "date": date.isoformat(),
                "amount": 500.00 + (i * 50),
                "status": "approved",
                "payment_method": "Credit Card (****1234)",
                "description": f"Monthly service payment - {'Month ' + str(i+1)}"
            })
        
        # Calculate summary
        total_paid = sum(t['amount'] for t in transactions)
        
        return {
            "success": True,
            "customer_id": customer_id,
            "transactions": transactions,
            "count": len(transactions),
            "total_amount": total_paid,
            "start_date": start_date,
            "end_date": end_date
        }
    
    except Exception as e:
        logger.error(f"Error retrieving payment history: {e}")
        return {
            "success": False,
            "error": f"Error retrieving payment history: {str(e)}"
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
        
        # Parse or set start date
        if start_date:
            start_date_obj = datetime.fromisoformat(start_date)
        else:
            start_date_obj = datetime.now() + timedelta(days=30)
        
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
        
        plan_id = f"PLAN-{datetime.now().strftime('%Y%m%d')}-{hash(str(total_amount)) % 1000:03d}"
        
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
