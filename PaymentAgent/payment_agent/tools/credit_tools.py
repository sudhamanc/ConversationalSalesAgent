"""
Credit check and assessment tools for the Payment Agent.

These tools handle business credit checks and credit report retrieval.
"""

import json
from typing import Dict, Any
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


def check_business_credit(
    business_name: str,
    ein: str,
    years_in_business: int,
    state: str,
    requested_credit_limit: float = None
) -> Dict[str, Any]:
    """
    Performs a business credit check.
    
    For production: Integrates with credit bureau APIs (Dun & Bradstreet, Experian, etc.)
    For testing: Simulates credit check with rule-based logic
    
    Args:
        business_name: Legal business name
        ein: Employer Identification Number
        years_in_business: Number of years in operation
        state: State of incorporation (2-letter code)
        requested_credit_limit: Requested credit limit amount
    
    Returns:
        Credit check result with decision and terms
    """
    logger.info(f"Running credit check for: {business_name} (EIN: {ein})")
    
    try:
        # Validate EIN format
        clean_ein = ein.replace('-', '')
        if not clean_ein.isdigit() or len(clean_ein) != 9:
            return {
                "success": False,
                "error": "Invalid EIN format. Must be 9 digits (XX-XXXXXXX)"
            }
        
        # Simulate credit scoring (in production: call credit bureau API)
        credit_score = _calculate_mock_credit_score(years_in_business, business_name)
        
        # Determine credit decision based on score
        if credit_score >= 70:
            decision = "approved"
            approved_limit = requested_credit_limit or 10000.0
            payment_terms = "Net 30"
            required_deposit = 0.0
            conditions = None
        
        elif credit_score >= 50:
            decision = "conditional"
            approved_limit = min(requested_credit_limit or 5000.0, 5000.0)
            payment_terms = "Net 15"
            required_deposit = approved_limit * 0.25  # 25% deposit
            conditions = [
                "25% deposit required",
                "Personal guarantee from business owner",
                "Review after 6 months of on-time payments"
            ]
        
        else:
            decision = "declined"
            approved_limit = 0.0
            payment_terms = None
            required_deposit = 0.0
            conditions = [
                "Insufficient credit history",
                "Alternative: Prepayment required",
                "Alternative: 50% deposit with monthly payments"
            ]
        
        result = {
            "success": True,
            "business_name": business_name,
            "ein": ein,
            "decision": decision,
            "credit_score": credit_score,
            "approved_credit_limit": approved_limit,
            "payment_terms": payment_terms,
            "required_deposit": required_deposit,
            "conditions": conditions,
            "checked_at": datetime.now().isoformat(),
            "message": _format_credit_decision_message(decision, approved_limit, payment_terms, required_deposit)
        }
        
        logger.info(f"Credit check complete: {decision} (score: {credit_score})")
        return result
    
    except Exception as e:
        logger.error(f"Error performing credit check: {e}")
        return {
            "success": False,
            "error": f"Credit check error: {str(e)}"
        }


def get_credit_report(ein: str) -> Dict[str, Any]:
    """
    Retrieves detailed credit report for a business.
    
    For production: Fetches from credit bureau
    For testing: Returns simulated credit report data
    
    Args:
        ein: Employer Identification Number
    
    Returns:
        Detailed credit report
    """
    logger.info(f"Retrieving credit report for EIN: {ein}")
    
    try:
        # Validate EIN
        clean_ein = ein.replace('-', '')
        if not clean_ein.isdigit() or len(clean_ein) != 9:
            return {
                "success": False,
                "error": "Invalid EIN format"
            }
        
        # Simulate credit report (in production: call credit bureau API)
        report = {
            "success": True,
            "ein": ein,
            "credit_score": 75,
            "risk_class": "Low Risk",
            "tradelines": [
                {
                    "creditor": "Office Supplies Inc.",
                    "account_type": "Revolving",
                    "credit_limit": 5000,
                    "balance": 1200,
                    "payment_status": "Current",
                    "months_reviewed": 24
                },
                {
                    "creditor": "Equipment Leasing Co.",
                    "account_type": "Installment",
                    "original_amount": 15000,
                    "balance": 8000,
                    "payment_status": "Current",
                    "months_reviewed": 18
                }
            ],
            "payment_history": {
                "on_time_payments": 95,
                "late_30_days": 2,
                "late_60_days": 0,
                "late_90_days": 0
            },
            "public_records": {
                "bankruptcies": 0,
                "liens": 0,
                "judgments": 0
            },
            "inquiries_last_6_months": 3,
            "report_date": datetime.now().isoformat()
        }
        
        return report
    
    except Exception as e:
        logger.error(f"Error retrieving credit report: {e}")
        return {
            "success": False,
            "error": f"Error retrieving credit report: {str(e)}"
        }


# Helper functions

def _calculate_mock_credit_score(years_in_business: int, business_name: str) -> int:
    """
    Simulates credit score calculation for testing.
    
    Args:
        years_in_business: Years company has been operating
        business_name: Business name (for variation)
    
    Returns:
        Credit score (0-100)
    """
    # Base score from years in business
    base_score = min(years_in_business * 10, 50)
    
    # Add variation based on business name (for testing variety)
    name_hash = hash(business_name) % 30
    
    # Final score between 20-100
    score = max(20, min(100, base_score + name_hash))
    
    return score


def _format_credit_decision_message(
    decision: str,
    approved_limit: float,
    payment_terms: str,
    required_deposit: float
) -> str:
    """
    Formats a human-readable credit decision message.
    
    Args:
        decision: Credit decision (approved/conditional/declined)
        approved_limit: Approved credit limit
        payment_terms: Payment terms (e.g., Net 30)
        required_deposit: Required deposit amount
    
    Returns:
        Formatted message
    """
    if decision == "approved":
        return (
            f"✓ APPROVED - Credit limit: ${approved_limit:,.2f}, "
            f"Payment terms: {payment_terms}, No deposit required"
        )
    elif decision == "conditional":
        return (
            f"⚠ CONDITIONAL APPROVAL - Credit limit: ${approved_limit:,.2f}, "
            f"Payment terms: {payment_terms}, Deposit required: ${required_deposit:,.2f}"
        )
    else:
        return (
            "✗ DECLINED - Prepayment or significant deposit required. "
            "Alternative payment arrangements available."
        )
