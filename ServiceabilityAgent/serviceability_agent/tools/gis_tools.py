"""
GIS integration tools for checking service availability.

These tools interface with GIS/Coverage Map APIs to determine
if an address can receive service and what products are available.
"""

import os
from typing import Dict, List, Any, Optional
from ..utils.logger import get_logger
from ..utils.cache import cache_result, get_cached_result

logger = get_logger(__name__)


# Mock coverage database for development/testing
# In production, this would be replaced with actual GIS API calls
MOCK_COVERAGE_DATA = {
    "19107": {  # Philadelphia downtown - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "infrastructure": {
            "type": "Fiber",
            "network_element": {
                "switch_id": "PHI-SW-001",
                "switch_location": "123 Market St CO",
                "cabinet_id": "PHI-CAB-015",
                "fiber_pairs_available": 48,
                "splice_point": "SP-19107-MKT",
                "olt_chassis": "CISCO-ASR9K-001",
                "olt_port": "1/1/5"
            },
            "speed_capability": {
                "min_speed_mbps": 100,
                "max_speed_mbps": 10000,
                "symmetrical": True
            },
            "service_class": "Enterprise",
            "redundancy_available": True
        },
        "zone": "Metro-East-PA",
        "install_days": 2
    },
    "19103": {  # Philadelphia city center - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "infrastructure": {
            "type": "Fiber",
            "network_element": {
                "switch_id": "PHI-SW-002",
                "switch_location": "456 Broad St CO",
                "cabinet_id": "PHI-CAB-023",
                "fiber_pairs_available": 36,
                "splice_point": "SP-19103-BRD",
                "olt_chassis": "CISCO-ASR9K-002",
                "olt_port": "1/2/3"
            },
            "speed_capability": {
                "min_speed_mbps": 100,
                "max_speed_mbps": 5000,
                "symmetrical": True
            },
            "service_class": "Business",
            "redundancy_available": True
        },
        "zone": "Metro-Center-PA",
        "install_days": 5
    },
    "18000": {  # Rural Pennsylvania - limited coax
        "serviceable": True,
        "technology": "HFC",
        "infrastructure": {
            "type": "Coax/HFC",
            "network_element": {
                "node_id": "PA-NODE-185",
                "node_location": "Rural Rd Tap",
                "cmts_id": "CMTS-RURAL-001",
                "cmts_port": "5/1",
                "cable_pairs_available": 12,
                "amplifier_cascade": 3,
                "last_mile_type": "RG-6 Coax"
            },
            "speed_capability": {
                "min_speed_mbps": 50,
                "max_speed_mbps": 500,
                "symmetrical": False
            },
            "service_class": "Standard",
            "redundancy_available": False
        },
        "zone": "Rural-PA",
        "install_days": 10
    },
    "10001": {  # New York City - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "infrastructure": {
            "type": "Fiber",
            "network_element": {
                "switch_id": "NYC-SW-101",
                "switch_location": "Manhattan CO-1",
                "cabinet_id": "NYC-CAB-450",
                "fiber_pairs_available": 72,
                "splice_point": "SP-10001-5AV",
                "olt_chassis": "JUNIPER-MX960-101",
                "olt_port": "2/1/8"
            },
            "speed_capability": {
                "min_speed_mbps": 100,
                "max_speed_mbps": 10000,
                "symmetrical": True
            },
            "service_class": "Enterprise",
            "redundancy_available": True
        },
        "zone": "Metro-NYC",
        "install_days": 7
    },
    "90001": {  # Los Angeles - hybrid
        "serviceable": True,
        "technology": "DOCSIS 3.1",
        "infrastructure": {
            "type": "Coax/DOCSIS 3.1",
            "network_element": {
                "node_id": "LA-NODE-901",
                "node_location": "LA Downtown Hub",
                "cmts_id": "CMTS-LA-050",
                "cmts_port": "3/2",
                "cable_pairs_available": 24,
                "docsis_version": "3.1",
                "channel_bonding": "32x8"
            },
            "speed_capability": {
                "min_speed_mbps": 100,
                "max_speed_mbps": 1000,
                "symmetrical": False
            },
            "service_class": "Business",
            "redundancy_available": False
        },
        "zone": "Metro-LA",
        "install_days": 7
    },
    "60601": {  # Chicago downtown - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "infrastructure": {
            "type": "Fiber",
            "network_element": {
                "switch_id": "CHI-SW-201",
                "switch_location": "Chicago Loop CO",
                "cabinet_id": "CHI-CAB-310",
                "fiber_pairs_available": 60,
                "splice_point": "SP-60601-LOOP",
                "olt_chassis": "CISCO-ASR9K-201",
                "olt_port": "1/3/4"
            },
            "speed_capability": {
                "min_speed_mbps": 100,
                "max_speed_mbps": 10000,
                "symmetrical": True
            },
            "service_class": "Enterprise",
            "redundancy_available": True
        },
        "zone": "Metro-Chicago-Loop",
        "install_days": 5
    },
    "94102": {  # San Francisco - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "infrastructure": {
            "type": "Fiber",
            "network_element": {
                "switch_id": "SF-SW-301",
                "switch_location": "SF Downtown CO",
                "cabinet_id": "SF-CAB-501",
                "fiber_pairs_available": 54,
                "splice_point": "SP-94102-MKT",
                "olt_chassis": "JUNIPER-MX480-301",
                "olt_port": "1/4/2"
            },
            "speed_capability": {
                "min_speed_mbps": 100,
                "max_speed_mbps": 5000,
                "symmetrical": True
            },
            "service_class": "Business",
            "redundancy_available": True
        },
        "zone": "Metro-SF-Downtown",
        "install_days": 6
    },
    "02101": {  # Boston - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "infrastructure": {
            "type": "Fiber",
            "network_element": {
                "switch_id": "BOS-SW-401",
                "switch_location": "Boston Downtown CO",
                "cabinet_id": "BOS-CAB-620",
                "fiber_pairs_available": 48,
                "splice_point": "SP-02101-DTN",
                "olt_chassis": "CISCO-ASR9K-401",
                "olt_port": "1/5/6"
            },
            "speed_capability": {
                "min_speed_mbps": 100,
                "max_speed_mbps": 10000,
                "symmetrical": True
            },
            "service_class": "Enterprise",
            "redundancy_available": True
        },
        "zone": "Metro-Boston-Downtown",
        "install_days": 5
    },
    "98101": {  # Seattle - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$289/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$659/mo"
            },
        ],
        "zone": "Metro-Seattle",
        "install_days": 7
    },
    "30301": {  # Atlanta - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$249/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$599/mo"
            },
            {
                "id": "FIB-10G",
                "name": "Business Fiber 10 Gbps",
                "speeds": ["10 Gbps"],
                "price": "$999/mo"
            },
        ],
        "zone": "Metro-Atlanta",
        "install_days": 6
    },
    "33101": {  # Miami - hybrid
        "serviceable": True,
        "technology": "HFC",
        "products": [
            {
                "id": "COAX-200M",
                "name": "Business Coax 200 Mbps",
                "speeds": ["200 Mbps"],
                "price": "$89/mo"
            },
            {
                "id": "COAX-500M",
                "name": "Business Coax 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$159/mo"
            },
            {
                "id": "COAX-1G",
                "name": "Business Coax 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$259/mo"
            },
        ],
        "zone": "Metro-Miami",
        "install_days": 8
    },
    "75201": {  # Dallas - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$259/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$619/mo"
            },
        ],
        "zone": "Metro-Dallas",
        "install_days": 6
    },
    "85001": {  # Phoenix - hybrid
        "serviceable": True,
        "technology": "DOCSIS 3.1",
        "products": [
            {
                "id": "COAX-500M",
                "name": "Business Internet 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
            {
                "id": "COAX-1G",
                "name": "Business Internet 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$249/mo"
            },
        ],
        "zone": "Metro-Phoenix",
        "install_days": 7
    },
    "80201": {  # Denver - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$269/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$639/mo"
            },
            {
                "id": "FIB-10G",
                "name": "Business Fiber 10 Gbps",
                "speeds": ["10 Gbps"],
                "price": "$1039/mo"
            },
        ],
        "zone": "Metro-Denver",
        "install_days": 6
    },
    "20001": {  # Washington DC - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$289/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$669/mo"
            },
            {
                "id": "FIB-10G",
                "name": "Business Fiber 10 Gbps",
                "speeds": ["10 Gbps"],
                "price": "$1069/mo"
            },
        ],
        "zone": "Metro-DC",
        "install_days": 5
    },
    "55401": {  # Minneapolis - hybrid
        "serviceable": True,
        "technology": "HFC",
        "products": [
            {
                "id": "COAX-200M",
                "name": "Business Coax 200 Mbps",
                "speeds": ["200 Mbps"],
                "price": "$79/mo"
            },
            {
                "id": "COAX-500M",
                "name": "Business Coax 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
            {
                "id": "COAX-1G",
                "name": "Business Coax 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$249/mo"
            },
        ],
        "zone": "Metro-Minneapolis",
        "install_days": 8
    },
    "63101": {  # St. Louis - hybrid
        "serviceable": True,
        "technology": "HFC",
        "products": [
            {
                "id": "COAX-200M",
                "name": "Business Coax 200 Mbps",
                "speeds": ["200 Mbps"],
                "price": "$79/mo"
            },
            {
                "id": "COAX-500M",
                "name": "Business Coax 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
        ],
        "zone": "Metro-StLouis",
        "install_days": 9
    },
    "97201": {  # Portland - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$279/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$649/mo"
            },
        ],
        "zone": "Metro-Portland",
        "install_days": 7
    },
    "89101": {  # Las Vegas - hybrid
        "serviceable": True,
        "technology": "DOCSIS 3.1",
        "products": [
            {
                "id": "COAX-500M",
                "name": "Business Internet 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
            {
                "id": "COAX-1G",
                "name": "Business Internet 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$249/mo"
            },
        ],
        "zone": "Metro-LasVegas",
        "install_days": 7
    },
    "28201": {  # Charlotte - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$259/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$619/mo"
            },
        ],
        "zone": "Metro-Charlotte",
        "install_days": 6
    },
    "92101": {  # San Diego - hybrid
        "serviceable": True,
        "technology": "DOCSIS 3.1",
        "products": [
            {
                "id": "COAX-500M",
                "name": "Business Internet 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
            {
                "id": "COAX-1G",
                "name": "Business Internet 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$249/mo"
            },
        ],
        "zone": "Metro-SanDiego",
        "install_days": 7
    },
    "78701": {  # Austin - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$259/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$619/mo"
            },
            {
                "id": "FIB-10G",
                "name": "Business Fiber 10 Gbps",
                "speeds": ["10 Gbps"],
                "price": "$1019/mo"
            },
        ],
        "zone": "Metro-Austin",
        "install_days": 5
    },
    "37201": {  # Nashville - hybrid
        "serviceable": True,
        "technology": "HFC",
        "products": [
            {
                "id": "COAX-200M",
                "name": "Business Coax 200 Mbps",
                "speeds": ["200 Mbps"],
                "price": "$79/mo"
            },
            {
                "id": "COAX-500M",
                "name": "Business Coax 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
            {
                "id": "COAX-1G",
                "name": "Business Coax 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$249/mo"
            },
        ],
        "zone": "Metro-Nashville",
        "install_days": 8
    },
    "27601": {  # Raleigh - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$259/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$619/mo"
            },
        ],
        "zone": "Metro-Raleigh",
        "install_days": 6
    },
    "43201": {  # Columbus - hybrid
        "serviceable": True,
        "technology": "HFC",
        "products": [
            {
                "id": "COAX-200M",
                "name": "Business Coax 200 Mbps",
                "speeds": ["200 Mbps"],
                "price": "$79/mo"
            },
            {
                "id": "COAX-500M",
                "name": "Business Coax 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
        ],
        "zone": "Metro-Columbus",
        "install_days": 8
    },
    "46201": {  # Indianapolis - hybrid
        "serviceable": True,
        "technology": "HFC",
        "products": [
            {
                "id": "COAX-200M",
                "name": "Business Coax 200 Mbps",
                "speeds": ["200 Mbps"],
                "price": "$79/mo"
            },
            {
                "id": "COAX-500M",
                "name": "Business Coax 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
            {
                "id": "COAX-1G",
                "name": "Business Coax 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$249/mo"
            },
        ],
        "zone": "Metro-Indianapolis",
        "install_days": 8
    },
    "64101": {  # Kansas City - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$259/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$619/mo"
            },
        ],
        "zone": "Metro-KansasCity",
        "install_days": 7
    },
    "53201": {  # Milwaukee - hybrid
        "serviceable": True,
        "technology": "HFC",
        "products": [
            {
                "id": "COAX-200M",
                "name": "Business Coax 200 Mbps",
                "speeds": ["200 Mbps"],
                "price": "$79/mo"
            },
            {
                "id": "COAX-500M",
                "name": "Business Coax 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
        ],
        "zone": "Metro-Milwaukee",
        "install_days": 9
    },
    "48201": {  # Detroit - hybrid
        "serviceable": True,
        "technology": "HFC",
        "products": [
            {
                "id": "COAX-200M",
                "name": "Business Coax 200 Mbps",
                "speeds": ["200 Mbps"],
                "price": "$79/mo"
            },
            {
                "id": "COAX-500M",
                "name": "Business Coax 500 Mbps",
                "speeds": ["500 Mbps"],
                "price": "$149/mo"
            },
            {
                "id": "COAX-1G",
                "name": "Business Coax 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$249/mo"
            },
        ],
        "zone": "Metro-Detroit",
        "install_days": 8
    },
    "21201": {  # Baltimore - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$269/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$639/mo"
            },
        ],
        "zone": "Metro-Baltimore",
        "install_days": 6
    },
    "95101": {  # San Jose - full fiber
        "serviceable": True,
        "technology": "FTTP",
        "products": [
            {
                "id": "FIB-1G",
                "name": "Business Fiber 1 Gbps",
                "speeds": ["1 Gbps"],
                "price": "$299/mo"
            },
            {
                "id": "FIB-5G",
                "name": "Business Fiber 5 Gbps",
                "speeds": ["5 Gbps"],
                "price": "$699/mo"
            },
            {
                "id": "FIB-10G",
                "name": "Business Fiber 10 Gbps",
                "speeds": ["10 Gbps"],
                "price": "$1099/mo"
            },
        ],
        "zone": "Metro-SanJose",
        "install_days": 5
    },
    "73301": {  # Austin suburbs - limited service
        "serviceable": True,
        "technology": "HFC",
        "products": [
            {
                "id": "COAX-100M",
                "name": "Business Coax 100 Mbps",
                "speeds": ["100 Mbps"],
                "price": "$59/mo"
            },
            {
                "id": "COAX-200M",
                "name": "Business Coax 200 Mbps",
                "speeds": ["200 Mbps"],
                "price": "$89/mo"
            },
        ],
        "zone": "Suburban-Austin",
        "install_days": 12
    },
    "99501": {  # Anchorage - not serviceable
        "serviceable": False,
        "reason": "Outside coverage area - Alaska region not currently served"
    },
    "96801": {  # Honolulu - not serviceable
        "serviceable": False,
        "reason": "Outside coverage area - Hawaii region not currently served"
    },
    "88901": {  # Remote Nevada - not serviceable
        "serviceable": False,
        "reason": "Outside coverage area - rural region with no infrastructure"
    },
}


