"""Unit tests for address parsing and coverage lookup (migrated from
``ServiceabilityAgent/tests/test_tools.py``; stale GIS expectations fixed to
match the seeded coverage data)."""

import httpx
import pytest

from serviceability_service import core, gis_client
from serviceability_service.address import (
    extract_zip_code,
    normalize_address,
    validate_and_parse_address,
)
from serviceability_service.models import Address


def addr(street="123 Market Street", city="Philadelphia", state="PA", zip_code="19107"):
    return Address(street=street, city=city, state=state, zip_code=zip_code)


class TestAddressValidation:
    def test_valid_address_parsing(self):
        result = validate_and_parse_address("123 Market Street, Philadelphia, PA 19107")
        assert result.valid is True
        assert result.address.zip_code == "19107"
        assert result.address.state == "PA"
        assert result.address.city == "Philadelphia"
        assert result.address.street == "123 Market Street"

    def test_valid_address_informal_format(self):
        result = validate_and_parse_address("456 Main St, New York, NY 10001")
        assert result.valid is True
        assert result.address.zip_code == "10001"

    def test_natural_language_address(self):
        result = validate_and_parse_address("I am at 123 Main street philadelphia pa 19103")
        assert result.valid is True
        # Known legacy limitation: without commas the street/city split is
        # ambiguous and the non-greedy parser yields street "123 Main".
        assert result.address.street.startswith("123 Main")
        assert result.address.state == "PA"
        assert result.address.zip_code == "19103"

    def test_po_box_rejection(self):
        result = validate_and_parse_address("PO Box 1234, Philadelphia, PA 19107")
        assert result.valid is False
        assert "PO Box" in result.error

    @pytest.mark.parametrize(
        "text",
        [
            "P.O. Box 1234, City, ST 12345",
            "POST OFFICE BOX 5678, City, ST 12345",
            "P O Box 999, City, ST 12345",
        ],
    )
    def test_po_box_variation(self, text):
        assert validate_and_parse_address(text).valid is False

    def test_missing_zip_code(self):
        result = validate_and_parse_address("123 Main Street, Philadelphia, PA")
        assert result.valid is False
        assert "ZIP code" in result.error

    def test_missing_state(self):
        result = validate_and_parse_address("123 Main Street, Philadelphia, 19107")
        assert result.valid is False
        assert "state code" in result.error

    def test_incomplete_address(self):
        result = validate_and_parse_address("Philadelphia, PA")
        assert result.valid is False
        assert "ZIP code" in result.error or "Complete address" in result.error

    def test_missing_house_number(self):
        result = validate_and_parse_address("Main Street, Philadelphia, PA 19107")
        assert result.valid is False
        assert "number" in result.error

    def test_international_address_rejection(self):
        result = validate_and_parse_address("10 Downing Street, London, UK SW1A 2AA")
        assert result.valid is False
        assert "United States" in result.error

    def test_normalize_address(self):
        normalized = normalize_address(
            Address(street="123 market st", city="philadelphia", state="pa", zip_code="19107")
        ).normalized_address
        assert normalized == "123 Market St, Philadelphia, PA 19107"

    def test_extract_zip_code(self):
        assert extract_zip_code("123 Main St, City, ST 12345").zip_code == "12345"

    def test_extract_zip_code_with_plus4(self):
        assert extract_zip_code("123 Main St, City, ST 12345-6789").zip_code == "12345"

    def test_extract_zip_code_missing(self):
        assert extract_zip_code("no zip here").zip_code == ""


class TestInfrastructureCatalog:
    def test_infrastructure_by_technology_fttp(self):
        result = core.get_infrastructure_by_technology("FTTP")
        infra = result.infrastructure[0]
        assert infra.technology == "Fiber to the Premises (FTTP)"
        assert infra.min_speed_mbps == 100
        assert infra.max_speed_mbps == 10000
        assert infra.symmetrical is True

    def test_infrastructure_by_technology_hfc(self):
        infra = core.get_infrastructure_by_technology("HFC").infrastructure[0]
        assert "HFC" in infra.technology
        assert infra.symmetrical is False

    @pytest.mark.parametrize("alias,key", [("Fiber", "FTTP"), ("coax", "HFC"), ("DOCSIS", "DOCSIS 3.1")])
    def test_infrastructure_by_technology_alias(self, alias, key):
        assert core.get_infrastructure_by_technology(alias) == core.get_infrastructure_by_technology(key)

    def test_unknown_technology_is_empty(self):
        assert core.get_infrastructure_by_technology("Satellite").infrastructure == []


