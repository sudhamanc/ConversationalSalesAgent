"""
Standalone Payment Agent Test
Tests Payment Agent independently without Super Agent dependency
"""

import asyncio
from datetime import datetime
from ...agent import AgentContext
from ..Payment.payment_agent import PaymentAgent


def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def print_result(test_name, result):
    """Print formatted test result"""
    print(f"✓ {test_name}")
    print(f"  Result: {result}")
    print()


async def test_credit_check():
    """Test credit check functionality"""
    print_section("TEST 1: Credit Check")
    
    context = AgentContext(
        conversation_id="test_credit_001",
        user_id="test_user"
    )
    
    payment_agent = PaymentAgent(context)
    
    # Test multiple businesses
    businesses = [
        {"ein": "12-3456789", "name": "Acme Corporation"},
        {"ein": "98-7654321", "name": "Tech Solutions Inc"},
        {"ein": "45-6789012", "name": "Enterprise Systems LLC"}
    ]
    
    for business in businesses:
        result = await payment_agent.process({
            'action': 'credit_check',
            'params': {
                'business_ein': business['ein'],
                'business_name': business['name']
            }
        })
        
        credit_data = result['result']
        print(f"Business: {business['name']}")
        print(f"  EIN: {business['ein']}")
        print(f"  Credit Score: {credit_data['credit_score']}")
        print(f"  Credit Tier: {credit_data['credit_tier']}")
        print(f"  Approved: {'✓ YES' if credit_data['approved'] else '✗ NO'}")
        print(f"  Recommended Credit Limit: ${credit_data['recommended_credit_limit']:,.2f}")
        print(f"  Factors: {', '.join(credit_data['factors'])}")
        print()


async def test_payment_validation():
    """Test payment method validation"""
    print_section("TEST 2: Payment Method Validation")
    
    context = AgentContext(
        conversation_id="test_validation_001",
        user_id="test_user"
    )
    
    payment_agent = PaymentAgent(context)
    
    # Test 1: Valid Credit Card
    print("2.1: Valid Credit Card (Visa)")
    cc_result = await payment_agent.process({
        'action': 'validate_payment',
        'params': {
            'payment_type': 'credit_card',
            'payment_details': {
                'card_number': '4532015112830366',  # Valid Visa test card
                'exp_month': '12',
                'exp_year': '2027',
                'cvv': '123',
                'billing_zip': '19102'
            }
        }
    })
    
    cc_data = cc_result['result']
    print(f"  Valid: {'✓' if cc_data['valid'] else '✗'}")
    print(f"  Payment Method ID: {cc_data.get('payment_method_id', 'N/A')}")
    print(f"  Card Brand: {cc_data.get('card_brand', 'N/A')}")
    if cc_data.get('errors'):
        print(f"  Errors: {', '.join(cc_data['errors'])}")
    print()
    
    # Test 2: Valid ACH
    print("2.2: Valid ACH")
    ach_result = await payment_agent.process({
        'action': 'validate_payment',
        'params': {
            'payment_type': 'ach',
            'payment_details': {
                'routing_number': '021000021',
                'account_number': '1234567890',
                'account_type': 'business_checking'
            }
        }
    })
    
    ach_data = ach_result['result']
    print(f"  Valid: {'✓' if ach_data['valid'] else '✗'}")
    print(f"  Payment Method ID: {ach_data.get('payment_method_id', 'N/A')}")
    if ach_data.get('errors'):
        print(f"  Errors: {', '.join(ach_data['errors'])}")
    print()
    
    # Test 3: Invalid Credit Card (expired)
    print("2.3: Invalid Credit Card (Expired)")
    invalid_cc = await payment_agent.process({
        'action': 'validate_payment',
        'params': {
            'payment_type': 'credit_card',
            'payment_details': {
                'card_number': '4532015112830366',
                'exp_month': '01',
                'exp_year': '2020',  # Expired
                'cvv': '123',
                'billing_zip': '19102'
            }
        }
    })
    
    invalid_data = invalid_cc['result']
    print(f"  Valid: {'✓' if invalid_data['valid'] else '✗'}")
    if invalid_data.get('errors'):
        print(f"  Errors: {', '.join(invalid_data['errors'])}")
    print()
    
    # Test 4: Wire Transfer
    print("2.4: Wire Transfer")
    wire_result = await payment_agent.process({
        'action': 'validate_payment',
        'params': {
            'payment_type': 'wire',
            'payment_details': {
                'bank_name': 'Chase Bank',
                'account_number': '9876543210',
                'swift_code': 'CHASUS33'
            }
        }
    })
    
    wire_data = wire_result['result']
    print(f"  Valid: {'✓' if wire_data['valid'] else '✗'}")
    print(f"  Payment Method ID: {wire_data.get('payment_method_id', 'N/A')}")
    print()


