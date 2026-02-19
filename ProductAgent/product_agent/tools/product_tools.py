"""
Product catalog and lookup tools.

These tools provide access to the product catalog and individual product details.
"""

from typing import Dict, Any, Optional, List
from ..utils.logger import get_logger
from ..utils.cache import cache_result, get_cached_result

logger = get_logger(__name__)


# Mock product catalog for development/testing
# In production, this would query a product database or API
PRODUCT_CATALOG = {
    "FIB-1G": {
        "product_id": "FIB-1G",
        "product_name": "Business Fiber 1 Gbps",
        "category": "Fiber Internet",
        "technology": "FTTP",
        "speeds": {
            "download": "1 Gbps",
            "upload": "1 Gbps"
        },
        "price": "$249/month",
        "description": "Symmetrical 1 Gbps fiber internet perfect for small to medium businesses",
        "features": [
            "99.9% uptime SLA",
            "Symmetrical speeds",
            "24/7 business support",
            "Free installation",
            "Business Gateway router included"
        ],
        "available": True
    },
    "FIB-5G": {
        "product_id": "FIB-5G",
        "product_name": "Business Fiber 5 Gbps",
        "category": "Fiber Internet",
        "technology": "FTTP",
        "speeds": {
            "download": "5 Gbps",
            "upload": "5 Gbps"
        },
        "price": "$599/month",
        "description": "High-performance 5 Gbps fiber for bandwidth-intensive businesses",
        "features": [
            "99.9% uptime SLA",
            "Symmetrical speeds",
            "Priority 24/7 support",
            "Free installation",
            "Premium Business Gateway included",
            "5 static IP addresses included"
        ],
        "available": True
    },
    "FIB-10G": {
        "product_id": "FIB-10G",
        "product_name": "Business Fiber 10 Gbps",
        "category": "Fiber Internet",
        "technology": "FTTP",
        "speeds": {
            "download": "10 Gbps",
            "upload": "10 Gbps"
        },
        "price": "$999/month",
        "description": "Enterprise-grade 10 Gbps fiber for maximum performance",
        "features": [
            "99.95% uptime SLA",
            "Symmetrical speeds",
            "Dedicated account manager",
            "Priority 24/7 support",
            "Free installation",
            "Enterprise Gateway with redundancy",
            "10 static IP addresses included",
            "Managed security options"
        ],
        "available": True
    },
    "COAX-200M": {
        "product_id": "COAX-200M",
        "product_name": "Business Internet 200 Mbps",
        "category": "Coax Internet",
        "technology": "HFC",
        "speeds": {
            "download": "200 Mbps",
            "upload": "20 Mbps"
        },
        "price": "$79/month",
        "description": "Affordable high-speed internet for small businesses",
        "features": [
            "99.5% uptime SLA",
            "Business support",
            "Standard installation",
            "Business modem included"
        ],
        "available": True
    },
    "COAX-500M": {
        "product_id": "COAX-500M",
        "product_name": "Business Internet 500 Mbps",
        "category": "Coax Internet",
        "technology": "HFC",
        "speeds": {
            "download": "500 Mbps",
            "upload": "50 Mbps"
        },
        "price": "$149/month",
        "description": "Mid-tier internet for growing businesses",
        "features": [
            "99.5% uptime SLA",
            "Business support",
            "Free installation",
            "Business Gateway included",
            "1 static IP address available"
        ],
        "available": True
    },
    "COAX-1G": {
        "product_id": "COAX-1G",
        "product_name": "Business Internet 1 Gbps",
        "category": "Coax Internet",
        "technology": "DOCSIS 3.1",
        "speeds": {
            "download": "1 Gbps",
            "upload": "100 Mbps"
        },
        "price": "$249/month",
        "description": "High-speed coax internet with gigabit download",
        "features": [
            "99.5% uptime SLA",
            "Business support",
            "Free installation",
            "Advanced Business Gateway",
            "2 static IP addresses included"
        ],
        "available": True
    },
    # ── Voice Products ──────────────────────────────────────────
    "VOICE-BAS": {
        "product_id": "VOICE-BAS",
        "product_name": "Business Voice Basic",
        "category": "Voice",
        "technology": "VoIP",
        "speeds": {
            "lines": "1-5 lines",
            "codec": "G.711 HD Voice"
        },
        "price": "$29/month/line",
        "description": "Essential business phone service for small offices with 1-5 lines",
        "features": [
            "HD Voice quality",
            "Voicemail to email",
            "Auto-attendant",
            "Call forwarding & transfer",
            "Free local and long-distance calling",
            "Business support"
        ],
        "available": True
    },
    "VOICE-STD": {
        "product_id": "VOICE-STD",
        "product_name": "Business Voice Standard",
        "category": "Voice",
        "technology": "VoIP",
        "speeds": {
            "lines": "5-20 lines",
            "codec": "G.711 HD Voice"
        },
        "price": "$24/month/line",
        "description": "Full-featured business phone system for growing teams with 5-20 lines",
        "features": [
            "HD Voice quality",
            "Voicemail to email",
            "Auto-attendant with multi-level IVR",
            "Call forwarding, transfer & parking",
            "Hunt groups and ring groups",
            "Free local and long-distance calling",
            "Conference bridge (10 participants)",
            "Priority business support"
        ],
        "available": True
    },
    "VOICE-ENT": {
        "product_id": "VOICE-ENT",
        "product_name": "Business Voice Enterprise",
        "category": "Voice",
        "technology": "SIP Trunking",
        "speeds": {
            "lines": "20-100+ lines",
            "codec": "G.711/G.722 HD Voice"
        },
        "price": "$19/month/line",
        "description": "Enterprise-grade SIP trunking for large organizations with PBX integration",
        "features": [
            "HD Voice quality with G.722",
            "SIP trunk integration with existing PBX",
            "Unlimited concurrent calls",
            "E911 support",
            "Toll-free number options",
            "Call recording and analytics",
            "Conference bridge (50 participants)",
            "Dedicated account manager",
            "99.99% voice uptime SLA"
        ],
        "available": True
    },
    "VOICE-UCAAS": {
        "product_id": "VOICE-UCAAS",
        "product_name": "Unified Communications (UCaaS)",
        "category": "Voice",
        "technology": "Cloud UCaaS",
        "speeds": {
            "lines": "Unlimited users",
            "codec": "Opus/G.722 HD Voice"
        },
        "price": "$39/month/user",
        "description": "All-in-one unified communications platform with voice, video, messaging, and collaboration",
        "features": [
            "HD Voice and video calling",
            "Team messaging and presence",
            "Video conferencing (up to 200 participants)",
            "Screen sharing and file sharing",
            "Mobile and desktop apps",
            "CRM integrations (Salesforce, HubSpot)",
            "Call analytics and reporting dashboard",
            "Auto-attendant with AI routing",
            "99.99% platform uptime SLA",
            "24/7 priority support"
        ],
        "available": True
    },
    # ── SD-WAN Products ─────────────────────────────────────────
    "SDWAN-ESS": {
        "product_id": "SDWAN-ESS",
        "product_name": "SD-WAN Essentials",
        "category": "SD-WAN",
        "technology": "SD-WAN",
        "speeds": {
            "throughput": "Up to 250 Mbps",
            "sites": "1-5 sites"
        },
        "price": "$199/month/site",
        "description": "Entry-level SD-WAN for small multi-site businesses with basic traffic optimization",
        "features": [
            "Application-aware routing",
            "Dual-WAN failover",
            "Basic QoS and traffic shaping",
            "Cloud-managed portal",
            "Zero-touch provisioning",
            "SD-WAN gateway appliance included",
            "Business support"
        ],
        "available": True
    },
    "SDWAN-PRO": {
        "product_id": "SDWAN-PRO",
        "product_name": "SD-WAN Professional",
        "category": "SD-WAN",
        "technology": "SD-WAN",
        "speeds": {
            "throughput": "Up to 1 Gbps",
            "sites": "5-25 sites"
        },
        "price": "$399/month/site",
        "description": "Advanced SD-WAN with integrated security and multi-cloud connectivity",
        "features": [
            "Application-aware routing with AI optimization",
            "Multi-WAN failover (up to 4 links)",
            "Advanced QoS with 8 traffic classes",
            "Integrated firewall and IPS",
            "Cloud-managed portal with analytics",
            "Multi-cloud connectivity (AWS, Azure, GCP)",
            "Zero-touch provisioning",
            "SD-WAN gateway appliance included",
            "99.9% uptime SLA",
            "Priority 24/7 support"
        ],
        "available": True
    },
    "SDWAN-ENT": {
        "product_id": "SDWAN-ENT",
        "product_name": "SD-WAN Enterprise",
        "category": "SD-WAN",
        "technology": "SD-WAN",
        "speeds": {
            "throughput": "Up to 10 Gbps",
            "sites": "25-500+ sites"
        },
        "price": "$699/month/site",
        "description": "Enterprise-class SD-WAN with full SASE integration, global backbone, and managed services",
        "features": [
            "AI-driven application optimization",
            "Multi-WAN failover with sub-second switchover",
            "Full SASE integration (ZTNA, SWG, CASB)",
            "Global private backbone network",
            "Advanced analytics and AIOps",
            "Multi-cloud connectivity with private peering",
            "Managed service option available",
            "Custom traffic policies per application",
            "99.99% uptime SLA",
            "Dedicated account manager",
            "24/7 NOC monitoring"
        ],
        "available": True
    },
    # ── Business Mobile Products ────────────────────────────────
    "MOB-BAS": {
        "product_id": "MOB-BAS",
        "product_name": "Business Mobile Basic",
        "category": "Business Mobile",
        "technology": "4G LTE / 5G",
        "speeds": {
            "data": "10 GB/month",
            "network": "4G LTE"
        },
        "price": "$35/month/line",
        "description": "Essential business mobile plan with 10 GB data for cost-conscious teams",
        "features": [
            "10 GB high-speed data per line",
            "Unlimited talk and text",
            "4G LTE nationwide coverage",
            "Mobile hotspot (5 GB)",
            "Business account management portal",
            "Device financing available"
        ],
        "available": True
    },
    "MOB-UNL": {
        "product_id": "MOB-UNL",
        "product_name": "Business Mobile Unlimited",
        "category": "Business Mobile",
        "technology": "5G",
        "speeds": {
            "data": "Unlimited",
            "network": "5G Nationwide"
        },
        "price": "$55/month/line",
        "description": "Unlimited 5G business mobile for teams that need reliable, always-on connectivity",
        "features": [
            "Unlimited high-speed 5G data",
            "Unlimited talk and text",
            "5G Nationwide coverage",
            "Mobile hotspot (25 GB)",
            "International texting to 200+ countries",
            "Business account management portal",
            "Device financing available",
            "Priority network access"
        ],
        "available": True
    },
    "MOB-PREM": {
        "product_id": "MOB-PREM",
        "product_name": "Business Mobile Premium",
        "category": "Business Mobile",
        "technology": "5G Ultra Wideband",
        "speeds": {
            "data": "Unlimited Premium",
            "network": "5G Ultra Wideband"
        },
        "price": "$75/month/line",
        "description": "Premium 5G Ultra Wideband mobile for executives and power users with global roaming",
        "features": [
            "Unlimited premium 5G Ultra Wideband data",
            "Unlimited talk and text",
            "5G Ultra Wideband access (fastest speeds)",
            "Mobile hotspot (50 GB)",
            "International roaming in 30+ countries",
            "Apple Watch / smartwatch connectivity included",
            "Premium device trade-in offers",
            "Business account management portal",
            "Dedicated business support line",
            "Mobile device management (MDM) integration"
        ],
        "available": True
    }
}


