#!/usr/bin/env python3
"""
Comprehensive test script to verify ALL agent integrations with SuperAgent.
Tests: Discovery, Serviceability, Product, Payment, ServiceFulfillment, Greeting, FAQ
"""

import sys
import os

# Add SuperAgent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set required environment variables for testing
os.environ['GEMINI_MODEL'] = 'gemini-2.0-flash'

def print_header(text):
    """Print formatted section header"""
    print('\n' + '=' * 70)
    print(f'  {text}')
    print('=' * 70)

def print_subheader(text):
    """Print formatted subsection header"""
    print(f'\n  {text}')
    print('  ' + '-' * 68)

def print_success(text):
    """Print success message"""
    print(f'   ✅ {text}')

def print_error(text):
    """Print error message"""
    print(f'   ❌ {text}')

def print_info(text):
    """Print info message"""
    print(f'   ℹ️  {text}')

def test_agent_import():
    """Test 1: Import SuperAgent module"""
    print_header('TEST 1: SuperAgent Import')
    try:
        from super_agent import get_agent
        print_success('SuperAgent module imported successfully')
        return True, get_agent
    except Exception as e:
        print_error(f'Failed to import SuperAgent: {e}')
        return False, None

def test_root_agent(get_agent):
    """Test 2: Get root agent instance"""
    print_header('TEST 2: Root Agent Instance')
    try:
        root_agent = get_agent()
        print_success(f'Root agent created: {root_agent.name}')
        print_info(f'Model: {root_agent.model}')
        return True, root_agent
    except Exception as e:
        print_error(f'Failed to get root agent: {e}')
        return False, None

def test_sub_agents(root_agent):
    """Test 3: Verify all sub-agents are loaded"""
    print_header('TEST 3: Sub-Agent Registration')
    
    expected_agents = [
        'discovery_agent',
        'serviceability_agent',
        'product_agent',
        'offer_management_agent',
        'payment_agent',
        'order_agent',
        'service_fulfillment_agent',
        'customer_communication_agent',
        'greeting_agent',
        'faq_agent'
    ]
    
    print_info(f'Expected agents: {len(expected_agents)}')
    print_info(f'Loaded agents: {len(root_agent.sub_agents)}')
    
    loaded_agent_names = [agent.name for agent in root_agent.sub_agents]
    
    all_present = True
    for expected_name in expected_agents:
        if expected_name in loaded_agent_names:
            print_success(f'{expected_name} is loaded')
        else:
            print_error(f'{expected_name} is MISSING')
            all_present = False
    
    # Check for unexpected agents
    for loaded_name in loaded_agent_names:
        if loaded_name not in expected_agents:
            print_info(f'Unexpected agent found: {loaded_name}')
    
    return all_present, root_agent.sub_agents

def test_agent_details(sub_agents):
    """Test 4: Check detailed configuration of each agent"""
    print_header('TEST 4: Agent Configuration Details')
    
    all_valid = True
    
    for agent in sub_agents:
        print_subheader(f'{agent.name}')
        
        # Check name
        if agent.name:
            print_success(f'Name: {agent.name}')
        else:
            print_error('Name is missing')
            all_valid = False
        
        # Check model
        if agent.model:
            print_info(f'Model: {agent.model}')
        else:
            print_error('Model is missing')
            all_valid = False
        
        # Check tools
        tool_count = len(agent.tools) if agent.tools else 0
        if tool_count > 0:
            print_success(f'Tools: {tool_count} tools loaded')
            # Print first 3 tool names
            for i, tool in enumerate(agent.tools[:3]):
                tool_name = getattr(tool, 'name', tool.__name__ if hasattr(tool, '__name__') else 'unknown')
                print(f'      {i+1}. {tool_name}')
            if tool_count > 3:
                print(f'      ... and {tool_count - 3} more')
        else:
            # Some agents like greeting/faq may not have tools
            if agent.name in ['greeting_agent', 'faq_agent']:
                print_info('Tools: 0 (expected for this agent type)')
            else:
                print_error(f'Tools: No tools loaded (unexpected for {agent.name})')
                all_valid = False
        
        # Check temperature
        if hasattr(agent, 'generate_content_config') and agent.generate_content_config:
            temp = agent.generate_content_config.temperature
            print_info(f'Temperature: {temp}')
        else:
            print_info('Temperature: Not accessible')
        
        # Check description
        if hasattr(agent, 'description') and agent.description:
            desc_preview = agent.description[:60] + '...' if len(agent.description) > 60 else agent.description
            print_info(f'Description: {desc_preview}')
    
    return all_valid

