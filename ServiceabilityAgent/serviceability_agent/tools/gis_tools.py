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
        "zone": "Metro-East-PA",
        "install_days": 5
    },
    "19103": {  # Philadelphia city center - full fiber
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
        ],
        "zone": "Metro-Center-PA",
        "install_days": 5
    },
    "18000": {  # Rural Pennsylvania - limited coax
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
        "zone": "Rural-PA",
        "install_days": 10
    },
    "10001": {  # New York City - full fiber
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
        "zone": "Metro-NYC",
        "install_days": 7
    },
    "90001": {  # Los Angeles - hybrid
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
        "zone": "Metro-LA",
        "install_days": 7
    },
    "60601": {  # Chicago downtown - full fiber
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
            {
                "id": "FIB-10G",
                "name": "Business Fiber 10 Gbps",
                "speeds": ["10 Gbps"],
                "price": "$1049/mo"
            },
        ],
        "zone": "Metro-Chicago-Loop",
        "install_days": 5
    },
    "94102": {  # San Francisco - full fiber
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
        ],
        "zone": "Metro-SF-Downtown",
        "install_days": 6
    },
    "02101": {  # Boston - full fiber
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
                "price": "$629/mo"
            },
            {
                "id": "FIB-10G",
                "name": "Business Fiber 10 Gbps",
                "speeds": ["10 Gbps"],
                "price": "$1029/mo"
            },
        ],
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
    Queries GIS/Coverage Map API to determine service availability.
    
    CRITICAL: This function NEVER invents data. All serviceability information
    comes from the GIS API (or mock data in development).
    
    Args:
        address: Dict with street, city, state, zip_code keys
        
    Returns:
        ServiceabilityResult dict with availability status and products
        
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
            "available_products": [...],
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
    
    This simulates a GIS API response based on ZIP code.
    """
    zip_code = address['zip_code']
    
    # Default to non-serviceable if ZIP not in database
    if zip_code not in MOCK_COVERAGE_DATA:
        logger.warning(f"ZIP code {zip_code} not found in coverage database")
        return {
            "serviceable": False,
            "address": address,
            "available_products": [],
            "reason": "No infrastructure at location. We're constantly expanding our network."
        }
    
    coverage = MOCK_COVERAGE_DATA[zip_code]
    
    if not coverage["serviceable"]:
        return {
            "serviceable": False,
            "address": address,
            "available_products": [],
            "reason": coverage.get("reason", "Service not available at this location")
        }
    
    # Build product list
    products = [
        {
            "product_id": p["id"],
            "product_name": p["name"],
            "technology": coverage["technology"],
            "speeds": p["speeds"],
            "available": True,
            "price": p.get("price")
        }
        for p in coverage["products"]
    ]
    
    return {
        "serviceable": True,
        "address": address,
        "available_products": products,
        "service_zone": coverage["zone"],
        "estimated_install_days": coverage["install_days"],
        "infrastructure_type": coverage["technology"]
    }


def _call_real_gis_api(address: Dict[str, str]) -> Dict[str, Any]:
    """
    Real GIS API integration for production use.
    
    This would connect to an actual GIS/serviceability API.
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
            "available_products": [],
            "reason": "Unable to verify serviceability at this time. Please contact our sales team."
        }
    
    try:
        # Make API request
        response = requests.post(
            f"{api_url}/serviceability/check",
            json={"address": address},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5  # 5 second timeout
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Transform API response to our schema
        return {
            "serviceable": data.get("available", False),
            "address": address,
            "available_products": data.get("products", []),
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
            "available_products": [],
            "reason": "Service check timed out. Please try again or contact our sales team."
        }
    except requests.RequestException as e:
        logger.error(f"GIS API error: {e}")
        return {
            "serviceable": False,
            "address": address,
            "available_products": [],
            "reason": "Unable to verify serviceability at this time. Please contact our sales team."
        }


def get_products_by_technology(technology: str, zone: str = "all") -> List[Dict[str, Any]]:
    """
    Returns available products filtered by infrastructure technology.
    
    This is a supplementary tool for product catalog queries.
    
    Args:
        technology: Technology type - "Fiber", "Coax", "HFC", "FTTP", "DOCSIS"
        zone: Service zone identifier (optional)
        
    Returns:
        List of product dicts matching criteria
        
    Example:
        >>> get_products_by_technology("FTTP")
        [
            {"id": "FIB-1G", "name": "Business Fiber 1G", "speed": "1 Gbps", ...},
            ...
        ]
    """
    logger.info(f"Fetching products for technology: {technology}, zone: {zone}")
    
    # Mock product catalog by technology
    product_catalog = {
        "FTTP": [
            {"id": "FIB-1G", "name": "Business Fiber 1G", "speed": "1 Gbps", "price": "$249/mo"},
            {"id": "FIB-5G", "name": "Business Fiber 5G", "speed": "5 Gbps", "price": "$599/mo"},
            {"id": "FIB-10G", "name": "Business Fiber 10G", "speed": "10 Gbps", "price": "$999/mo"},
        ],
        "HFC": [
            {"id": "COAX-200M", "name": "Business Coax 200M", "speed": "200 Mbps", "price": "$79/mo"},
            {"id": "COAX-500M", "name": "Business Coax 500M", "speed": "500 Mbps", "price": "$149/mo"},
        ],
        "DOCSIS 3.1": [
            {"id": "COAX-500M", "name": "Business Internet 500M", "speed": "500 Mbps", "price": "$149/mo"},
            {"id": "COAX-1G", "name": "Business Internet 1G", "speed": "1 Gbps", "price": "$249/mo"},
        ],
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
    
    products = product_catalog.get(tech_normalized, [])
    
    logger.info(f"Found {len(products)} products for technology {tech_normalized}")
    return products


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