def _strip_pricing_fields() -> None:
    """Ensure ProductAgent does not expose commercial pricing fields."""
    for product in PRODUCT_CATALOG.values():
        product.pop("price", None)


_strip_pricing_fields()


def _normalize_category_filter(category: str) -> str:
    """Normalize category aliases to canonical catalog categories."""
    normalized = category.strip().lower()
    alias_map = {
        "voice": "Voice",
        "business voice": "Voice",
        "mobile": "Business Mobile",
        "business mobile": "Business Mobile",
        "wireless": "Business Mobile",
        "sd-wan": "SD-WAN",
        "sdwan": "SD-WAN",
        "wan": "SD-WAN",
        "fiber": "Fiber Internet",
        "fiber internet": "Fiber Internet",
        "coax": "Coax Internet",
        "coax internet": "Coax Internet",
        "internet": "Fiber Internet",
    }
    return alias_map.get(normalized, category)


def list_available_products(category: Optional[str] = None) -> Dict[str, Any]:
    """
    List all available products or filter by category.
    
    Args:
        category: Optional category filter (e.g., "Fiber Internet", "Coax Internet")
        
    Returns:
        dict with list of products
        
    Examples:
        >>> list_available_products()
        {'products': [...], 'count': 6}
        
        >>> list_available_products(category="Fiber Internet")
        {'products': [...], 'count': 3, 'category': 'Fiber Internet'}
    """
    logger.info(f"Listing products (category={category})")
    
    try:
        products = list(PRODUCT_CATALOG.values())
        
        # Filter by category if provided
        if category:
            category = _normalize_category_filter(category)
            products = [p for p in products if p['category'].lower() == category.lower()]
        
        # Filter only available products
        products = [p for p in products if p.get('available', True)]
        
        # Create simplified catalog items
        catalog_items = [
            {
                "product_id": p['product_id'],
                "product_name": p['product_name'],
                "category": p['category'],
                "technology": p['technology'],
                "speeds": p['speeds']
            }
            for p in products
        ]
        
        response = {
            "products": catalog_items,
            "count": len(catalog_items)
        }
        
        if category:
            response['category'] = category
        
        logger.info(f"Found {len(catalog_items)} products")
        return response
        
    except Exception as e:
        logger.error(f"Failed to list products: {e}")
        return {
            "products": [],
            "count": 0,
            "error": str(e)
        }


