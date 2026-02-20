"""
Unit tests for Product Agent tools.
"""

import pytest
from product_agent.tools.product_tools import (
    list_available_products,
    get_product_by_id,
    search_products_by_criteria,
    get_product_categories,
)
from product_agent.tools.comparison_tools import (
    compare_products,
    suggest_alternatives,
    get_best_value_product,
)


class TestProductTools:
    """Tests for product catalog tools"""
    
    def test_list_all_products(self):
        """Test listing all products"""
        result = list_available_products()
        
        assert 'products' in result
        assert 'count' in result
        assert result['count'] > 0
        assert len(result['products']) == result['count']
    
    def test_list_products_by_category(self):
        """Test listing products filtered by category"""
        result = list_available_products(category="Fiber Internet")
        
        assert 'products' in result
        assert 'category' in result
        assert result['category'] == "Fiber Internet"
        
        # All products should be fiber
        for product in result['products']:
            assert product['category'] == "Fiber Internet"
    
    def test_get_product_by_id_success(self):
        """Test getting product by valid ID"""
        result = get_product_by_id("FIB-5G")
        
        assert result['found'] is True
        assert result['product_id'] == "FIB-5G"
        assert result['product_name'] == "Business Fiber 5 Gbps"
        assert 'speeds' in result
        assert 'features' in result
    
    def test_get_product_by_id_not_found(self):
        """Test getting product with invalid ID"""
        result = get_product_by_id("INVALID-ID")
        
        assert result['found'] is False
        assert 'message' in result
    
    def test_search_products_by_technology(self):
        """Test searching products by technology"""
        result = search_products_by_criteria(technology="FTTP")
        
        assert 'products' in result
        assert result['count'] > 0
        
        # All results should be FTTP
        for product in result['products']:
            assert product['technology'] == "FTTP"
    
    def test_search_products_ignores_max_price_filter(self):
        """Pricing filters are handled by OfferManagement, not ProductAgent"""
        result = search_products_by_criteria(max_price=300)
        assert 'products' in result
        assert result['criteria']['max_price'] is None
    
    def test_get_product_categories(self):
        """Test getting all product categories"""
        result = get_product_categories()
        
        assert 'categories' in result
        assert 'count' in result
        assert result['count'] > 0
        assert "Fiber Internet" in result['categories']


class TestComparisonTools:
    """Tests for product comparison tools"""
    
    def test_compare_products_success(self):
        """Test comparing multiple products"""
        result = compare_products(["FIB-1G", "FIB-5G", "FIB-10G"])
        
        assert 'comparison' in result
        assert 'products_compared' in result
        assert result['products_compared'] == 3
        assert 'recommendation' in result
        
        # Check comparison table structure
        comparison = result['comparison']
        assert 'comparison_table' in comparison
        assert len(comparison['comparison_table']['product_name']) == 3
    
    def test_compare_products_too_few(self):
        """Test comparison with too few products"""
        result = compare_products(["FIB-1G"])
        
        assert 'error' in result
        assert result['products_compared'] == 0
    
    def test_compare_products_too_many(self):
        """Test comparison with too many products"""
        product_ids = [f"PROD-{i}" for i in range(10)]
        result = compare_products(product_ids)
        
        assert 'error' in result
        assert result['products_compared'] == 0
    
    def test_suggest_alternatives_cheaper_redirect(self):
        """Cheaper criteria should redirect to OfferManagement"""
        result = suggest_alternatives("FIB-10G", criteria="cheaper")
        assert 'error' in result
        assert result['count'] == 0
    
    def test_suggest_alternatives_faster(self):
        """Test suggesting faster alternatives"""
        result = suggest_alternatives("FIB-1G", criteria="faster")
        
        assert 'base_product' in result
        assert 'alternatives' in result
        # Should find faster options
        assert result['count'] > 0
    
    def test_suggest_alternatives_invalid_product(self):
        """Test suggesting alternatives for invalid product"""
        result = suggest_alternatives("INVALID-ID")
        
        assert 'error' in result
        assert result['count'] == 0
    
    def test_get_best_value_product_with_budget(self):
        """Budget parameter is deprecated but function remains deterministic"""
        result = get_best_value_product(max_budget=300)
        assert result['found'] is True
        assert 'recommended' in result
        assert result['budget'] is None
    
    def test_get_best_value_product_no_budget(self):
        """Test getting best value without budget constraint"""
        result = get_best_value_product()
        
        assert result['found'] is True
        assert 'recommended' in result


class TestCacheIntegration:
    """Test cache functionality"""
    
    def test_cache_product_lookup(self):
        """Test that product lookups are cached"""
        from product_agent.utils.cache import get_cache_stats, clear_cache
        
        # Clear cache first
        clear_cache()
        
        # First lookup - should miss cache
        first = get_product_by_id("FIB-5G")
        stats1 = get_cache_stats()
        
        # Second lookup - should hit cache
        second = get_product_by_id("FIB-5G")
        stats2 = get_cache_stats()
        
        # Product result should be stable across repeated calls.
        assert first["product_id"] == second["product_id"]
        assert stats2['hits'] >= stats1['hits']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
