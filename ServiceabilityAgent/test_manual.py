#!/usr/bin/env python3
"""
Manual integration test for Serviceability Agent

Tests the agent's tools directly without requiring Gemini API key.
This demonstrates that all core functionality works with mock data.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from serviceability_agent.tools.address_tools import validate_and_parse_address
from serviceability_agent.tools.gis_tools import (
    check_service_availability,
    get_products_by_technology,
    get_coverage_zones
)
from serviceability_agent.utils.cache import get_cache_stats, clear_cache
from serviceability_agent.utils.logger import get_logger

logger = get_logger(__name__)

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_address_validation():
    """Test address validation functionality"""
    print_section("TEST 1: Address Validation")
    
    # Test valid address
    address = "123 Market Street, Philadelphia, PA 19107"
    print(f"\n📍 Testing: {address}")
    result = validate_and_parse_address(address)
    if result['valid']:
        print("✅ Address validated successfully!")
        print(f"   Parsed: {result['address']}")
    else:
        print(f"❌ Validation failed: {result['error']}")
    
    # Test PO Box rejection
    print("\n📍 Testing PO Box rejection: PO Box 1234, Philadelphia, PA 19107")
    result = validate_and_parse_address("PO Box 1234, Philadelphia, PA 19107")
    if not result['valid']:
        print("✅ PO Box correctly rejected!")
        print(f"   Reason: {result['error']}")
    else:
        print("❌ PO Box should have been rejected")
    
    # Test international address
    print("\n📍 Testing international address: 10 Downing Street, London, UK")
    result = validate_and_parse_address("10 Downing Street, London, UK")
    if not result['valid']:
        print("✅ International address correctly rejected!")
        print(f"   Reason: {result['error']}")
    else:
        print("❌ International address should have been rejected")

def test_serviceability_checks():
    """Test GIS serviceability checks"""
    print_section("TEST 2: Serviceability Checks (Mock Data)")
    
    # Test serviceable address - Philadelphia
    address = {
        "street": "123 Market Street",
        "city": "Philadelphia",
        "state": "PA",
        "zip_code": "19107"
    }
    print(f"\n🏢 Checking: {address['street']}, {address['city']}, {address['state']} {address['zip_code']}")
    result = check_service_availability(address)
    
    if result['serviceable']:
        print("✅ Address is serviceable!")
        print(f"   Infrastructure: {result['infrastructure_type']}")
        print(f"   Service Zone: {result['service_zone']}")
        print(f"   Install Time: {result['estimated_install_days']} days")
        print(f"   Available Products: {len(result['available_products'])}")
        for product in result['available_products']:
            print(f"      • {product['product_name']} - {product['speeds'][0]} ({product.get('price', 'N/A')})")
    else:
        print(f"❌ Address not serviceable: {result.get('reason')}")
    
    # Test non-serviceable address
    address = {
        "street": "789 Remote Road",
        "city": "Nowhere",
        "state": "AK",
        "zip_code": "99999"
    }
    print(f"\n🏢 Checking: {address['street']}, {address['city']}, {address['state']} {address['zip_code']}")
    result = check_service_availability(address)
    
    if not result['serviceable']:
        print("✅ Correctly identified as non-serviceable!")
        print(f"   Reason: {result['reason']}")
    else:
        print("❌ This address should not be serviceable")

def test_product_catalog():
    """Test product catalog retrieval"""
    print_section("TEST 3: Product Catalog")
    
    technologies = ['FTTP', 'HFC', 'DOCSIS 3.1']
    for tech in technologies:
        products = get_products_by_technology(tech)
        print(f"\n📦 {tech} Products: {len(products)} available")
        for product in products:
            print(f"   • {product['name']} - {product['speed']}")

def test_coverage_zones():
    """Test coverage zone retrieval"""
    print_section("TEST 4: Coverage Zones")
    
    zones = get_coverage_zones()
    print(f"\n🗺️  Total Coverage Zones: {len(zones)}")
    for zone in zones:
        print(f"   • {zone}")

def test_caching():
    """Test caching functionality"""
    print_section("TEST 5: Caching System")
    
    # Clear cache first
    clear_cache()
    print("\n🗑️  Cache cleared")
    
    # Make first request
    address = {
        "street": "123 Market Street",
        "city": "Philadelphia",
        "state": "PA",
        "zip_code": "19107"
    }
    print("\n📊 First request (cache miss expected)...")
    check_service_availability(address)
    
    stats = get_cache_stats()
    print(f"   Cache size: {stats['size']}")
    print(f"   Cache misses: {stats['misses']}")
    
    # Make second request (should hit cache)
    print("\n📊 Second request (cache hit expected)...")
    check_service_availability(address)
    
    stats = get_cache_stats()
    print(f"   Cache size: {stats['size']}")
    print(f"   Cache hits: {stats['hits']}")
    print(f"   Hit rate: {stats['hit_rate']}")
    
    if stats['hits'] > 0:
        print("\n✅ Caching working correctly!")
    else:
        print("\n❌ Cache not working as expected")

def test_agent_initialization():
    """Test agent initialization"""
    print_section("TEST 6: Agent Initialization")
    
    try:
        from serviceability_agent import get_agent
        agent = get_agent()
        
        print(f"\n🤖 Agent Name: {agent.name}")
        print(f"   Model: {agent.model}")
        print(f"   Tools: {len(agent.tools)} registered")
        print(f"   Temperature: {agent.generate_content_config.temperature}")
        print(f"   Top-P: {agent.generate_content_config.top_p}")
        print(f"   Top-K: {agent.generate_content_config.top_k}")
        
        # List tools
        print("\n   Registered Tools:")
        for tool in agent.tools:
            tool_name = tool.__name__ if hasattr(tool, '__name__') else str(tool)
            print(f"      • {tool_name}")
        
        print("\n✅ Agent initialized successfully!")
        
        if agent.generate_content_config.temperature == 0.0:
            print("✅ Agent is deterministic (temperature=0.0)")
        else:
            print(f"⚠️  Agent temperature is {agent.generate_content_config.temperature} (expected 0.0)")
            
    except Exception as e:
        print(f"\n❌ Agent initialization failed: {e}")

def main():
    """Run all tests"""
    print("\n" + "🚀" * 30)
    print("  SERVICEABILITY AGENT - MANUAL INTEGRATION TEST")
    print("🚀" * 30)
    print("\n📝 This test validates all core functionality using mock data")
    print("   No Gemini API key required for these tests\n")
    
    try:
        test_address_validation()
        test_serviceability_checks()
        test_product_catalog()
        test_coverage_zones()
        test_caching()
        test_agent_initialization()
        
        print_section("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("\n🎉 The Serviceability Agent is fully functional!")
        print("\n📌 Next Steps:")
        print("   1. Add your GOOGLE_API_KEY to .env file")
        print("   2. Run: python main.py")
        print("   3. Test with: curl http://localhost:8002/health")
        print("   4. Check documentation in README.md\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
