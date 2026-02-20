"""
Product comparison tools.

Tools for comparing multiple products side-by-side and suggesting alternatives.
"""

from typing import Dict, Any, List, Optional
from ..utils.logger import get_logger
from .product_tools import get_product_by_id, PRODUCT_CATALOG

logger = get_logger(__name__)


def compare_products(product_ids: List[str]) -> Dict[str, Any]:
    """
    Compare multiple products side-by-side.
    
    Generates a comparison table showing key technical differences between products
    including speeds, features, and technology.
    
    Args:
        product_ids: List of 2-5 product IDs to compare
        
    Returns:
        dict with comparison data
        
    Example:
        >>> compare_products(["FIB-1G", "FIB-5G", "FIB-10G"])
        {
            'comparison': {...},
            'products_compared': 3,
            'recommendation': '...'
        }
    """
    logger.info(f"Comparing products: {product_ids}")
    
    if len(product_ids) < 2:
        return {
            "error": "At least 2 products required for comparison",
            "products_compared": 0
        }
    
    if len(product_ids) > 5:
        return {
            "error": "Maximum 5 products can be compared at once",
            "products_compared": 0
        }
    
    try:
        products = []
        not_found = []
        
        # Fetch all products
        for pid in product_ids:
            result = get_product_by_id(pid)
            if result.get('found'):
                products.append(result)
            else:
                not_found.append(pid)
        
        if not products:
            return {
                "error": "No valid products found",
                "not_found": not_found,
                "products_compared": 0
            }
        
        # Build comparison table
        comparison = {
            "products": [],
            "comparison_table": {
                "product_name": [],
                "technology": [],
                "download_speed": [],
                "upload_speed": [],
                "uptime_sla": [],
                "key_features": []
            }
        }
        
        for product in products:
            comparison["products"].append(product['product_id'])
            comparison["comparison_table"]["product_name"].append(product['product_name'])
            comparison["comparison_table"]["technology"].append(product['technology'])
            comparison["comparison_table"]["download_speed"].append(
                product['speeds'].get('download', 'N/A')
            )
            comparison["comparison_table"]["upload_speed"].append(
                product['speeds'].get('upload', 'N/A')
            )
            
            # Extract SLA from features (simplified)
            sla = "N/A"
            for feature in product.get('features', []):
                if 'SLA' in feature or 'uptime' in feature:
                    sla = feature
                    break
            comparison["comparison_table"]["uptime_sla"].append(sla)
            
            # Get top 3 key features
            key_features = product.get('features', [])[:3]
            comparison["comparison_table"]["key_features"].append(key_features)
        
        # Generate simple recommendation based on speed
        speeds = [p['speeds'].get('download', '0') for p in products]
        fastest_idx = speeds.index(max(speeds))
        
        recommendation = (
            f"For maximum performance, consider {products[fastest_idx]['product_name']}. "
            f"For general business fit, review SLA and feature requirements for each option."
        )
        
        response = {
            "comparison": comparison,
            "products_compared": len(products),
            "not_found": not_found,
            "recommendation": recommendation
        }
        
        logger.info(f"Comparison generated for {len(products)} products")
        return response
        
    except Exception as e:
        logger.error(f"Product comparison failed: {e}")
        return {
            "error": str(e),
            "products_compared": 0
        }


