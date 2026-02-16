#!/usr/bin/env python3
"""
Test script to verify ProductAgent integration with SuperAgent.
"""

import sys
import os

# Add SuperAgent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set required environment variable for testing
os.environ['GEMINI_MODEL'] = 'gemini-2.0-flash'

try:
    print('=' * 60)
    print('Testing SuperAgent + ProductAgent Integration')
    print('=' * 60)
    
    # Test import
    print('\n1. Importing SuperAgent...')
    from super_agent import get_agent
    print('   ✅ SuperAgent imported successfully')
    
    # Get root agent
    print('\n2. Getting root agent...')
    root_agent = get_agent()
    print(f'   ✅ Root agent: {root_agent.name}')
    
    # Check sub-agents
    print('\n3. Checking sub-agents...')
    print(f'   Total sub-agents: {len(root_agent.sub_agents)}')
    for agent in root_agent.sub_agents:
        print(f'   - {agent.name} ({len(agent.tools)} tools)')
    
    # Verify ProductAgent specifically
    print('\n4. Verifying ProductAgent...')
    product_agents = [a for a in root_agent.sub_agents if a.name == 'product_agent']
    if product_agents:
        product_agent = product_agents[0]
        print(f'   ✅ ProductAgent found: {product_agent.name}')
        print(f'   ✅ Tools: {len(product_agent.tools)}')
        print(f'   ✅ Model: {product_agent.model}')
        print(f'   ✅ Temperature: {product_agent.generate_content_config.temperature}')
        
        # List tools
        print('\n   Tool names:')
        for tool in product_agent.tools:
            tool_name = getattr(tool, 'name', tool.__name__ if hasattr(tool, '__name__') else str(tool))
            print(f'      - {tool_name}')
    else:
        print('   ❌ ProductAgent not found!')
        sys.exit(1)
    
    # Check for duplicate names
    print('\n5. Checking for duplicate agent names...')
    names = [a.name for a in root_agent.sub_agents]
    if len(names) == len(set(names)):
        print(f'   ✅ All agent names unique: {names}')
    else:
        print(f'   ❌ Duplicate names found: {names}')
        sys.exit(1)
    
    # Verify agent hierarchy
    print('\n6. Verifying agent hierarchy...')
    expected_agents = ['discovery_agent', 'serviceability_agent', 'product_agent', 'greeting_agent', 'faq_agent']
    for expected in expected_agents:
        if expected in names:
            print(f'   ✅ {expected} present')
        else:
            print(f'   ❌ {expected} missing!')
            sys.exit(1)
    
    # Test agent configuration
    print('\n7. Testing agent configurations...')
    for agent in root_agent.sub_agents:
        if agent.name == 'product_agent':
            # ProductAgent should have temp 0.1
            expected_temp = 0.1
            actual_temp = agent.generate_content_config.temperature
            if abs(actual_temp - expected_temp) < 0.01:
                print(f'   ✅ {agent.name} temperature: {actual_temp} (RAG agent)')
            else:
                print(f'   ⚠️  {agent.name} temperature: {actual_temp} (expected {expected_temp})')
        elif agent.name == 'serviceability_agent':
            # ServiceabilityAgent should have temp 0.0
            expected_temp = 0.0
            actual_temp = agent.generate_content_config.temperature
            if actual_temp == expected_temp:
                print(f'   ✅ {agent.name} temperature: {actual_temp} (deterministic)')
            else:
                print(f'   ⚠️  {agent.name} temperature: {actual_temp} (expected {expected_temp})')
    
    print('\n' + '=' * 60)
    print('✅ ALL TESTS PASSED!')
    print('=' * 60)
    print('\nSummary:')
    print(f'  • SuperAgent: {root_agent.name}')
    print(f'  • Sub-agents: {len(root_agent.sub_agents)}')
    print(f'  • ProductAgent: Integrated with {len(product_agent.tools)} tools')
    print(f'  • All agent names unique: Yes')
    print('\n✨ ProductAgent integration successful!')
    
except Exception as e:
    print(f'\n❌ ERROR: {type(e).__name__}: {str(e)}')
    import traceback
    print('\nFull traceback:')
    traceback.print_exc()
    sys.exit(1)
