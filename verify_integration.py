#!/usr/bin/env python3
"""
Verification script for ProductAgent and ServiceabilityAgent integrations.
Checks compliance with all ADK best practices and integration requirements.
"""

import os
import sys
import ast
import re

def check_file_exists(path, description):
    """Check if a file exists."""
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def check_no_load_dotenv(file_path, agent_name):
    """Verify that load_dotenv() is not called (ignores comments)."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Check for uncommented load_dotenv() calls
    has_load_dotenv = False
    for line in lines:
        stripped = line.strip()
        # Skip comment lines
        if stripped.startswith('#'):
            continue
        # Check if load_dotenv() appears in actual code
        if 'load_dotenv()' in stripped:
            has_load_dotenv = True
            break
    
    status = "❌" if has_load_dotenv else "✅"
    print(f"{status} {agent_name}: No load_dotenv() call")
    return not has_load_dotenv

def check_hardcoded_name(file_path, expected_name, agent_name):
    """Verify agent uses hardcoded name."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Look for name="expected_name" pattern
    pattern = f'name="{expected_name}"'
    has_hardcoded = pattern in content
    
    # Check it's NOT using environment variable
    no_env_name = 'AGENT_NAME' not in content or 'os.getenv("AGENT_NAME")' not in content
    
    status = "✅" if (has_hardcoded and no_env_name) else "❌"
    print(f"{status} {agent_name}: Hardcoded name='{expected_name}'")
    return has_hardcoded and no_env_name

