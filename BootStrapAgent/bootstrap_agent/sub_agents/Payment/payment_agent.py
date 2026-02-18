"""
Payment Agent - B2B Agentic Sales System
Handles credit verification, payment processing, and fraud detection

This agent follows the Hybrid Cognitive Model:
- LLM: Intent understanding, risk assessment
- Deterministic: Credit scoring, payment gateway integration
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import random
import hashlib
from decimal import Decimal

from ...agent import BaseAgent, AgentContext, AgentMessage, Tool, AgentStatus


class CreditScore(Enum):
    """Credit score ranges"""
    EXCELLENT = (750, 850, "Excellent")
    GOOD = (700, 749, "Good")
    FAIR = (650, 699, "Fair")
    POOR = (600, 649, "Poor")
    VERY_POOR = (300, 599, "Very Poor")


class PaymentStatus(Enum):
    """Payment processing status"""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    DECLINED = "declined"
    REFUNDED = "refunded"
    FAILED = "failed"


class FraudRiskLevel(Enum):
    """Fraud risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PaymentAgent(BaseAgent):
    """
    Payment Agent for B2B Sales System
    
    Responsibilities:
    - Credit verification and scoring
    - Payment method validation
    - Fraud detection and prevention
    - Payment authorization and capture
    - A2A communication with Offer Management and Order agents
    
    Tools:
    - check_credit_score
    - validate_payment_method
    - assess_fraud_risk
    - authorize_payment
    - process_payment
    """
    
    def __init__(self, context: AgentContext):
        super().__init__(
            agent_id="payment_agent_001",
            agent_name="Payment Agent",
            description="Handles credit verification, payment processing, and fraud detection for B2B sales",
            context=context
        )
        
        # Payment processing state
        self.pending_authorizations: Dict[str, Dict] = {}
        self.payment_history: List[Dict] = []
        
        # Risk thresholds
        self.min_credit_score_threshold = 650
        self.max_fraud_score_threshold = 0.7
        self.daily_transaction_limit = 100000.00
        
    def _register_tools(self):
        """Register payment-specific tools"""
        
        # Credit Check Tool
        self.register_tool(Tool(
            name="check_credit_score",
            description="Check business credit score using external credit bureau API",
            parameters={
                "business_ein": {"type": "string", "required": True},
                "business_name": {"type": "string", "required": True}
            },
            function=self._check_credit_score
        ))
        
        # Payment Method Validation Tool
        self.register_tool(Tool(
            name="validate_payment_method",
            description="Validate payment method details (credit card, ACH, wire)",
            parameters={
                "payment_type": {"type": "string", "enum": ["credit_card", "ach", "wire"]},
                "payment_details": {"type": "object", "required": True}
            },
            function=self._validate_payment_method
        ))
        
        # Fraud Assessment Tool
        self.register_tool(Tool(
            name="assess_fraud_risk",
            description="Assess fraud risk using ML model and historical patterns",
            parameters={
                "transaction_amount": {"type": "number", "required": True},
                "customer_data": {"type": "object", "required": True},
                "behavioral_signals": {"type": "object"}
            },
            function=self._assess_fraud_risk
        ))
        
        # Payment Authorization Tool
        self.register_tool(Tool(
            name="authorize_payment",
            description="Authorize payment with payment gateway",
            parameters={
                "amount": {"type": "number", "required": True},
                "payment_method_id": {"type": "string", "required": True},
                "order_id": {"type": "string", "required": True}
            },
            function=self._authorize_payment
        ))
        
        # Payment Processing Tool
        self.register_tool(Tool(
            name="process_payment",
            description="Process and capture authorized payment",
            parameters={
                "authorization_id": {"type": "string", "required": True},
                "amount": {"type": "number", "required": True}
            },
            function=self._process_payment
        ))
    
    # ==================== TOOL IMPLEMENTATIONS ====================
    
    def _check_credit_score(self, business_ein: str, business_name: str) -> Dict[str, Any]:
        """
        Check business credit score
        
        In production, this would integrate with:
        - Dun & Bradstreet API
        - Experian Business API
        - Equifax Business API
        
        Args:
            business_ein: Business EIN number
            business_name: Legal business name
            
        Returns:
            Credit score information
        """
        self.logger.info(f"Checking credit for EIN: {business_ein}")
        
        # Mock credit check (replace with actual API call)
        # Deterministic based on EIN hash for consistency
        ein_hash = int(hashlib.md5(business_ein.encode()).hexdigest()[:8], 16)
        mock_score = 600 + (ein_hash % 200)  # Score between 600-800
        
        # Determine credit tier
        credit_tier = None
        for tier in CreditScore:
            min_score, max_score, label = tier.value
            if min_score <= mock_score <= max_score:
                credit_tier = label
                break
        
        result = {
            "ein": business_ein,
            "business_name": business_name,
            "credit_score": mock_score,
            "credit_tier": credit_tier,
            "score_date": datetime.now().isoformat(),
            "approved": mock_score >= self.min_credit_score_threshold,
            "recommended_credit_limit": self._calculate_credit_limit(mock_score),
            "factors": self._get_credit_factors(mock_score)
        }
        
        self.add_to_memory({
            'type': 'credit_check',
            'ein': business_ein,
            'score': mock_score,
            'approved': result['approved']
        })
        
        return result
    
    def _calculate_credit_limit(self, credit_score: int) -> float:
        """Calculate recommended credit limit based on score"""
        if credit_score >= 750:
            return 500000.00
        elif credit_score >= 700:
            return 250000.00
        elif credit_score >= 650:
            return 100000.00
        else:
            return 50000.00
    
    def _get_credit_factors(self, score: int) -> List[str]:
        """Get credit score contributing factors"""
        factors = []
        
        if score >= 750:
            factors.extend([
                "Excellent payment history",
                "Low credit utilization",
                "Long credit history"
            ])
        elif score >= 700:
            factors.extend([
                "Good payment history",
                "Moderate credit utilization"
            ])
        elif score >= 650:
            factors.extend([
                "Fair payment history",
                "Some late payments noted"
            ])
        else:
            factors.extend([
                "Poor payment history",
                "High credit utilization",
                "Recent delinquencies"
            ])
        
        return factors
    
    def _validate_payment_method(self, 
                                 payment_type: str, 
                                 payment_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate payment method details
        
        Args:
            payment_type: Type of payment (credit_card, ach, wire)
            payment_details: Payment method details
            
        Returns:
            Validation result
        """
        self.logger.info(f"Validating payment method: {payment_type}")
        
        validation_result = {
            "payment_type": payment_type,
            "valid": False,
            "errors": [],
            "payment_method_id": None
        }
        
        if payment_type == "credit_card":
            validation_result = self._validate_credit_card(payment_details)
        elif payment_type == "ach":
            validation_result = self._validate_ach(payment_details)
        elif payment_type == "wire":
            validation_result = self._validate_wire(payment_details)
        else:
            validation_result["errors"].append(f"Unsupported payment type: {payment_type}")
        
        self.add_to_memory({
            'type': 'payment_validation',
            'payment_type': payment_type,
            'valid': validation_result['valid']
        })
        
        return validation_result
    
    def _validate_credit_card(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Validate credit card details using Luhn algorithm"""
        errors = []
        
        # Check required fields
        required_fields = ['card_number', 'exp_month', 'exp_year', 'cvv', 'billing_zip']
        for field in required_fields:
            if field not in details:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return {"payment_type": "credit_card", "valid": False, "errors": errors}
        
        # Validate card number (Luhn algorithm)
        card_number = details['card_number'].replace(' ', '').replace('-', '')
        if not self._luhn_check(card_number):
            errors.append("Invalid card number")
        
        # Validate expiration
        exp_month = int(details['exp_month'])
        exp_year = int(details['exp_year'])
        if exp_month < 1 or exp_month > 12:
            errors.append("Invalid expiration month")
        
        exp_date = datetime(exp_year, exp_month, 1)
        if exp_date < datetime.now():
            errors.append("Card is expired")
        
        # Validate CVV
        cvv = str(details['cvv'])
        if not (len(cvv) == 3 or len(cvv) == 4):
            errors.append("Invalid CVV")
        
        valid = len(errors) == 0
        
        return {
            "payment_type": "credit_card",
            "valid": valid,
            "errors": errors,
            "payment_method_id": f"pm_card_{hashlib.md5(card_number.encode()).hexdigest()[:12]}" if valid else None,
            "card_brand": self._detect_card_brand(card_number) if valid else None
        }
    
    def _luhn_check(self, card_number: str) -> bool:
        """Implement Luhn algorithm for card validation"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10 == 0
    
    def _detect_card_brand(self, card_number: str) -> str:
        """Detect card brand from number"""
        if card_number[0] == '4':
            return 'visa'
        elif card_number[0:2] in ['51', '52', '53', '54', '55']:
            return 'mastercard'
        elif card_number[0:2] in ['34', '37']:
            return 'amex'
        elif card_number[0:4] == '6011':
            return 'discover'
        return 'unknown'
    
    def _validate_ach(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Validate ACH payment details"""
        errors = []
        required_fields = ['routing_number', 'account_number', 'account_type']
        
        for field in required_fields:
            if field not in details:
                errors.append(f"Missing required field: {field}")
        
        if 'routing_number' in details:
            routing = details['routing_number']
            if len(routing) != 9 or not routing.isdigit():
                errors.append("Invalid routing number (must be 9 digits)")
        
        valid = len(errors) == 0
        
        return {
            "payment_type": "ach",
            "valid": valid,
            "errors": errors,
            "payment_method_id": f"pm_ach_{hashlib.md5(details.get('account_number', '').encode()).hexdigest()[:12]}" if valid else None
        }
    
    def _validate_wire(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Validate wire transfer details"""
        errors = []
        required_fields = ['bank_name', 'account_number', 'swift_code']
        
        for field in required_fields:
            if field not in details:
                errors.append(f"Missing required field: {field}")
        
        valid = len(errors) == 0
        
        return {
            "payment_type": "wire",
            "valid": valid,
            "errors": errors,
            "payment_method_id": f"pm_wire_{hashlib.md5(details.get('account_number', '').encode()).hexdigest()[:12]}" if valid else None
        }
    
    def _assess_fraud_risk(self,
                          transaction_amount: float,
                          customer_data: Dict[str, Any],
                          behavioral_signals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Assess fraud risk using multiple signals
        
        In production, integrate with:
        - Stripe Radar
        - Sift Science
        - Kount
        
        Args:
            transaction_amount: Transaction amount
            customer_data: Customer information
            behavioral_signals: Optional behavioral data
            
        Returns:
            Fraud risk assessment
        """
        self.logger.info(f"Assessing fraud risk for amount: ${transaction_amount}")
        
        risk_factors = []
        risk_score = 0.0
        
        # Amount-based risk
        if transaction_amount > 50000:
            risk_score += 0.3
            risk_factors.append("High transaction amount")
        elif transaction_amount > 100000:
            risk_score += 0.5
            risk_factors.append("Very high transaction amount")
        
        # New customer risk
        if customer_data.get('account_age_days', 0) < 30:
            risk_score += 0.2
            risk_factors.append("New customer account")
        
        # Geographic risk (mock)
        high_risk_states = ['FL', 'CA', 'NY']
        if customer_data.get('state') in high_risk_states:
            risk_score += 0.1
            risk_factors.append("High-risk geographic location")
        
        # Behavioral signals
        if behavioral_signals:
            if behavioral_signals.get('rapid_checkout', False):
                risk_score += 0.15
                risk_factors.append("Unusually rapid checkout")
            
            if behavioral_signals.get('vpn_detected', False):
                risk_score += 0.2
                risk_factors.append("VPN or proxy detected")
        
        # Velocity check
        recent_transactions = self._check_transaction_velocity(
            customer_data.get('customer_id')
        )
        if recent_transactions > 5:
            risk_score += 0.25
            risk_factors.append("High transaction velocity")
        
        # Determine risk level
        if risk_score < 0.3:
            risk_level = FraudRiskLevel.LOW
        elif risk_score < 0.5:
            risk_level = FraudRiskLevel.MEDIUM
        elif risk_score < 0.7:
            risk_level = FraudRiskLevel.HIGH
        else:
            risk_level = FraudRiskLevel.CRITICAL
        
        result = {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "recommended_action": self._get_fraud_recommendation(risk_level),
            "requires_manual_review": risk_score > self.max_fraud_score_threshold,
            "assessed_at": datetime.now().isoformat()
        }
        
        self.add_to_memory({
            'type': 'fraud_assessment',
            'amount': transaction_amount,
            'risk_score': risk_score,
            'risk_level': risk_level.value
        })
        
        return result
    
    def _check_transaction_velocity(self, customer_id: Optional[str]) -> int:
        """Check number of recent transactions for velocity analysis"""
        if not customer_id:
            return 0
        
        # Mock: count transactions in last 24 hours
        recent_count = sum(
            1 for txn in self.payment_history
            if txn.get('customer_id') == customer_id
            and datetime.fromisoformat(txn['timestamp']) > datetime.now() - timedelta(hours=24)
        )
        
        return recent_count
    
    def _get_fraud_recommendation(self, risk_level: FraudRiskLevel) -> str:
        """Get recommended action based on risk level"""
        recommendations = {
            FraudRiskLevel.LOW: "Approve transaction",
            FraudRiskLevel.MEDIUM: "Approve with additional verification",
            FraudRiskLevel.HIGH: "Hold for manual review",
            FraudRiskLevel.CRITICAL: "Decline transaction"
        }
        return recommendations[risk_level]
    
    def _authorize_payment(self,
                          amount: float,
                          payment_method_id: str,
                          order_id: str) -> Dict[str, Any]:
        """
        Authorize payment with payment gateway
        
        Args:
            amount: Amount to authorize
            payment_method_id: Payment method identifier
            order_id: Associated order ID
            
        Returns:
            Authorization result
        """
        self.logger.info(f"Authorizing payment: ${amount} for order {order_id}")
        
        # Mock authorization (in production: Stripe, Braintree, etc.)
        authorization_id = f"auth_{hashlib.md5(f'{order_id}{datetime.now()}'.encode()).hexdigest()[:16]}"
        
        # Simulate authorization with 95% success rate
        success = random.random() < 0.95
        
        if success:
            status = PaymentStatus.AUTHORIZED
            self.pending_authorizations[authorization_id] = {
                'amount': amount,
                'payment_method_id': payment_method_id,
                'order_id': order_id,
                'authorized_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
            }
        else:
            status = PaymentStatus.DECLINED
        
        result = {
            "authorization_id": authorization_id if success else None,
            "status": status.value,
            "amount": amount,
            "order_id": order_id,
            "authorized_at": datetime.now().isoformat() if success else None,
            "decline_reason": "Insufficient funds" if not success else None
        }
        
        self.add_to_memory({
            'type': 'payment_authorization',
            'authorization_id': authorization_id,
            'status': status.value,
            'amount': amount
        })
        
        return result
    
    def _process_payment(self, authorization_id: str, amount: float) -> Dict[str, Any]:
        """
        Capture authorized payment
        
        Args:
            authorization_id: Authorization ID to capture
            amount: Amount to capture (must be <= authorized amount)
            
        Returns:
            Payment processing result
        """
        self.logger.info(f"Processing payment for authorization: {authorization_id}")
        
        # Check if authorization exists
        if authorization_id not in self.pending_authorizations:
            return {
                "status": PaymentStatus.FAILED.value,
                "error": "Authorization not found",
                "authorization_id": authorization_id
            }
        
        auth = self.pending_authorizations[authorization_id]
        
        # Validate amount
        if amount > auth['amount']:
            return {
                "status": PaymentStatus.FAILED.value,
                "error": "Capture amount exceeds authorized amount",
                "authorization_id": authorization_id
            }
        
        # Check expiration
        if datetime.fromisoformat(auth['expires_at']) < datetime.now():
            return {
                "status": PaymentStatus.FAILED.value,
                "error": "Authorization expired",
                "authorization_id": authorization_id
            }
        
        # Process capture (mock)
        transaction_id = f"txn_{hashlib.md5(f'{authorization_id}{datetime.now()}'.encode()).hexdigest()[:16]}"
        
        result = {
            "transaction_id": transaction_id,
            "authorization_id": authorization_id,
            "status": PaymentStatus.CAPTURED.value,
            "amount_captured": amount,
            "order_id": auth['order_id'],
            "processed_at": datetime.now().isoformat(),
            "payment_method_id": auth['payment_method_id']
        }
        
        # Record in payment history
        self.payment_history.append({
            **result,
            'timestamp': datetime.now().isoformat(),
            'customer_id': self.context.user_id
        })
        
        # Remove from pending
        del self.pending_authorizations[authorization_id]
        
        self.add_to_memory({
            'type': 'payment_captured',
            'transaction_id': transaction_id,
            'amount': amount
        })
        
        return result
    
    # ==================== AGENT PROCESSING ====================
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method for Payment Agent
        
        Args:
            input_data: Contains action and relevant parameters
            
        Returns:
            Processing result
        """
        self.update_status(AgentStatus.PROCESSING)
        
        action = input_data.get('action')
        self.logger.info(f"Processing action: {action}")
        
        try:
            if action == 'full_payment_flow':
                result = await self._full_payment_flow(input_data)
            elif action == 'credit_check':
                result = self.execute_tool('check_credit_score', **input_data.get('params', {}))
            elif action == 'validate_payment':
                result = self.execute_tool('validate_payment_method', **input_data.get('params', {}))
            elif action == 'assess_fraud':
                result = self.execute_tool('assess_fraud_risk', **input_data.get('params', {}))
            elif action == 'authorize':
                result = self.execute_tool('authorize_payment', **input_data.get('params', {}))
            elif action == 'capture':
                result = self.execute_tool('process_payment', **input_data.get('params', {}))
            else:
                result = {
                    'status': 'error',
                    'error': f'Unknown action: {action}'
                }
            
            self.update_status(AgentStatus.COMPLETED)
            return result
            
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            self.update_status(AgentStatus.ERROR)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _full_payment_flow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete payment flow with all checks
        
        Args:
            input_data: Full payment information
            
        Returns:
            Complete payment flow result
        """
        flow_result = {
            'flow': 'complete_payment_verification',
            'steps': [],
            'overall_status': 'pending'
        }
        
        # Step 1: Credit Check
        credit_result = self.execute_tool(
            'check_credit_score',
            business_ein=input_data.get('business_ein'),
            business_name=input_data.get('business_name')
        )
        flow_result['steps'].append({
            'step': 'credit_check',
            'result': credit_result
        })
        
        if not credit_result.get('result', {}).get('approved'):
            flow_result['overall_status'] = 'declined'
            flow_result['decline_reason'] = 'Credit score below threshold'
            return flow_result
        
        # Step 2: Payment Method Validation
        payment_validation = self.execute_tool(
            'validate_payment_method',
            payment_type=input_data.get('payment_type'),
            payment_details=input_data.get('payment_details')
        )
        flow_result['steps'].append({
            'step': 'payment_validation',
            'result': payment_validation
        })
        
        if not payment_validation.get('result', {}).get('valid'):
            flow_result['overall_status'] = 'declined'
            flow_result['decline_reason'] = 'Invalid payment method'
            return flow_result
        
        # Step 3: Fraud Assessment
        fraud_assessment = self.execute_tool(
            'assess_fraud_risk',
            transaction_amount=input_data.get('amount'),
            customer_data=input_data.get('customer_data', {}),
            behavioral_signals=input_data.get('behavioral_signals')
        )
        flow_result['steps'].append({
            'step': 'fraud_assessment',
            'result': fraud_assessment
        })
        
        if fraud_assessment.get('result', {}).get('requires_manual_review'):
            flow_result['overall_status'] = 'hold'
            flow_result['hold_reason'] = 'Requires manual fraud review'
            return flow_result
        
        # Step 4: Authorization
        authorization = self.execute_tool(
            'authorize_payment',
            amount=input_data.get('amount'),
            payment_method_id=payment_validation['result']['payment_method_id'],
            order_id=input_data.get('order_id')
        )
        flow_result['steps'].append({
            'step': 'authorization',
            'result': authorization
        })
        
        if authorization.get('result', {}).get('status') != 'authorized':
            flow_result['overall_status'] = 'declined'
            flow_result['decline_reason'] = authorization['result'].get('decline_reason')
            return flow_result
        
        flow_result['overall_status'] = 'approved'
        flow_result['authorization_id'] = authorization['result']['authorization_id']
        
        return flow_result
    
    async def _handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle A2A messages from other agents
        
        Args:
            message: Incoming message from another agent
            
        Returns:
            Response to the message
        """
        content = message.content
        message_type = content.get('type')
        
        if message_type == 'credit_inquiry':
            # Offer Management Agent asking about creditworthiness
            return await self._handle_credit_inquiry(content)
        
        elif message_type == 'payment_request':
            # Order Agent requesting payment processing
            return await self._handle_payment_request(content)
        
        elif message_type == 'refund_request':
            # Handle refund request
            return await self._handle_refund_request(content)
        
        else:
            return {
                'status': 'error',
                'error': f'Unknown message type: {message_type}'
            }
    
    async def _handle_credit_inquiry(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle credit inquiry from another agent"""
        credit_result = self.execute_tool(
            'check_credit_score',
            business_ein=content.get('business_ein'),
            business_name=content.get('business_name')
        )
        
        return {
            'type': 'credit_inquiry_response',
            'approved': credit_result['result']['approved'],
            'credit_score': credit_result['result']['credit_score'],
            'credit_limit': credit_result['result']['recommended_credit_limit']
        }
    
    async def _handle_payment_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment processing request from Order Agent"""
        result = await self.process({
            'action': 'full_payment_flow',
            **content
        })
        
        return {
            'type': 'payment_response',
            'status': result.get('overall_status'),
            'authorization_id': result.get('authorization_id'),
            'details': result
        }
    
    async def _handle_refund_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle refund request"""
        # Mock refund processing
        return {
            'type': 'refund_response',
            'status': 'processed',
            'refund_id': f"refund_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:16]}",
            'amount': content.get('amount')
        }