def check_service_availability(address: Dict[str, str]) -> Dict[str, Any]:
    """
    Checks if telecom services are available at the given address.
    
    This is the MAIN deterministic tool for the Serviceability Agent.
    Queries GIS/Coverage Map API to determine service availability and network infrastructure details.
    
    CRITICAL: This function NEVER invents data. All serviceability information
    comes from the GIS API (or mock data in development).
    
    Args:
        address: Dict with street, city, state, zip_code keys
        
    Returns:
        ServiceabilityResult dict with availability status, infrastructure details,
        network elements (switch, cable pairs), and speed capabilities
        
    Example:
        >>> check_service_availability({
        ...     "street": "123 Market Street",
        ...     "city": "Philadelphia",
        ...     "state": "PA",
        ...     "zip_code": "19107"
        ... })
        {
            "serviceable": True,
            "address": {...},
            "infrastructure": {
                "type": "Fiber",
                "network_element": {"switch_id": "PHI-SW-001", ...},
                "speed_capability": {"min_speed_mbps": 100, "max_speed_mbps": 10000}
            },
            "service_zone": "Metro-East-PA"
        }
    """
    logger.info(f"Checking serviceability for: {address['street']}, {address['city']}, {address['state']} {address['zip_code']}")
    
    # Generate cache key
    cache_key = f"serviceability:{address['zip_code']}:{address['street'].lower()}"
    
    # Check cache first (24-hour TTL)
    cached = get_cached_result(cache_key)
    if cached:
        logger.info("Returning cached serviceability result")
        return cached
    
    # Determine if using mock data or real API
    use_mock = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
    
    if use_mock:
        result = _mock_gis_lookup(address)
    else:
        result = _call_real_gis_api(address)
    
    # Cache the result for 24 hours
    cache_result(cache_key, result, ttl_hours=24)
    
    logger.info(f"Serviceability check complete: serviceable={result['serviceable']}")
    return result


