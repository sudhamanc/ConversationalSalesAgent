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
    
    Generates a comparison table showing key differences between products
    including speeds, pricing, features, and technology.
    
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
                "price": [],
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
            comparison["comparison_table"]["price"].append(product['price'])
            
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
            f"For budget-conscious options, {products[0]['product_name']} offers great value."
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
    
    Finds similar products or alternatives based on criteria like:
    - Same technology, different speed
    - Different technology, similar speed
    - Lower/higher price points
    
    Args:
        product_id: Base product ID to find alternatives for
        criteria: Optional criteria ("cheaper", "faster", "similar", "different_tech")
        
    Returns:
        dict with suggested alternative products
        
    Example:
        >>> suggest_alternatives("FIB-5G", criteria="cheaper")
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
        base_price = int(base_product['price'].replace('$', '').replace('/month', ''))
        base_tech = base_product['technology']
        base_speed = base_product['speeds'].get('download', '')
        
        # Find alternatives based on criteria
        for pid, product in PRODUCT_CATALOG.items():
            if pid == product_id or not product.get('available', True):
                continue
            
            product_price = int(product['price'].replace('$', '').replace('/month', ''))
            
            # Apply criteria filters
            include = False
            reason = ""
            
            if criteria == "cheaper":
                if product_price < base_price:
                    include = True
                    reason = f"${base_price - product_price}/month less expensive"
            
            elif criteria == "faster":
                # Simple comparison based on numeric speed value
                base_speed_num = int(''.join(filter(str.isdigit, base_speed)) or '0')
                product_speed_num = int(''.join(filter(str.isdigit, product['speeds'].get('download', '0'))) or '0')
                if product_speed_num > base_speed_num:
                    include = True
                    reason = "Higher speed tier"
            
            elif criteria == "similar":
                # Similar technology and similar price range (±30%)
                if (product['technology'] == base_tech and 
                    abs(product_price - base_price) / base_price < 0.3):
                    include = True
                    reason = "Similar technology and price range"
            
            elif criteria == "different_tech":
                # Different technology but similar speed/price
                if product['technology'] != base_tech:
                    include = True
                    reason = f"Alternative technology ({product['technology']})"
            
            else:
                # No criteria - suggest based on being in same category or similar price
                if (product.get('category') == base_product.get('category') or
                    abs(product_price - base_price) / base_price < 0.5):
                    include = True
                    reason = "Similar product category"
            
            if include:
                alternatives.append({
                    "product_id": product['product_id'],
                    "product_name": product['product_name'],
                    "technology": product['technology'],
                    "price": product['price'],
                    "speeds": product['speeds'],
                    "reason": reason
                })
        
        # Sort by price
        alternatives.sort(key=lambda x: int(x['price'].replace('$', '').replace('/month', '')))
        
        # Limit to top 5
        alternatives = alternatives[:5]
        
        response = {
            "base_product": {
                "product_id": base_product['product_id'],
                "product_name": base_product['product_name'],
                "price": base_product['price']
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
    Get the best value product within a budget.
    
    Args:
        max_budget: Maximum monthly budget in dollars (optional)
        
    Returns:
        dict with recommended product
        
    Example:
        >>> get_best_value_product(max_budget=300)
        {'recommended': {...}, 'reason': '...'}
    """
    logger.info(f"Finding best value product (budget={max_budget})")
    
    try:
        products = [p for p in PRODUCT_CATALOG.values() if p.get('available', True)]
        
        # Filter by budget if provided
        if max_budget:
            products = [
                p for p in products
                if int(p['price'].replace('$', '').replace('/month', '')) <= max_budget
            ]
        
        if not products:
            return {
                "found": False,
                "message": f"No products found within ${max_budget}/month budget" if max_budget else "No products available"
            }
        
        # Calculate value score (speed / price ratio)
        scored_products = []
        for product in products:
            price = int(product['price'].replace('$', '').replace('/month', ''))
            speed_str = product['speeds'].get('download', '0')
            speed_num = int(''.join(filter(str.isdigit, speed_str)) or '0')
            
            # Convert Gbps to Mbps for fair comparison
            if 'Gbps' in speed_str:
                speed_num *= 1000
            
            value_score = speed_num / price if price > 0 else 0
            
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
                "price": best_product['price'],
                "speeds": best_product['speeds'],
                "technology": best_product['technology']
            },
            "reason": f"Best speed-to-price ratio within your budget",
            "budget": max_budget
        }
        
        logger.info(f"Recommended: {best_product['product_name']}")
        return response
        
    except Exception as e:
        logger.error(f"Best value search failed: {e}")
        return {
            "found": False,
            "error": str(e)
        }
