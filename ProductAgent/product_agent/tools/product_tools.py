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
    }
}


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
            products = [p for p in products if p['category'] == category]
        
        # Filter only available products
        products = [p for p in products if p.get('available', True)]
        
        # Create simplified catalog items
        catalog_items = [
            {
                "product_id": p['product_id'],
                "product_name": p['product_name'],
                "category": p['category'],
                "technology": p['technology'],
                "price": p['price'],
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
        max_price: Maximum monthly price in dollars
        
    Returns:
        dict with matching products
        
    Example:
        >>> search_products_by_criteria(technology="FTTP", max_price=600)
        {'products': [...], 'count': 2, 'criteria': {...}}
    """
    logger.info(f"Searching products (speed={speed}, tech={technology}, max_price={max_price})")
    
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
            
            # Check price
            if max_price:
                # Extract price number from string like "$599/month"
                price_str = product['price'].replace('$', '').replace('/month', '')
                try:
                    product_price = int(price_str)
                    if product_price > max_price:
                        matches = False
                except ValueError:
                    pass
            
            if matches and product.get('available', True):
                matching.append({
                    "product_id": product['product_id'],
                    "product_name": product['product_name'],
                    "technology": product['technology'],
                    "speeds": product['speeds'],
                    "price": product['price'],
                    "description": product['description']
                })
        
        response = {
            "products": matching,
            "count": len(matching),
            "criteria": {
                "speed": speed,
                "technology": technology,
                "max_price": max_price
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