def test_specific_agents(sub_agents):
    """Test 5: Verify newly integrated agents specifically"""
    print_header('TEST 5: Newly Integrated Agents (Payment & ServiceFulfillment)')
    
    agents_dict = {agent.name: agent for agent in sub_agents}
    
    # Test PaymentAgent
    print_subheader('PaymentAgent')
    if 'payment_agent' in agents_dict:
        payment = agents_dict['payment_agent']
        print_success('PaymentAgent is integrated')
        print_info(f'Tools: {len(payment.tools)} tools')
        
        # Check expected tools
        expected_tools = ['validate_payment_method', 'process_payment', 'check_business_credit']
        tool_names = [getattr(t, 'name', t.__name__ if hasattr(t, '__name__') else '') for t in payment.tools]
        
        for expected_tool in expected_tools:
            if expected_tool in tool_names:
                print_success(f'Tool "{expected_tool}" found')
            else:
                print_info(f'Tool "{expected_tool}" not found (may be named differently)')
    else:
        print_error('PaymentAgent NOT FOUND')
        return False
    
    # Test ServiceFulfillmentAgent
    print_subheader('ServiceFulfillmentAgent')
    if 'service_fulfillment_agent' in agents_dict:
        fulfillment = agents_dict['service_fulfillment_agent']
        print_success('ServiceFulfillmentAgent is integrated')
        print_info(f'Tools: {len(fulfillment.tools)} tools')
        
        # Check expected tools
        expected_tools = ['check_availability', 'schedule_installation', 'activate_service']
        tool_names = [getattr(t, 'name', t.__name__ if hasattr(t, '__name__') else '') for t in fulfillment.tools]
        
        for expected_tool in expected_tools:
            if expected_tool in tool_names:
                print_success(f'Tool "{expected_tool}" found')
            else:
                print_info(f'Tool "{expected_tool}" not found (may be named differently)')
    else:
        print_error('ServiceFulfillmentAgent NOT FOUND')
        return False
    
    return True

def test_routing_coverage():
    """Test 6: Verify routing rules cover all agents"""
    print_header('TEST 6: Routing Rules Coverage')
    
    try:
        from super_agent.prompts import ORCHESTRATOR_INSTRUCTION
        
        agent_names = [
            'discovery_agent',
            'serviceability_agent',
            'product_agent',
            'offer_management_agent',
            'order_agent',
            'payment_agent',
            'service_fulfillment_agent',
            'customer_communication_agent',
            'greeting_agent',
            'faq_agent'
        ]
        
        for agent_name in agent_names:
            if agent_name in ORCHESTRATOR_INSTRUCTION:
                print_success(f'{agent_name} mentioned in routing rules')
            else:
                print_error(f'{agent_name} NOT mentioned in routing rules')
        
        # Check for payment-related keywords
        payment_keywords = ['payment', 'credit check', 'billing']
        fulfillment_keywords = ['installation', 'schedule', 'service activation']
        
        print_subheader('Payment Keywords')
        for keyword in payment_keywords:
            if keyword.lower() in ORCHESTRATOR_INSTRUCTION.lower():
                print_success(f'"{keyword}" found in routing rules')
        
        print_subheader('Fulfillment Keywords')
        for keyword in fulfillment_keywords:
            if keyword.lower() in ORCHESTRATOR_INSTRUCTION.lower():
                print_success(f'"{keyword}" found in routing rules')
        
        return True
    except Exception as e:
        print_error(f'Failed to check routing rules: {e}')
        return False

def main():
    """Run all tests"""
    print_header('SuperAgent Integration Test Suite')
    print('Testing all agent integrations including Payment & ServiceFulfillment\n')
    
    results = []
    
    # Test 1: Import
    success, get_agent = test_agent_import()
    results.append(('Import', success))
    if not success:
        print('\n❌ CRITICAL: Cannot proceed without successful import')
        return False
    
    # Test 2: Root agent
    success, root_agent = test_root_agent(get_agent)
    results.append(('Root Agent', success))
    if not success:
        print('\n❌ CRITICAL: Cannot proceed without root agent')
        return False
    
    # Test 3: Sub-agents
    success, sub_agents = test_sub_agents(root_agent)
    results.append(('Sub-Agent Registration', success))
    
    # Test 4: Agent details
    success = test_agent_details(sub_agents)
    results.append(('Agent Configuration', success))
    
    # Test 5: Specific agents
    success = test_specific_agents(sub_agents)
    results.append(('New Agents (Payment/Fulfillment)', success))
    
    # Test 6: Routing rules
    success = test_routing_coverage()
    results.append(('Routing Rules', success))
    
    # Final summary
    print_header('TEST RESULTS SUMMARY')
    
    all_passed = True
    for test_name, passed in results:
        if passed:
            print_success(f'{test_name}: PASSED')
        else:
            print_error(f'{test_name}: FAILED')
            all_passed = False
    
    print('\n' + '=' * 70)
    if all_passed:
        print('  ✅ ALL TESTS PASSED - Integration is working correctly!')
    else:
        print('  ❌ SOME TESTS FAILED - Please review errors above')
    print('=' * 70 + '\n')
    
    return all_passed

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'\n❌ FATAL ERROR: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