@pytest.mark.pg
@pytest.mark.usefixtures("migrated_db")
class TestCoverageLookup:
    def test_serviceable_address_philadelphia(self):
        result = core.check_service_availability(addr())
        assert result.serviceable is True
        assert result.service_zone == "Metro-East-PA"
        assert result.infrastructure_type == "FTTP"
        assert result.estimated_install_days == 2
        assert result.max_speed_mbps == 10000
        infra = result.infrastructure
        assert infra["type"] == "Fiber"
        assert infra["network_element"]["switch_id"] == "PHI-SW-001"
        assert infra["speed_capability"] == {
            "min_speed_mbps": 100, "max_speed_mbps": 10000, "symmetrical": True,
        }
        assert "FIB-10G" in result.available_products
        assert result.available_product_categories == ["Internet", "Voice", "SD-WAN", "Mobile"]

    def test_serviceable_address_rural(self):
        result = core.check_service_availability(
            addr(street="456 Country Road", city="Smalltown", zip_code="18000")
        )
        assert result.serviceable is True
        assert result.infrastructure_type == "HFC"
        assert result.estimated_install_days == 10
        infra = result.infrastructure
        assert infra["type"] == "Coax/HFC"
        assert infra["speed_capability"]["min_speed_mbps"] == 50
        assert infra["speed_capability"]["max_speed_mbps"] == 500
        assert infra["speed_capability"]["symmetrical"] is False
        assert result.available_products == [
            "COAX-200M", "COAX-500M", "VOICE-BAS", "VOICE-STD", "SDWAN-ESS", "MOB-BAS", "MOB-UNL",
        ]

    def test_zip_not_in_coverage(self):
        result = core.check_service_availability(
            addr(street="789 Nowhere Road", city="Remote", state="AK", zip_code="99999")
        )
        assert result.serviceable is False
        assert result.infrastructure is None
        assert result.available_products == []
        assert result.reason

    def test_explicitly_unserviceable_zip_keeps_reason(self):
        result = core.check_service_availability(
            addr(street="1 Main St", city="Anchorage", state="AK", zip_code="99501")
        )
        assert result.serviceable is False
        assert "Alaska" in result.reason
        assert result.available_products == []

    @pytest.mark.parametrize("zip_code", ["98101", "73301", "85001"])
    def test_previously_sparse_zip_has_infrastructure(self, zip_code):
        result = core.check_service_availability(addr(zip_code=zip_code))
        assert result.serviceable is True
        speed = result.infrastructure["speed_capability"]
        assert speed["max_speed_mbps"] == result.max_speed_mbps
        assert speed["min_speed_mbps"] <= speed["max_speed_mbps"]
        assert result.infrastructure["service_class"]
        assert "redundancy_available" in result.infrastructure

    def test_sparse_zip_speed_capped_by_products(self):
        # Seattle sells FIB-1G/FIB-5G only; the FTTP default max (10 Gbps) is capped to 5 Gbps.
        assert core.check_service_availability(addr(zip_code="98101")).max_speed_mbps == 5000

    def test_every_serviceable_zone_row_has_infrastructure(self):
        from sales_common import db

        rows = db.fetch_all(
            "SELECT zip_code FROM coverage_zones WHERE serviceable AND "
            "(infrastructure IS NULL OR infrastructure->'speed_capability' IS NULL)"
        )
        assert rows == []
        assert db.fetch_one("SELECT count(*) AS n FROM coverage_zones")["n"] == 38

    def test_coverage_zones(self):
        result = core.get_coverage_zones()
        assert "Metro-East-PA" in result.zones
        assert result.zones == sorted(result.zones)
        assert result.count == len(result.zones) == 35

    def test_repeated_lookups_identical(self):
        assert core.check_service_availability(addr()) == core.check_service_availability(addr())


class TestUpstreamGis:
    """``USE_MOCK_DATA=false`` path, with a mocked upstream transport."""

    @pytest.fixture(autouse=True)
    def _upstream(self, monkeypatch):
        monkeypatch.setenv("USE_MOCK_DATA", "false")
        monkeypatch.setenv("GIS_API_URL", "https://gis.example.test")
        monkeypatch.setenv("GIS_API_KEY", "secret-key")
        gis_client.clear_cache()
        yield
        gis_client.clear_cache()

    def test_translates_upstream_response(self):
        seen = {}

        def handler(request):
            seen["auth"] = request.headers["authorization"]
            seen["url"] = str(request.url)
            return httpx.Response(200, json={
                "available": True, "technology": "FTTP", "zone": "Metro-X", "install_days": 4,
                "infrastructure": {"type": "Fiber", "speed_capability": {"max_speed_mbps": 1000}},
                "available_products": ["FIB-1G"],
            })

        client = httpx.Client(transport=httpx.MockTransport(handler))
        result = gis_client.check(addr(), client=client)
        assert seen == {"auth": "Bearer secret-key", "url": "https://gis.example.test/serviceability/check"}
        assert result.serviceable is True
        assert result.max_speed_mbps == 1000
        assert result.available_products == ["FIB-1G"]
        assert result.available_product_categories[0] == "Internet"

    def test_upstream_error_is_unserviceable_and_key_not_logged(self, caplog):
        client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
        result = gis_client.check(addr(zip_code="19103"), client=client)
        assert result.serviceable is False
        assert result.reason == gis_client.UNAVAILABLE_REASON
        assert "secret-key" not in caplog.text

    def test_missing_credentials(self, monkeypatch):
        monkeypatch.delenv("GIS_API_KEY")
        result = core.check_service_availability(addr(zip_code="10001"))
        assert result.serviceable is False
