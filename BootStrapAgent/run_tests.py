"""
Test Runner for Payment and Service Fulfillment Agents
Tests that agents work correctly with the new imports from agent.py
"""

import asyncio
import sys
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional

# Add bootstrap_agent to path
bootstrap_path = Path(__file__).parent / "BootStrapAgent"
sys.path.insert(0, str(bootstrap_path))

# Define the base classes here to avoid circular imports
class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentContext:
    """Shared context across agents"""
    conversation_id: str
    user_id: Optional[str] = None
    session_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentMessage:
    """Message structure for agent communication"""
    sender: str
    receiver: str
    content: Dict[str, Any]
    message_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None


@dataclass
class Tool:
    """Tool definition for agent capabilities"""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: callable


async def test_payment_agent_imports():
    """Test that Payment Agent can be imported and instantiated"""
    print("\n" + "="*80)
    print("TEST 1: Payment Agent Imports and Instantiation")
    print("="*80 + "\n")
    
    try:
        from bootstrap_agent.sub_agents.Payment.payment_agent import PaymentAgent
        print("✓ Successfully imported PaymentAgent")
        
        # Create context
        context = AgentContext(
            conversation_id="test_001",
            user_id="test_user"
        )
        print("✓ Created AgentContext")
        
        # Instantiate agent
        payment_agent = PaymentAgent(context)
        print(f"✓ Instantiated PaymentAgent: {payment_agent.agent_name}")
        
        # Check agent state
        state = payment_agent.get_state()
        print(f"\n  Agent Details:")
        print(f"    - ID: {state['agent_id']}")
        print(f"    - Status: {state['status']}")
        print(f"    - Tools Registered: {len(state['tools'])}")
        print(f"    - Available Tools: {', '.join(state['tools'])}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_payment_agent_tools():
    """Test Payment Agent tool execution"""
    print("\n" + "="*80)
    print("TEST 2: Payment Agent Tool Execution")
    print("="*80 + "\n")
    
    try:
        from bootstrap_agent.sub_agents.Payment.payment_agent import PaymentAgent
        
        context = AgentContext(
            conversation_id="test_002",
            user_id="test_user"
        )
        
        payment_agent = PaymentAgent(context)
        print("✓ PaymentAgent instantiated\n")
        
        # Test credit check
        print("Testing Credit Check Tool:")
        result = await payment_agent.process({
            'action': 'credit_check',
            'params': {
                'business_ein': '12-3456789',
                'business_name': 'Acme Corp'
            }
        })
        
        if result.get('status') == 'success':
            credit_data = result['result']
            print(f"  ✓ Credit Score: {credit_data['credit_score']}")
            print(f"  ✓ Credit Tier: {credit_data['credit_tier']}")
            print(f"  ✓ Approved: {credit_data['approved']}")
        else:
            print(f"  ✗ Error: {result.get('error')}")
            return False
        
        # Test payment method validation
        print("\nTesting Payment Method Validation Tool:")
        result = await payment_agent.process({
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
        
        if result.get('status') == 'success':
            validation = result['result']
            print(f"  ✓ Valid: {validation['valid']}")
            print(f"  ✓ Payment Method ID: {validation.get('payment_method_id', 'N/A')}")
        else:
            print(f"  ✗ Error: {result.get('error')}")
            return False
        
        # Test fraud assessment
        print("\nTesting Fraud Assessment Tool:")
        result = await payment_agent.process({
            'action': 'assess_fraud',
            'params': {
                'transaction_amount': 5000.00,
                'customer_data': {
                    'customer_id': 'cust_001',
                    'account_age_days': 365,
                    'state': 'PA'
                }
            }
        })
        
        if result.get('status') == 'success':
            fraud = result['result']
            print(f"  ✓ Risk Score: {fraud['risk_score']}")
            print(f"  ✓ Risk Level: {fraud['risk_level']}")
            print(f"  ✓ Manual Review Required: {fraud['requires_manual_review']}")
        else:
            print(f"  ✗ Error: {result.get('error')}")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_service_fulfillment_agent_imports():
    """Test that Service Fulfillment Agent can be imported and instantiated"""
    print("\n" + "="*80)
    print("TEST 3: Service Fulfillment Agent Imports and Instantiation")
    print("="*80 + "\n")
    
    try:
        from bootstrap_agent.sub_agents.Service_Fulfillment.service_fulfillment_agent import ServiceFulfillmentAgent
        print("✓ Successfully imported ServiceFulfillmentAgent")
        
        # Create context
        context = AgentContext(
            conversation_id="test_003",
            user_id="test_user"
        )
        print("✓ Created AgentContext")
        
        # Instantiate agent
        service_agent = ServiceFulfillmentAgent(context)
        print(f"✓ Instantiated ServiceFulfillmentAgent: {service_agent.agent_name}")
        
        # Check agent state
        state = service_agent.get_state()
        print(f"\n  Agent Details:")
        print(f"    - ID: {state['agent_id']}")
        print(f"    - Status: {state['status']}")
        print(f"    - Tools Registered: {len(state['tools'])}")
        print(f"    - Available Tools: {', '.join(state['tools'])}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_service_fulfillment_agent_tools():
    """Test Service Fulfillment Agent tool execution"""
    print("\n" + "="*80)
    print("TEST 4: Service Fulfillment Agent Tool Execution")
    print("="*80 + "\n")
    
    try:
        from bootstrap_agent.sub_agents.Service_Fulfillment.service_fulfillment_agent import ServiceFulfillmentAgent
        
        context = AgentContext(
            conversation_id="test_004",
            user_id="test_user"
        )
        
        service_agent = ServiceFulfillmentAgent(context)
        print("✓ ServiceFulfillmentAgent instantiated\n")
        
        # Test serviceability check
        print("Testing Serviceability Check Tool:")
        result = await service_agent.process({
            'action': 'check_serviceability',
            'params': {
                'address': {
                    'street': '123 Market Street',
                    'city': 'Philadelphia',
                    'state': 'PA',
                    'zip_code': '19102'
                },
                'service_type': 'internet',
                'speed_tier': '1G'
            }
        })
        
        if result.get('status') == 'success':
            serviceability = result['result']
            print(f"  ✓ Serviceable: {serviceability['serviceable']}")
            print(f"  ✓ Status: {serviceability['status']}")
            print(f"  ✓ Available Services: {len(serviceability['available_services'])} services")
        else:
            print(f"  ✗ Error: {result.get('error')}")
            return False
        
        # Test network capacity check
        print("\nTesting Network Capacity Check Tool:")
        result = await service_agent.process({
            'action': 'check_capacity',
            'params': {
                'zip_code': '19102',
                'bandwidth_required': 1000
            }
        })
        
        if result.get('status') == 'success':
            capacity = result['result']
            print(f"  ✓ Available Capacity: {capacity['available_capacity_mbps']} Mbps")
            print(f"  ✓ Sufficient: {capacity['sufficient_capacity']}")
            print(f"  ✓ Utilization: {capacity['current_utilization_pct']}%")
        else:
            print(f"  ✗ Error: {result.get('error')}")
            return False
        
        # Test available slots
        print("\nTesting Available Slots Tool:")
        result = await service_agent.process({
            'action': 'get_slots',
            'params': {
                'zip_code': '19102',
                'installation_type': 'standard'
            }
        })
        
        if result.get('status') == 'success':
            slots = result['result']
            print(f"  ✓ Total Available Slots: {slots['total_available']}")
            if slots['available_slots']:
                first_slot = slots['available_slots'][0]
                print(f"  ✓ Earliest Slot: {first_slot['date']} {first_slot['start_time']}")
        else:
            print(f"  ✗ Error: {result.get('error')}")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_memory():
    """Test agent memory features"""
    print("\n" + "="*80)
    print("TEST 5: Agent Memory and State Management")
    print("="*80 + "\n")
    
    try:
        from bootstrap_agent.sub_agents.Payment.payment_agent import PaymentAgent
        
        context = AgentContext(
            conversation_id="test_005",
            user_id="test_user"
        )
        
        payment_agent = PaymentAgent(context)
        print("✓ PaymentAgent instantiated\n")
        
        # Perform multiple operations
        print("Performing multiple operations to populate memory...")
        await payment_agent.process({
            'action': 'credit_check',
            'params': {
                'business_ein': '12-3456789',
                'business_name': 'Test Corp'
            }
        })
        print("  ✓ Credit check completed")
        
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
        print("  ✓ Payment validation completed")
        
        # Check memory
        print("\nMemory Analysis:")
        all_memory = payment_agent.get_memory()
        print(f"  ✓ Total Memory Entries: {len(all_memory)}")
        
        credit_checks = payment_agent.get_memory(filter_type='credit_check')
        print(f"  ✓ Credit Checks: {len(credit_checks)}")
        
        validations = payment_agent.get_memory(filter_type='payment_validation')
        print(f"  ✓ Payment Validations: {len(validations)}")
        
        # Check state
        state = payment_agent.get_state()
        print(f"\nAgent State:")
        print(f"  ✓ Status: {state['status']}")
        print(f"  ✓ Memory Size: {state['memory_size']}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("=" + " "*78 + "=")
    print("=" + "PAYMENT & SERVICE FULFILLMENT AGENTS - TEST SUITE".center(78) + "=")
    print("=" + "Testing new imports from agent.py".center(78) + "=")
    print("=" + " "*78 + "=")
    print("="*80)
    
    results = []
    
    # Run tests
    results.append(("Payment Agent Imports", await test_payment_agent_imports()))
    results.append(("Payment Agent Tools", await test_payment_agent_tools()))
    results.append(("Service Agent Imports", await test_service_fulfillment_agent_imports()))
    results.append(("Service Agent Tools", await test_service_fulfillment_agent_tools()))
    results.append(("Agent Memory", await test_agent_memory()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:12} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed\n")
    
    if passed == total:
        print("="*80)
        print("=" + " "*78 + "=")
        print("=" + "ALL TESTS PASSED! ✓".center(78) + "=")
        print("=" + " "*78 + "=")
        print("="*80 + "\n")
        return 0
    else:
        print("="*80)
        print("=" + " "*78 + "=")
        print("=" + f"SOME TESTS FAILED ({total - passed} failed)".center(78) + "=")
        print("=" + " "*78 + "=")
        print("="*80 + "\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