async def test_fraud_assessment():
    """Test fraud risk assessment"""
    print_section("TEST 3: Fraud Risk Assessment")
    
    context = AgentContext(
        conversation_id="test_fraud_001",
        user_id="test_user"
    )
    
    payment_agent = PaymentAgent(context)
    
    # Test different risk scenarios
    scenarios = [
        {
            'name': 'Low Risk - Established Customer, Normal Amount',
            'amount': 5000.00,
            'customer_data': {
                'customer_id': 'cust_001',
                'account_age_days': 365,
                'state': 'PA'
            },
            'behavioral_signals': {
                'rapid_checkout': False,
                'vpn_detected': False
            }
        },
        {
            'name': 'Medium Risk - High Amount',
            'amount': 75000.00,
            'customer_data': {
                'customer_id': 'cust_002',
                'account_age_days': 180,
                'state': 'NY'
            },
            'behavioral_signals': {
                'rapid_checkout': False,
                'vpn_detected': False
            }
        },
        {
            'name': 'High Risk - New Customer, High Amount, VPN',
            'amount': 100000.00,
            'customer_data': {
                'customer_id': 'cust_003',
                'account_age_days': 15,
                'state': 'FL'
            },
            'behavioral_signals': {
                'rapid_checkout': True,
                'vpn_detected': True
            }
        }
    ]
    
    for scenario in scenarios:
        result = await payment_agent.process({
            'action': 'assess_fraud',
            'params': {
                'transaction_amount': scenario['amount'],
                'customer_data': scenario['customer_data'],
                'behavioral_signals': scenario['behavioral_signals']
            }
        })
        
        fraud_data = result['result']
        print(f"Scenario: {scenario['name']}")
        print(f"  Amount: ${scenario['amount']:,.2f}")
        print(f"  Risk Score: {fraud_data['risk_score']}")
        print(f"  Risk Level: {fraud_data['risk_level'].upper()}")
        print(f"  Manual Review Required: {'YES' if fraud_data['requires_manual_review'] else 'NO'}")
        print(f"  Risk Factors: {', '.join(fraud_data['risk_factors']) if fraud_data['risk_factors'] else 'None'}")
        print(f"  Recommendation: {fraud_data['recommended_action']}")
        print()


async def test_payment_authorization():
    """Test payment authorization"""
    print_section("TEST 4: Payment Authorization")
    
    context = AgentContext(
        conversation_id="test_auth_001",
        user_id="test_user"
    )
    
    payment_agent = PaymentAgent(context)
    
    # First validate a payment method
    validation = await payment_agent.process({
        'action': 'validate_payment',
        'params': {
            'payment_type': 'credit_card',
            'payment_details': {
                'card_number': '5555555555554444',  # Mastercard
                'exp_month': '06',
                'exp_year': '2028',
                'cvv': '456',
                'billing_zip': '10001'
            }
        }
    })
    
    if validation['result']['valid']:
        payment_method_id = validation['result']['payment_method_id']
        
        # Test multiple authorization amounts
        amounts = [1000.00, 5000.00, 25000.00]
        
        for amount in amounts:
            result = await payment_agent.process({
                'action': 'authorize',
                'params': {
                    'amount': amount,
                    'payment_method_id': payment_method_id,
                    'order_id': f'order_{int(datetime.now().timestamp())}'
                }
            })
            
            auth_data = result['result']
            print(f"Authorization for ${amount:,.2f}")
            print(f"  Status: {auth_data['status'].upper()}")
            if auth_data['status'] == 'authorized':
                print(f"  Authorization ID: {auth_data['authorization_id']}")
                print(f"  Authorized At: {auth_data['authorized_at']}")
            else:
                print(f"  Decline Reason: {auth_data.get('decline_reason', 'Unknown')}")
            print()