def _mock_gis_lookup(address: Dict[str, str]) -> Dict[str, Any]:
    """
    Mock GIS lookup for development and testing.
    
    This simulates a GIS API response based on ZIP code, returning
    infrastructure and network resource details instead of product plans.
    """
    zip_code = address['zip_code']
    
    # Default to non-serviceable if ZIP not in database
    if zip_code not in MOCK_COVERAGE_DATA:
        logger.warning(f"ZIP code {zip_code} not found in coverage database")
        return {
            "serviceable": False,
            "address": address,
            "infrastructure": None,
            "reason": "No infrastructure at location. We're constantly expanding our network."
        }
    
    coverage = MOCK_COVERAGE_DATA[zip_code]
    
    if not coverage["serviceable"]:
        return {
            "serviceable": False,
            "address": address,
            "infrastructure": None,
            "reason": coverage.get("reason", "Service not available at this location")
        }
    
    # Return infrastructure details instead of products
    return {
        "serviceable": True,
        "address": address,
        "infrastructure": coverage["infrastructure"],
        "service_zone": coverage["zone"],
        "estimated_install_days": coverage["install_days"],
        "infrastructure_type": coverage["technology"]
    }


def _call_real_gis_api(address: Dict[str, str]) -> Dict[str, Any]:
    """
    Real GIS API integration for production use.
    
    This would connect to an actual GIS/serviceability API.
    Returns infrastructure and network resource details.
    Implement when production API is available.
    """
    import requests
    
    api_url = os.getenv("GIS_API_URL")
    api_key = os.getenv("GIS_API_KEY")
    
    if not api_url or not api_key:
        logger.error("GIS API credentials not configured")
        return {
            "serviceable": False,
            "address": address,
            "infrastructure": None,
            "reason": "Unable to verify serviceability at this time. Please contact our sales team."
        }
    
    try:
        # Make API call to real GIS service
        response = requests.post(
            f"{api_url}/serviceability/check",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=address,
            timeout=10
        )
        
        response.raise_for_status()
        
        data = response.json()
        
        # Transform API response to our schema (infrastructure-focused)
        return {
            "serviceable": data.get("available", False),
            "address": address,
            "infrastructure": data.get("infrastructure"),  # Expects infrastructure object from API
            "service_zone": data.get("zone"),
            "estimated_install_days": data.get("install_days"),
            "infrastructure_type": data.get("technology"),
            "reason": data.get("reason") if not data.get("available") else None
        }
        
    except requests.Timeout:
        logger.error("GIS API timeout")
        return {
            "serviceable": False,
            "address": address,
            "infrastructure": None,
            "reason": "Service check timed out. Please try again or contact our sales team."
        }
    except requests.RequestException as e:
        logger.error(f"GIS API error: {e}")
        return {
            "serviceable": False,
            "address": address,
            "infrastructure": None,
            "reason": "Unable to verify serviceability at this time. Please contact our sales team."
        }


