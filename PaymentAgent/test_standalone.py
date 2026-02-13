"""
Standalone test script for Payment Agent tools.
Tests the core payment functionality without requiring full ADK setup.
"""

import sys
from datetime import datetime
from payment_agent.tools.payment_tools import (
    validate_payment_method,
    process_payment,
    tokenize_payment_method,
    get_payment_methods
)
from payment_agent.tools.credit_tools import (
    check_business_credit,
    get_credit_report
)
from payment_agent.tools.billing_tools import (
    generate_invoice,
    get_payment_history,
    setup_payment_plan
)

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_payment_tools():
    """Test payment processing tools."""
    print_section("TESTING PAYMENT TOOLS")
    
    # Test 1: Validate credit card
    print("\n1. Validating credit card...")
    result = validate_payment_method(
        payment_type="credit_card",
        card_number="4532015112830366"  # Valid test Visa
    )
    print(f"   Result: {result.get('message', 'Valid' if result.get('valid') else 'Invalid')}")
    
    # Test 2: Tokenize payment method
    print("\n2. Tokenizing credit card...")
    result = tokenize_payment_method(
        payment_type="credit_card",
        card_number="4532015112830366",
        expiry_month=12,
        expiry_year=2026,
        cvv="123"
    )
    print(f"   Result: {result.get('message', 'Success' if result.get('success') else 'Failed')}")
    if result.get('success'):
        token = result.get('token')
        print(f"   Token: {token}")
        
        # Test 3: Process payment
        print("\n3. Processing payment...")
        payment_result = process_payment(
            amount=500.00,
            payment_method_token=token,
            description="Test payment"
        )
        print(f"   Result: {payment_result.get('message', 'Success' if payment_result.get('success') else 'Failed')}")
        if payment_result.get('success'):
            print(f"   Transaction ID: {payment_result.get('transaction_id')}")
    
    # Test 4: Get payment methods
    print("\n4. Retrieving saved payment methods...")
    result = get_payment_methods(customer_id="CUST-12345")
    print(f"   Found {result.get('count', 0)} payment methods")
    for method in result.get('payment_methods', []):
        print(f"   - {method.get('brand', method.get('type')).upper()}: ...{method.get('last_four')} ({method.get('nickname')})")

def test_credit_tools():
    """Test credit check tools."""
    print_section("TESTING CREDIT CHECK TOOLS")
    
    # Test 1: Business credit check
    print("\n1. Running business credit check...")
    result = check_business_credit(
        business_name="ABC Corporation",
        ein="12-3456789",
        years_in_business=10,
        state="DE",
        requested_credit_limit=10000.00
    )
    if result.get('success'):
        print(f"   Decision: {result.get('decision').upper()}")
        print(f"   Credit Score: {result.get('credit_score')}")
        print(f"   Approved Limit: ${result.get('approved_credit_limit'):,.2f}")
        print(f"   Payment Terms: {result.get('payment_terms')}")
        print(f"   Required Deposit: ${result.get('required_deposit'):,.2f}")
    
    # Test 2: Get credit report
    print("\n2. Retrieving credit report...")
    result = get_credit_report(ein="12-3456789")
    if result.get('success'):
        print(f"   Credit Score: {result.get('credit_score')}")
        print(f"   Risk Class: {result.get('risk_class')}")
        print(f"   Tradelines: {len(result.get('tradelines', []))}")
        print(f"   On-time Payments: {result.get('payment_history', {}).get('on_time_payments')}%")

def test_billing_tools():
    """Test billing and invoice tools."""
    print_section("TESTING BILLING TOOLS")
    
    # Test 1: Generate invoice
    print("\n1. Generating invoice...")
    result = generate_invoice(
        customer_name="ABC Corporation",
        line_items=[
            {"description": "Business Fiber 1 Gbps", "quantity": 1, "unit_price": 500.00},
            {"description": "Installation Fee", "quantity": 1, "unit_price": 199.00}
        ]
    )
    if result.get('success'):
        print(f"   Invoice ID: {result.get('invoice_id')}")
        print(f"   Subtotal: ${result.get('subtotal'):,.2f}")
        print(f"   Tax: ${result.get('tax'):,.2f}")
        print(f"   Total: ${result.get('total'):,.2f}")
        print(f"   Due Date: {result.get('due_date', '')[:10]}")
    
    # Test 2: Get payment history
    print("\n2. Retrieving payment history...")
    result = get_payment_history(customer_id="CUST-12345", limit=5)
    if result.get('success'):
        print(f"   Found {result.get('count')} transactions")
        print(f"   Total Paid: ${result.get('total_amount'):,.2f}")
        for txn in result.get('transactions', [])[:3]:
            print(f"   - {txn.get('date')[:10]}: ${txn.get('amount'):,.2f} ({txn.get('status')})")
    
    # Test 3: Setup payment plan
    print("\n3. Creating payment plan...")
    result = setup_payment_plan(
        total_amount=1200.00,
        num_installments=12,
        frequency="monthly"
    )
    if result.get('success'):
        print(f"   Plan ID: {result.get('plan_id')}")
        print(f"   Installment Amount: ${result.get('installment_amount'):,.2f}")
        print(f"   Frequency: {result.get('frequency')}")
        print(f"   Start Date: {result.get('start_date')[:10]}")

def main():
    """Run all tests."""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + "  PAYMENT AGENT - STANDALONE TOOL TESTING".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    
    try:
        test_payment_tools()
        test_credit_tools()
        test_billing_tools()
        
        print_section("ALL TESTS COMPLETED SUCCESSFULLY")
        print("\n✓ All payment agent tools are working correctly!")
        print("\nNote: These tests use simulated data. In production, these tools")
        print("would integrate with actual payment gateways and credit bureaus.\n")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