async def test_payment_capture():
    """Test payment capture"""
    print_section("TEST 5: Payment Capture")
    
    context = AgentContext(
        conversation_id="test_capture_001",
        user_id="test_user"
    )
    
    payment_agent = PaymentAgent(context)
    
    # Setup: Validate payment method and authorize
    validation = await payment_agent.process({
        'action': 'validate_payment',
        'params': {
            'payment_type': 'ach',
            'payment_details': {
                'routing_number': '021000021',
                'account_number': '9876543210',
                'account_type': 'business_checking'
            }
        }
    })
    
    if validation['result']['valid']:
        # Authorize
        auth_result = await payment_agent.process({
            'action': 'authorize',
            'params': {
                'amount': 10000.00,
                'payment_method_id': validation['result']['payment_method_id'],
                'order_id': 'order_capture_test_001'
            }
        })
        
        if auth_result['result']['status'] == 'authorized':
            auth_id = auth_result['result']['authorization_id']
            print(f"Authorization ID: {auth_id}")
            print(f"Authorized Amount: $10,000.00\n")
            
            # Test different capture scenarios
            captures = [
                {'amount': 10000.00, 'description': 'Full capture'},
                {'amount': 5000.00, 'description': 'Partial capture'},
            ]
            
            for capture in captures:
                result = await payment_agent.process({
                    'action': 'capture',
                    'params': {
                        'authorization_id': auth_id,
                        'amount': capture['amount']
                    }
                })
                
                capture_data = result['result']
                print(f"{capture['description']}: ${capture['amount']:,.2f}")
                print(f"  Status: {capture_data['status'].upper()}")
                
                if capture_data['status'] == 'captured':
                    print(f"  Transaction ID: {capture_data['transaction_id']}")
                    print(f"  Amount Captured: ${capture_data['amount_captured']:,.2f}")
                    break  # Only one capture per authorization
                else:
                    print(f"  Error: {capture_data.get('error', 'Unknown')}")
                print()


