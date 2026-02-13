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
    get_infrastructure_by_technology,
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
        assert "infrastructure" in result
        assert result["infrastructure"] is not None
        assert result["service_zone"] == "Metro-East-PA"
        assert result["infrastructure_type"] == "FTTP"
        assert result["estimated_install_days"] == 5
        
        # Check infrastructure details
        infra = result["infrastructure"]
        assert infra["type"] == "Fiber"
        assert "network_element" in infra
        assert "speed_capability" in infra
        assert infra["speed_capability"]["min_speed_mbps"] == 100
        assert infra["speed_capability"]["max_speed_mbps"] == 10000
        assert infra["speed_capability"]["symmetrical"] is True
    
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
        
        # Check infrastructure details for HFC
        infra = result["infrastructure"]
        assert infra["type"] == "Coax/HFC"
        assert infra["speed_capability"]["min_speed_mbps"] == 50
        assert infra["speed_capability"]["max_speed_mbps"] == 500
        assert infra["speed_capability"]["symmetrical"] is False
    
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
        assert result.get("infrastructure") is None
        assert "reason" in result
        assert result["reason"] is not None
    
    def test_infrastructure_by_technology_fttp(self):
        """Test infrastructure lookup by technology - FTTP"""
        infrastructure_list = get_infrastructure_by_technology("FTTP")
        
        assert len(infrastructure_list) > 0
        infra = infrastructure_list[0]
        assert infra["technology"] == "Fiber to the Premises (FTTP)"
        assert infra["min_speed_mbps"] == 100
        assert infra["max_speed_mbps"] == 10000
        assert infra["symmetrical"] is True
    
    def test_infrastructure_by_technology_hfc(self):
        """Test infrastructure lookup by technology - HFC"""
        infrastructure_list = get_infrastructure_by_technology("HFC")
        
        assert len(infrastructure_list) > 0
        infra = infrastructure_list[0]
        assert "HFC" in infra["technology"]
        assert infra["symmetrical"] is False
    
    def test_infrastructure_by_technology_alias(self):
        """Test infrastructure lookup with technology alias"""
        fiber_infra = get_infrastructure_by_technology("Fiber")
        fttp_infra = get_infrastructure_by_technology("FTTP")
        
        # Should return same infrastructure
        assert len(fiber_infra) == len(fttp_infra)
        if len(fiber_infra) > 0:
            assert fiber_infra[0]["min_speed_mbps"] == fttp_infra[0]["min_speed_mbps"]
    
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
        """Test that infrastructure has required fields"""
        address = {
            "street": "123 Market Street",
            "city": "Philadelphia",
            "state": "PA",
            "zip_code": "19107"
        }
        result = check_service_availability(address)
        
        # Check infrastructure structure instead of products
        assert "infrastructure" in result
        infrastructure = result["infrastructure"]
        assert "type" in infrastructure  # Infrastructure type (Fiber, Coax, etc.)
        assert "network_element" in infrastructure  # Singular, not plural
        assert "speed_capability" in infrastructure
        assert "service_class" in infrastructure
        assert "redundancy_available" in infrastructure
        
        # Check network element structure
        network_element = infrastructure["network_element"]
        assert isinstance(network_element, dict)
        # At least one identifier should be present
        identifiers = ["switch_id", "cabinet_id", "node_id", "cmts_id"]
        assert any(key in network_element for key in identifiers)
    
    def test_multiple_speed_tiers(self):
        """Test that fiber locations have speed capability details"""
        address = {
            "street": "123 Market Street",
            "city": "Philadelphia",
            "state": "PA",
            "zip_code": "19107"
        }
        result = check_service_availability(address)
        
        # Philadelphia downtown should have infrastructure with speed capabilities
        assert "infrastructure" in result
        infrastructure = result["infrastructure"]
        assert "speed_capability" in infrastructure
        speed_cap = infrastructure["speed_capability"]
        assert "min_speed_mbps" in speed_cap
        assert "max_speed_mbps" in speed_cap
        assert speed_cap["max_speed_mbps"] >= speed_cap["min_speed_mbps"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