def get_infrastructure_by_technology(technology: str, zone: str = "all") -> List[Dict[str, Any]]:
    """
    Returns infrastructure capabilities filtered by technology type.
    
    This tool returns network infrastructure capabilities and speed ranges
    for different technology types, NOT specific product plans or pricing.
    
    Args:
        technology: Technology type - "Fiber", "Coax", "HFC", "FTTP", "DOCSIS"
        zone: Service zone identifier (optional)
        
    Returns:
        List of infrastructure capability dicts matching criteria
        
    Example:
        >>> get_infrastructure_by_technology("FTTP")
        [
            {
                "technology": "FTTP",
                "min_speed_mbps": 100,
                "max_speed_mbps": 10000,
                "symmetrical": True,
                "service_classes": ["Enterprise", "Business"]
            },
            ...
        ]
    """
    logger.info(f"Fetching infrastructure capabilities for technology: {technology}, zone: {zone}")
    
    # Infrastructure capabilities by technology type
    infrastructure_catalog = {
        "FTTP": {
            "technology": "Fiber to the Premises (FTTP)",
            "min_speed_mbps": 100,
            "max_speed_mbps": 10000,
            "symmetrical": True,
            "service_classes": ["Enterprise", "Business"],
            "typical_equipment": ["OLT", "ONT", "Fiber Optic Cable"],
            "redundancy_capable": True
        },
        "HFC": {
            "technology": "Hybrid Fiber-Coax (HFC)",
            "min_speed_mbps": 50,
            "max_speed_mbps": 1000,
            "symmetrical": False,
            "service_classes": ["Business", "Standard"],
            "typical_equipment": ["CMTS", "Cable Modem", "Coax Cable"],
            "redundancy_capable": False
        },
        "DOCSIS 3.1": {
            "technology": "DOCSIS 3.1",
            "min_speed_mbps": 100,
            "max_speed_mbps": 1000,
            "symmetrical": False,
            "service_classes": ["Business", "Standard"],
            "typical_equipment": ["CMTS", "DOCSIS 3.1 Modem", "Coax Cable"],
            "redundancy_capable": False
        },
    }
    
    # Normalize technology name
    tech_normalized = technology.upper()
    
    # Map common aliases
    tech_aliases = {
        "FIBER": "FTTP",
        "COAX": "HFC",
        "DOCSIS": "DOCSIS 3.1",
    }
    
    tech_normalized = tech_aliases.get(tech_normalized, tech_normalized)
    
    infrastructure = infrastructure_catalog.get(tech_normalized)
    
    if infrastructure:
        logger.info(f"Found infrastructure capabilities for technology {tech_normalized}")
        return [infrastructure]
    else:
        logger.warning(f"No infrastructure data for technology {tech_normalized}")
        return []


def get_coverage_zones() -> List[str]:
    """
    Returns list of all service zones.
    
    Useful for informational queries about service areas.
    
    Returns:
        List of zone identifiers
    """
    zones = list(set(
        data["zone"]
        for data in MOCK_COVERAGE_DATA.values()
        if data["serviceable"]
    ))
    
    logger.info(f"Retrieved {len(zones)} coverage zones")
    return sorted(zones)