async def test_full_payment_flow():
    """Test complete end-to-end payment flow"""
    print_section("TEST 6: Complete Payment Flow")
    
    context = AgentContext(
        conversation_id="test_full_flow_001",
        user_id="test_user"
    )
    
    payment_agent = PaymentAgent(context)
    
    # Test different payment scenarios
    scenarios = [
        {
            'name': 'Approved - Good Credit, Valid Card',
            'business_ein': '11-2233445',
            'business_name': 'Premium Tech Corp',
            'payment_type': 'credit_card',
            'payment_details': {
                'card_number': '4532015112830366',
                'exp_month': '12',
                'exp_year': '2027',
                'cvv': '123',
                'billing_zip': '19102'
            },
            'amount': 15000.00,
            'customer_data': {
                'customer_id': 'cust_premium_001',
                'account_age_days': 365,
                'state': 'PA'
            }
        },
        {
            'name': 'Approved - ACH Payment',
            'business_ein': '22-3344556',
            'business_name': 'Enterprise Solutions LLC',
            'payment_type': 'ach',
            'payment_details': {
                'routing_number': '021000021',
                'account_number': '1234567890',
                'account_type': 'business_checking'
            },
            'amount': 50000.00,
            'customer_data': {
                'customer_id': 'cust_enterprise_001',
                'account_age_days': 730,
                'state': 'NY'
            }
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"Scenario {i}: {scenario['name']}")
        print("-" * 60)
        
        result = await payment_agent.process({
            'action': 'full_payment_flow',
            'business_ein': scenario['business_ein'],
            'business_name': scenario['business_name'],
            'payment_type': scenario['payment_type'],
            'payment_details': scenario['payment_details'],
            'amount': scenario['amount'],
            'order_id': f'order_flow_{i}',
            'customer_data': scenario['customer_data']
        })
        
        print(f"Overall Status: {result['overall_status'].upper()}")
        print(f"\nSteps Completed:")
        
        for step in result['steps']:
            step_name = step['step']
            step_result = step['result']
            
            if step_name == 'credit_check':
                credit = step_result.get('result', {})
                print(f"  ✓ Credit Check")
                print(f"    - Score: {credit.get('credit_score')}")
                print(f"    - Approved: {credit.get('approved')}")
                
            elif step_name == 'payment_validation':
                validation = step_result.get('result', {})
                print(f"  ✓ Payment Validation")
                print(f"    - Valid: {validation.get('valid')}")
                print(f"    - Method ID: {validation.get('payment_method_id')}")
                
            elif step_name == 'fraud_assessment':
                fraud = step_result.get('result', {})
                print(f"  ✓ Fraud Assessment")
                print(f"    - Risk Level: {fraud.get('risk_level')}")
                print(f"    - Risk Score: {fraud.get('risk_score')}")
                
            elif step_name == 'authorization':
                auth = step_result.get('result', {})
                print(f"  ✓ Authorization")
                print(f"    - Status: {auth.get('status')}")
                if auth.get('authorization_id'):
                    print(f"    - Auth ID: {auth.get('authorization_id')}")
        
        if result['overall_status'] == 'approved':
            print(f"\n✓ Payment Flow APPROVED")
            print(f"  Authorization ID: {result.get('authorization_id')}")
        else:
            print(f"\n✗ Payment Flow DECLINED")
            print(f"  Reason: {result.get('decline_reason', 'Unknown')}")
        
        print("\n")


async def test_agent_state_and_memory():
    """Test agent state and memory features"""
    print_section("TEST 7: Agent State & Memory")
    
    context = AgentContext(
        conversation_id="test_state_001",
        user_id="test_user"
    )
    
    payment_agent = PaymentAgent(context)
    
    # Perform several operations
    await payment_agent.process({
        'action': 'credit_check',
        'params': {
            'business_ein': '12-3456789',
            'business_name': 'Test Corp'
        }
    })
    
    await payment_agent.process({
        'action': 'validate_payment',
        'params': {
            'payment_type': 'credit_card',
            'payment_details': {
                'card_number': '4532015112830366',
                'exp_month': '12',
                'exp_year': '2027',
                'cvv': '123',
                'billing_zip': '19102'
            }
        }
    })
    
    # Get agent state
    state = payment_agent.get_state()
    print("Agent State:")
    print(f"  Agent ID: {state['agent_id']}")
    print(f"  Agent Name: {state['agent_name']}")
    print(f"  Status: {state['status']}")
    print(f"  Tools Available: {len(state['tools'])}")
    print(f"    - {', '.join(state['tools'])}")
    print(f"  Memory Entries: {state['memory_size']}")
    print()
    
    # Get memory
    all_memory = payment_agent.get_memory()
    print(f"Total Memory Entries: {len(all_memory)}")
    print("\nMemory Timeline:")
    for entry in all_memory[-5:]:  # Last 5 entries
        print(f"  [{entry['timestamp']}] {entry['type']}")
    print()
    
    # Get filtered memory
    credit_checks = payment_agent.get_memory(filter_type='credit_check')
    print(f"Credit Checks Performed: {len(credit_checks)}")
    
    payment_validations = payment_agent.get_memory(filter_type='payment_validation')
    print(f"Payment Validations: {len(payment_validations)}")
    print()


async def main():
    """Run all standalone payment agent tests"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  PAYMENT AGENT - STANDALONE TEST SUITE".center(78) + "█")
    print("█" + "  No Super Agent Required".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    # Run all tests
    await test_credit_check()
    await test_payment_validation()
    await test_fraud_assessment()
    await test_payment_authorization()
    await test_payment_capture()
    await test_full_payment_flow()
    await test_agent_state_and_memory()
    
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  ALL PAYMENT AGENT TESTS COMPLETED SUCCESSFULLY".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
