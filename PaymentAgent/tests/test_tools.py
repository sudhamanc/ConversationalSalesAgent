"""
Tests for payment agent tools.
"""

import pytest
from payment_agent.tools.payment_tools import (
    validate_payment_method,
    process_payment,
    tokenize_payment_method,
)
from payment_agent.tools.credit_tools import (
    check_business_credit,
)
from payment_agent.tools.billing_tools import (
    generate_invoice,
    setup_payment_plan,
)


class TestPaymentTools:
    """Tests for payment processing tools."""
    
    def test_validate_credit_card(self):
        """Test credit card validation."""
        result = validate_payment_method(
            payment_type="credit_card",
            card_number="4532015112830366"  # Valid test Visa card
        )
        assert result["valid"] is True
        assert result["card_brand"] == "visa"
    
    def test_validate_invalid_card(self):
        """Test invalid credit card."""
        result = validate_payment_method(
            payment_type="credit_card",
            card_number="1234567890123456"
        )
        assert result["valid"] is False
    
    def test_validate_ach(self):
        """Test ACH validation."""
        result = validate_payment_method(
            payment_type="ach",
            routing_number="021000021",
            account_number="123456789"
        )
        assert result["valid"] is True
    
    def test_process_payment(self):
        """Test payment processing."""
        result = process_payment(
            amount=100.00,
            payment_method_token="tok_visa_1234",
            description="Test payment"
        )
        assert result["success"] is True
        assert result["amount"] == 100.00


class TestCreditTools:
    """Tests for credit check tools."""
    
    def test_check_business_credit_approved(self):
        """Test credit check approval."""
        result = check_business_credit(
            business_name="ABC Corporation",
            ein="12-3456789",
            years_in_business=10,
            state="DE"
        )
        assert result["success"] is True
        assert result["decision"] in ["approved", "conditional", "declined"]
    
    def test_check_business_credit_invalid_ein(self):
        """Test credit check with invalid EIN."""
        result = check_business_credit(
            business_name="Test Corp",
            ein="invalid",
            years_in_business=5,
            state="CA"
        )
        assert result["success"] is False


class TestBillingTools:
    """Tests for billing tools."""
    
    def test_generate_invoice(self):
        """Test invoice generation."""
        result = generate_invoice(
            customer_name="ABC Corporation",
            line_items=[
                {"description": "Internet Service", "quantity": 1, "unit_price": 500.00}
            ]
        )
        assert result["success"] is True
        assert result["total"] > 0
    
    def test_setup_payment_plan(self):
        """Test payment plan setup."""
        result = setup_payment_plan(
            total_amount=1200.00,
            num_installments=12
        )
        assert result["success"] is True
        assert result["installment_amount"] == 100.00
        assert len(result["installments"]) == 12
