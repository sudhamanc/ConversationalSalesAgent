#!/usr/bin/env python3
"""
Quick verification script to test API keys in both agents.
"""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

def test_api_key(agent_name, env_file):
    """Test if the API key works by making a simple API call."""
    print(f"\n{'='*60}")
    print(f"Testing {agent_name}")
    print(f"{'='*60}")
    
    # Load environment variables
    load_dotenv(env_file)
    api_key = os.getenv("GOOGLE_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    if not api_key:
        print(f"❌ ERROR: No GOOGLE_API_KEY found in {env_file}")
        return False
    
    print(f"✓ API Key found: {api_key[:20]}...")
    print(f"✓ Model: {model_name}")
    
    try:
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Try a simple generation
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'API key is working' in one sentence.")
        
        print(f"✓ API Response: {response.text.strip()}")
        print(f"✅ SUCCESS: {agent_name} API key is working!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: API call failed - {str(e)}")
        return False

def main():
    """Run verification for both agents."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    results = {}
    
    # Test ProductAgent
    product_env = os.path.join(base_path, "ProductAgent", ".env")
    results["ProductAgent"] = test_api_key("ProductAgent", product_env)
    
    # Test ServiceabilityAgent
    serviceability_env = os.path.join(base_path, "ServiceabilityAgent", ".env")
    results["ServiceabilityAgent"] = test_api_key("ServiceabilityAgent", serviceability_env)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for agent, status in results.items():
        status_symbol = "✅" if status else "❌"
        print(f"{status_symbol} {agent}: {'WORKING' if status else 'FAILED'}")
    
    all_working = all(results.values())
    print(f"\nOverall: {'✅ All API keys working!' if all_working else '❌ Some API keys failed'}")
    
    return 0 if all_working else 1

if __name__ == "__main__":
    sys.exit(main())
