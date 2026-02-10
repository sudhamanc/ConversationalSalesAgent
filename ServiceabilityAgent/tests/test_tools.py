"""
Unit tests for Serviceability Agent tools.
"""

import pytest
from serviceability_agent.tools.address_tools import (
    validate_and_parse_address,
    normalize_address,
    extract_zip_code,
)
from serviceability_agent.tools.gis_tools import (
    check_service_availability,
    get_products_by_technology,
    get_coverage_zones,
)


class TestAddressValidation:
    """Test address validation tools"""
    
    def test_valid_address_parsing(self):
        """Test successful address parsing"""
        result = validate_and_parse_address(
            "123 Market Street, Philadelphia, PA 19107"
        )
        assert result["valid"] is True
        assert result["address"]["zip_code"] == "19107"
        assert result["address"]["state"] == "PA"
        assert result["address"]["city"] == "Philadelphia"
        assert result["address"]["street"] == "123 Market Street"
    
    def test_valid_address_informal_format(self):
        """Test address with informal formatting"""
        result = validate_and_parse_address(
            "456 Main St, New York, NY 10001"
        )
        assert result["valid"] is True
        assert result["address"]["zip_code"] == "10001"
    
    def test_po_box_rejection(self):
        """Test PO Box addresses are rejected"""
        result = validate_and_parse_address(
            "PO Box 1234, Philadelphia, PA 19107"
        )
        assert result["valid"] is False
        assert "PO Box" in result["error"]
    
    def test_po_box_variation(self):
        """Test various PO Box formats are rejected"""
        variations = [
            "P.O. Box 1234, City, ST 12345",
            "POST OFFICE BOX 5678, City, ST 12345",
            "P O Box 999, City, ST 12345",
        ]
        for addr in variations:
            result = validate_and_parse_address(addr)
            assert result["valid"] is False
    
    def test_missing_zip_code(self):
        """Test address without ZIP code"""
        result = validate_and_parse_address(
            "123 Main Street, Philadelphia, PA"
        )
        assert result["valid"] is False
        assert "ZIP code" in result["error"]
    
    def test_missing_state(self):
        """Test address without state code"""
        result = validate_and_parse_address(
            "123 Main Street, Philadelphia, 19107"
        )
        assert result["valid"] is False
        assert "state code" in result["error"]
    
    def test_incomplete_address(self):
        """Test incomplete address format"""
        result = validate_and_parse_address("Philadelphia, PA")
        assert result["valid"] is False
        assert "ZIP code" in result["error"] or "Complete address" in result["error"]
    
    def test_missing_house_number(self):
        """Test street address without house number"""
        result = validate_and_parse_address(
            "Main Street, Philadelphia, PA 19107"
        )
        assert result["valid"] is False
        assert "number" in result["error"]
    
    def test_international_address_rejection(self):
        """Test international addresses are rejected"""
        result = validate_and_parse_address(
            "10 Downing Street, London, UK SW1A 2AA"
        )
        assert result["valid"] is False
        assert "United States" in result["error"]
    
    def test_normalize_address(self):
        """Test address normalization"""
        address = {
            "street": "123 market st",
            "city": "philadelphia",
            "state": "pa",
            "zip_code": "19107"
        }
        normalized = normalize_address(address)
        assert "123 Market St" in normalized
        assert "Philadelphia" in normalized
        assert "PA" in normalized
        assert "19107" in normalized
    
    def test_extract_zip_code(self):
        """Test ZIP code extraction"""
        zip_code = extract_zip_code("123 Main St, City, ST 12345")
        assert zip_code == "12345"
    
    def test_extract_zip_code_with_plus4(self):
        """Test ZIP+4 extraction returns only 5 digits"""
        zip_code = extract_zip_code("123 Main St, City, ST 12345-6789")
        assert zip_code == "12345"


class TestGISTools:
    """Test GIS integration tools"""
    
    def test_serviceable_address_philadelphia(self):
        """Test serviceable address lookup in Philadelphia"""
        address = {
            "street": "123 Market Street",
            "city": "Philadelphia",
            "state": "PA",
            "zip_code": "19107"
        }
        result = check_service_availability(address)
        
        assert result["serviceable"] is True
        assert len(result["available_products"]) > 0
        assert result["service_zone"] == "Metro-East-PA"
        assert result["infrastructure_type"] == "FTTP"
        assert result["estimated_install_days"] == 5
    
    def test_serviceable_address_rural(self):
        """Test serviceable address in rural area"""
        address = {
            "street": "456 Country Road",
            "city": "Smalltown",
            "state": "PA",
            "zip_code": "18000"
        }
        result = check_service_availability(address)
        
        assert result["serviceable"] is True
        assert result["infrastructure_type"] == "HFC"
        # Rural areas should have coax products
        product_names = [p["product_name"] for p in result["available_products"]]
        assert any("Coax" in name for name in product_names)
    
    def test_non_serviceable_address(self):
        """Test non-serviceable address"""
        address = {
            "street": "789 Nowhere Road",
            "city": "Remote",
            "state": "AK",
            "zip_code": "99999"
        }
        result = check_service_availability(address)
        
        assert result["serviceable"] is False
        assert len(result["available_products"]) == 0
        assert "reason" in result
        assert result["reason"] is not None
    
    def test_products_by_technology_fttp(self):
        """Test product lookup by technology - FTTP"""
        products = get_products_by_technology("FTTP")
        
        assert len(products) > 0
        assert all(p["speed"] in ["1 Gbps", "5 Gbps", "10 Gbps"] for p in products)
    
    def test_products_by_technology_hfc(self):
        """Test product lookup by technology - HFC"""
        products = get_products_by_technology("HFC")
        
        assert len(products) > 0
        assert all("Coax" in p["name"] for p in products)
    
    def test_products_by_technology_alias(self):
        """Test product lookup with technology alias"""
        fiber_products = get_products_by_technology("Fiber")
        fttp_products = get_products_by_technology("FTTP")
        
        # Should return same products
        assert len(fiber_products) == len(fttp_products)
    
    def test_coverage_zones(self):
        """Test coverage zone retrieval"""
        zones = get_coverage_zones()
        
        assert len(zones) > 0
        assert "Metro-East-PA" in zones
        assert isinstance(zones, list)
    
    def test_caching_behavior(self):
        """Test that repeated lookups use cache"""
        address = {
            "street": "123 Market Street",
            "city": "Philadelphia",
            "state": "PA",
            "zip_code": "19107"
        }
        
        # First call
        result1 = check_service_availability(address)
        
        # Second call should be cached
        result2 = check_service_availability(address)
        
        # Results should be identical
        assert result1 == result2


class TestProductData:
    """Test product data structure and consistency"""
    
    def test_product_structure(self):
        """Test that products have required fields"""
        address = {
            "street": "123 Market Street",
            "city": "Philadelphia",
            "state": "PA",
            "zip_code": "19107"
        }
        result = check_service_availability(address)
        
        for product in result["available_products"]:
            assert "product_id" in product
            assert "product_name" in product
            assert "technology" in product
            assert "speeds" in product
            assert "available" in product
    
    def test_multiple_speed_tiers(self):
        """Test that fiber locations have multiple speed tiers"""
        address = {
            "street": "123 Market Street",
            "city": "Philadelphia",
            "state": "PA",
            "zip_code": "19107"
        }
        result = check_service_availability(address)
        
        # Philadelphia downtown should have multiple fiber tiers
        assert len(result["available_products"]) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