def suggest_alternatives(
    product_id: str,
    criteria: Optional[str] = None
) -> Dict[str, Any]:
    """
    Suggest alternative products based on a given product.
    
    Finds similar products or alternatives based on technical criteria like:
    - Same technology, different speed
    - Different technology, similar speed
    
    Args:
        product_id: Base product ID to find alternatives for
        criteria: Optional criteria ("faster", "similar", "different_tech")
        
    Returns:
        dict with suggested alternative products
        
    Example:
        >>> suggest_alternatives("FIB-5G", criteria="faster")
        {
            'base_product': {...},
            'alternatives': [...],
            'count': 2
        }
    """
    logger.info(f"Finding alternatives for {product_id} (criteria={criteria})")
    
    try:
        # Get base product
        base_product = get_product_by_id(product_id)
        
        if not base_product.get('found'):
            return {
                "error": f"Base product '{product_id}' not found",
                "alternatives": [],
                "count": 0
            }
        
        alternatives = []
        base_tech = base_product['technology']
        base_speed = base_product['speeds'].get('download', '')

        if criteria == "cheaper":
            return {
                "error": "Pricing criteria are handled by offer_management_agent",
                "alternatives": [],
                "count": 0
            }
        
        # Find alternatives based on criteria
        for pid, product in PRODUCT_CATALOG.items():
            if pid == product_id or not product.get('available', True):
                continue
            
            # Apply criteria filters
            include = False
            reason = ""
            
            if criteria == "faster":
                # Simple comparison based on numeric speed value
                base_speed_num = int(''.join(filter(str.isdigit, base_speed)) or '0')
                product_speed_num = int(''.join(filter(str.isdigit, product['speeds'].get('download', '0'))) or '0')
                if product_speed_num > base_speed_num:
                    include = True
                    reason = "Higher speed tier"
            
            elif criteria == "similar":
                if product['technology'] == base_tech:
                    include = True
                    reason = "Similar technology profile"
            
            elif criteria == "different_tech":
                # Different technology but similar speed/price
                if product['technology'] != base_tech:
                    include = True
                    reason = f"Alternative technology ({product['technology']})"
            
            else:
                if product.get('category') == base_product.get('category'):
                    include = True
                    reason = "Similar product category"
            
            if include:
                alternatives.append({
                    "product_id": product['product_id'],
                    "product_name": product['product_name'],
                    "technology": product['technology'],
                    "speeds": product['speeds'],
                    "reason": reason
                })

            # Sort by product id for deterministic output
            alternatives.sort(key=lambda x: x['product_id'])
        
        # Limit to top 5
        alternatives = alternatives[:5]
        
        response = {
            "base_product": {
                "product_id": base_product['product_id'],
                "product_name": base_product['product_name']
            },
            "alternatives": alternatives,
            "count": len(alternatives),
            "criteria": criteria or "general"
        }
        
        logger.info(f"Found {len(alternatives)} alternative products")
        return response
        
    except Exception as e:
        logger.error(f"Alternative suggestion failed: {e}")
        return {
            "error": str(e),
            "alternatives": [],
            "count": 0
        }


def get_best_value_product(max_budget: Optional[int] = None) -> Dict[str, Any]:
    """
    Get a technical best-fit recommendation without pricing.
    
    Args:
        max_budget: Deprecated (pricing is handled by OfferManagement)
        
    Returns:
        dict with recommended product
        
    Example:
        >>> get_best_value_product(max_budget=300)
        {'recommended': {...}, 'reason': '...'}
    """
    logger.info("Finding best fit product by technical capability")
    
    try:
        products = [p for p in PRODUCT_CATALOG.values() if p.get('available', True)]
        
        if not products:
            return {
                "found": False,
                "message": "No products available"
            }

        # Calculate score by technical throughput only
        scored_products = []
        for product in products:
            speed_str = product['speeds'].get('download', '0')
            speed_num = int(''.join(filter(str.isdigit, speed_str)) or '0')
            
            # Convert Gbps to Mbps for fair comparison
            if 'Gbps' in speed_str:
                speed_num *= 1000

            value_score = speed_num
            
            scored_products.append({
                "product": product,
                "value_score": value_score
            })
        
        # Sort by value score
        scored_products.sort(key=lambda x: x['value_score'], reverse=True)
        best_product = scored_products[0]['product']
        
        response = {
            "found": True,
            "recommended": {
                "product_id": best_product['product_id'],
                "product_name": best_product['product_name'],
                "speeds": best_product['speeds'],
                "technology": best_product['technology']
            },
            "reason": "Highest technical throughput among available products",
            "budget": None
        }
        
        logger.info(f"Recommended: {best_product['product_name']}")
        return response
        
    except Exception as e:
        logger.error(f"Best value search failed: {e}")
        return {
            "found": False,
            "error": str(e)
        }
