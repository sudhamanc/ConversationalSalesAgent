"""
Pydantic models for payment processing and billing.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class PaymentMethodType(str, Enum):
    """Supported payment method types"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ACH = "ach"
    WIRE = "wire"
    CHECK = "check"


class CardBrand(str, Enum):
    """Supported credit card brands"""
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"


class PaymentStatus(str, Enum):
    """Payment transaction status"""
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    FAILED = "failed"
    REFUNDED = "refunded"


class CreditDecision(str, Enum):
    """Credit check decision types"""
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    DECLINED = "declined"


class PaymentMethod(BaseModel):
    """Base payment method"""
    method_type: PaymentMethodType
    is_default: bool = Field(default=False)
    nickname: Optional[str] = Field(None, description="Customer-defined name")
    

class CreditCard(PaymentMethod):
    """Credit card payment method"""
    method_type: PaymentMethodType = PaymentMethodType.CREDIT_CARD
    card_brand: CardBrand
    last_four: str = Field(..., description="Last 4 digits of card")
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2024)
    cardholder_name: str
    token: Optional[str] = Field(None, description="Tokenized card reference")
    
    @validator('last_four')
    def validate_last_four(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError('last_four must be 4 digits')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "method_type": "credit_card",
                "card_brand": "visa",
                "last_four": "1234",
                "expiry_month": 12,
                "expiry_year": 2026,
                "cardholder_name": "John Smith",
                "is_default": True,
                "nickname": "Business Visa"
            }
        }


class BankAccount(PaymentMethod):
    """ACH bank account payment method"""
    method_type: PaymentMethodType = PaymentMethodType.ACH
    account_type: str = Field(..., description="checking or savings")
    routing_number: str = Field(..., description="9-digit routing number")
    account_last_four: str = Field(..., description="Last 4 digits of account")
    account_holder_name: str
    bank_name: Optional[str] = None
    
    @validator('routing_number')
    def validate_routing(cls, v):
        if not v.isdigit() or len(v) != 9:
            raise ValueError('routing_number must be 9 digits')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "method_type": "ach",
                "account_type": "checking",
                "routing_number": "021000021",
                "account_last_four": "5678",
                "account_holder_name": "ABC Corporation",
                "bank_name": "Chase Bank"
            }
        }


class PaymentTransaction(BaseModel):
    """Payment transaction record"""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    amount: float = Field(..., gt=0, description="Transaction amount in USD")
    currency: str = Field(default="USD")
    payment_method: PaymentMethod
    status: PaymentStatus
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    description: Optional[str] = None
    invoice_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN-20260213-001",
                "amount": 500.00,
                "currency": "USD",
                "status": "approved",
                "description": "Monthly service payment",
                "invoice_id": "INV-2026-001"
            }
        }


class CreditCheckRequest(BaseModel):
    """Business credit check request"""
    business_name: str = Field(..., description="Legal business name")
    ein: str = Field(..., description="Employer Identification Number")
    years_in_business: int = Field(..., ge=0)
    state: str = Field(..., description="State of incorporation")
    requested_credit_limit: Optional[float] = Field(None, gt=0)
    
    @validator('ein')
    def validate_ein(cls, v):
        # Remove hyphens for validation
        clean_ein = v.replace('-', '')
        if not clean_ein.isdigit() or len(clean_ein) != 9:
            raise ValueError('EIN must be 9 digits (format: XX-XXXXXXX)')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "ABC Corporation",
                "ein": "12-3456789",
                "years_in_business": 5,
                "state": "DE",
                "requested_credit_limit": 10000.00
            }
        }


class CreditCheckResponse(BaseModel):
    """Business credit check response"""
    request: CreditCheckRequest
    decision: CreditDecision
    credit_score: Optional[int] = Field(None, ge=0, le=100)
    approved_credit_limit: float = Field(default=0.0, ge=0)
    payment_terms: Optional[str] = Field(None, description="e.g., Net 30, Net 60")
    required_deposit: float = Field(default=0.0, ge=0)
    conditions: Optional[List[str]] = Field(default=None)
    checked_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "decision": "approved",
                "credit_score": 75,
                "approved_credit_limit": 10000.00,
                "payment_terms": "Net 30",
                "required_deposit": 0.00,
                "conditions": None
            }
        }


class InvoiceLineItem(BaseModel):
    """Individual line item on invoice"""
    description: str
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    

class Invoice(BaseModel):
    """Customer invoice"""
    invoice_id: str = Field(..., description="Unique invoice number")
    customer_name: str
    issue_date: datetime = Field(default_factory=datetime.now)
    due_date: datetime
    line_items: List[InvoiceLineItem]
    subtotal: float = Field(..., ge=0)
    tax: float = Field(default=0.0, ge=0)
    total: float = Field(..., ge=0)
    amount_paid: float = Field(default=0.0, ge=0)
    balance_due: float = Field(..., ge=0)
    status: str = Field(default="unpaid")
    
    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-2026-001",
                "customer_name": "ABC Corporation",
                "due_date": "2026-03-15T00:00:00",
                "subtotal": 500.00,
                "tax": 40.00,
                "total": 540.00,
                "balance_due": 540.00,
                "status": "unpaid"
            }
        }


class PaymentPlan(BaseModel):
    """Payment plan for installments"""
    plan_id: str
    total_amount: float = Field(..., gt=0)
    num_installments: int = Field(..., ge=2)
    installment_amount: float = Field(..., gt=0)
    frequency: str = Field(default="monthly")
    start_date: datetime
    installments: List[dict] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "PLAN-001",
                "total_amount": 1200.00,
                "num_installments": 12,
                "installment_amount": 100.00,
                "frequency": "monthly",
                "start_date": "2026-03-01T00:00:00"
            }
        }