def get_product_by_id(product_id: str) -> Dict[str, Any]:
    """
    Get complete product information by product ID.
    
    Args:
        product_id: Product identifier (e.g., "FIB-5G")
        
    Returns:
        dict with complete product information
        
    Example:
        >>> get_product_by_id("FIB-5G")
        {'product_id': 'FIB-5G', 'product_name': '...', 'found': True, ...}
    """
    logger.info(f"Getting product by ID: {product_id}")
    
    # Check cache
    cache_key = f"product:{product_id}"
    cached = get_cached_result(cache_key)
    if cached:
        logger.debug("Returning cached product")
        return cached
    
    try:
        if product_id not in PRODUCT_CATALOG:
            logger.warning(f"Product not found: {product_id}")
            return {
                "found": False,
                "product_id": product_id,
                "message": f"Product '{product_id}' not found in catalog"
            }
        
        product = PRODUCT_CATALOG[product_id].copy()
        product['found'] = True
        
        # Cache result
        cache_result(cache_key, product)
        
        logger.info(f"Found product: {product['product_name']}")
        return product
        
    except Exception as e:
        logger.error(f"Failed to get product: {e}")
        return {
            "found": False,
            "error": str(e)
        }


def search_products_by_criteria(
    speed: Optional[str] = None,
    technology: Optional[str] = None,
    max_price: Optional[int] = None
) -> Dict[str, Any]:
    """
    Search products by specific criteria.
    
    Args:
        speed: Speed requirement (e.g., "1 Gbps", "500 Mbps")
        technology: Technology type (e.g., "FTTP", "HFC", "DOCSIS 3.1")
        max_price: Deprecated (pricing is handled by OfferManagement)
        
    Returns:
        dict with matching products
        
    Example:
        >>> search_products_by_criteria(technology="FTTP", max_price=600)
        {'products': [...], 'count': 2, 'criteria': {...}}
    """
    logger.info(f"Searching products (speed={speed}, tech={technology})")
    
    try:
        products = list(PRODUCT_CATALOG.values())
        matching = []
        
        for product in products:
            # Check if product matches criteria
            matches = True
            
            # Check technology
            if technology and product['technology'] != technology:
                matches = False
            
            # Check speed (simplified - checks download speed)
            if speed and speed not in product['speeds'].get('download', ''):
                matches = False
            
            if matches and product.get('available', True):
                matching.append({
                    "product_id": product['product_id'],
                    "product_name": product['product_name'],
                    "technology": product['technology'],
                    "speeds": product['speeds'],
                    "description": product['description']
                })
        
        response = {
            "products": matching,
            "count": len(matching),
            "criteria": {
                "speed": speed,
                "technology": technology,
                "max_price": None
            }
        }
        
        logger.info(f"Found {len(matching)} matching products")
        return response
        
    except Exception as e:
        logger.error(f"Product search failed: {e}")
        return {
            "products": [],
            "count": 0,
            "error": str(e)
        }


def get_product_categories() -> Dict[str, Any]:
    """
    Get list of all product categories.
    
    Returns:
        dict with list of categories
    """
    logger.info("Getting product categories")
    
    try:
        categories = set()
        for product in PRODUCT_CATALOG.values():
            categories.add(product['category'])
        
        return {
            "categories": sorted(list(categories)),
            "count": len(categories)
        }
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        return {
            "categories": [],
            "count": 0,
            "error": str(e)
        }