def check_model_no_default(file_path, agent_name):
    """Verify GEMINI_MODEL reads from env without default."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Look for os.getenv("GEMINI_MODEL") without default
    has_no_default = re.search(r'os\.getenv\(["\']GEMINI_MODEL["\']\)(?!\s*,)', content)
    
    status = "✅" if has_no_default else "❌"
    print(f"{status} {agent_name}: GEMINI_MODEL without default")
    return bool(has_no_default)

def check_importlib_wrapper(wrapper_path, agent_name):
    """Check importlib wrapper exists and has correct structure."""
    if not os.path.exists(wrapper_path):
        print(f"❌ {agent_name}: Importlib wrapper missing at {wrapper_path}")
        return False
    
    with open(wrapper_path, 'r') as f:
        content = f.read()
    
    checks = {
        'importlib.util': 'importlib.util' in content,
        'spec_from_file_location': 'spec_from_file_location' in content,
        'stub package': 'ModuleType' in content or 'stub' in content.lower(),
        'exports agent': f'{agent_name.lower()} =' in content
    }
    
    all_good = all(checks.values())
    status = "✅" if all_good else "❌"
    print(f"{status} {agent_name}: Importlib wrapper structure")
    
    if not all_good:
        for check, passed in checks.items():
            if not passed:
                print(f"    ⚠️  Missing: {check}")
    
    return all_good

def check_superagent_registration(agent_import_name):
    """Check agent is imported and registered in SuperAgent."""
    agent_file = '/Users/rbarat738@cable.comcast.com/Documents/GitHub/ConversationalSalesAgent/SuperAgent/super_agent/agent.py'
    
    with open(agent_file, 'r') as f:
        content = f.read()
    
    has_import = f'from .sub_agents.{agent_import_name} import' in content
    has_registration = agent_import_name in content and 'sub_agents' in content
    
    status = "✅" if (has_import and has_registration) else "❌"
    print(f"{status} {agent_import_name}: Registered in SuperAgent")
    return has_import and has_registration

def check_routing_instructions(agent_name_display):
    """Check agent is mentioned in routing instructions."""
    prompts_file = '/Users/rbarat738@cable.comcast.com/Documents/GitHub/ConversationalSalesAgent/SuperAgent/super_agent/prompts.py'
    
    with open(prompts_file, 'r') as f:
        content = f.read()
    
    is_mentioned = agent_name_display.lower() in content.lower()
    
    status = "✅" if is_mentioned else "❌"
    print(f"{status} {agent_name_display}: Routing instructions present")
    return is_mentioned

def main():
    print("=" * 70)
    print("INTEGRATION VERIFICATION: ProductAgent & ServiceabilityAgent")
    print("=" * 70)
    print()
    
    base_path = '/Users/rbarat738@cable.comcast.com/Documents/GitHub/ConversationalSalesAgent'
    
    all_checks = []
    
    # =======================================================================
    # SERVICEABILITY AGENT CHECKS
    # =======================================================================
    print("📋 ServiceabilityAgent Integration:")
    print("-" * 70)
    
    sa_agent_file = f'{base_path}/ServiceabilityAgent/serviceability_agent/agent.py'
    sa_wrapper = f'{base_path}/SuperAgent/super_agent/sub_agents/serviceability/agent.py'
    
    all_checks.append(check_file_exists(sa_agent_file, "Agent file"))
    all_checks.append(check_file_exists(sa_wrapper, "Importlib wrapper"))
    all_checks.append(check_no_load_dotenv(sa_agent_file, "ServiceabilityAgent"))
    all_checks.append(check_hardcoded_name(sa_agent_file, "serviceability_agent", "ServiceabilityAgent"))
    all_checks.append(check_model_no_default(sa_agent_file, "ServiceabilityAgent"))
    all_checks.append(check_importlib_wrapper(sa_wrapper, "serviceability_agent"))
    all_checks.append(check_superagent_registration("serviceability"))
    all_checks.append(check_routing_instructions("ServiceabilityAgent"))
    
    print()
    
    # =======================================================================
    # PRODUCT AGENT CHECKS
    # =======================================================================
    print("📋 ProductAgent Integration:")
    print("-" * 70)
    
    pa_agent_file = f'{base_path}/ProductAgent/product_agent/agent.py'
    pa_wrapper = f'{base_path}/SuperAgent/super_agent/sub_agents/product/agent.py'
    
    all_checks.append(check_file_exists(pa_agent_file, "Agent file"))
    all_checks.append(check_file_exists(pa_wrapper, "Importlib wrapper"))
    all_checks.append(check_no_load_dotenv(pa_agent_file, "ProductAgent"))
    all_checks.append(check_hardcoded_name(pa_agent_file, "product_agent", "ProductAgent"))
    all_checks.append(check_model_no_default(pa_agent_file, "ProductAgent"))
    all_checks.append(check_importlib_wrapper(pa_wrapper, "product_agent"))
    all_checks.append(check_superagent_registration("product"))
    all_checks.append(check_routing_instructions("ProductAgent"))
    
    print()
    
    # =======================================================================
    # SUPERAGENT INTEGRATION CHECK
    # =======================================================================
    print("📋 SuperAgent Configuration:")
    print("-" * 70)
    
    # Check SuperAgent can be imported
    sys.path.insert(0, f'{base_path}/SuperAgent')
    try:
        from super_agent import get_agent
        agent = get_agent()
        
        # Check agent tree
        sub_agent_names = [sa.name for sa in agent.sub_agents] if agent.sub_agents else []
        
        has_serviceability = 'serviceability_agent' in sub_agent_names
        has_product = 'product_agent' in sub_agent_names
        
        print(f"✅ SuperAgent imports successfully")
        print(f"{'✅' if has_serviceability else '❌'} serviceability_agent in agent tree")
        print(f"{'✅' if has_product else '❌'} product_agent in agent tree")
        print(f"📊 Total sub-agents: {len(sub_agent_names)}")
        print(f"   Sub-agents: {', '.join(sub_agent_names)}")
        
        all_checks.append(has_serviceability)
        all_checks.append(has_product)
        
        # Check tool counts
        sa_agent = next((a for a in agent.sub_agents if a.name == 'serviceability_agent'), None)
        pa_agent = next((a for a in agent.sub_agents if a.name == 'product_agent'), None)
        
        if sa_agent:
            sa_tools = len(sa_agent.tools) if sa_agent.tools else 0
            print(f"   ServiceabilityAgent tools: {sa_tools}")
            all_checks.append(sa_tools == 6)  # Expected 6 tools
        
        if pa_agent:
            pa_tools = len(pa_agent.tools) if pa_agent.tools else 0
            print(f"   ProductAgent tools: {pa_tools}")
            all_checks.append(pa_tools == 11)  # Expected 11 tools
            
    except Exception as e:
        print(f"❌ SuperAgent import failed: {e}")
        all_checks.append(False)
    
    print()
    
    # =======================================================================
    # SUMMARY
    # =======================================================================
    print("=" * 70)
    passed = sum(all_checks)
    total = len(all_checks)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"RESULTS: {passed}/{total} checks passed ({percentage:.1f}%)")
    
    if passed == total:
        print("✅ ALL CHECKS PASSED - Integrations are compliant!")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Review issues above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
