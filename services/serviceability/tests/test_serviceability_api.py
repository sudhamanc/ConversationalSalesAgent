"""REST API scenarios from ``specs/serviceability-service/spec.md``."""

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.pg, pytest.mark.usefixtures("migrated_db")]

PHILLY = {"street": "123 Main St", "city": "Philadelphia", "state": "PA", "zip_code": "19103"}


@pytest.fixture(scope="module")
def client():
    from serviceability_service.app import create_app

    with TestClient(create_app()) as c:
        yield c


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_serviceable_address(client):
    response = client.post("/api/v1/serviceability/check", json=PHILLY)
    assert response.status_code == 200
    body = response.json()
    assert body["serviceable"] is True
    assert body["infrastructure_type"] == "FTTP"
    assert body["max_speed_mbps"] == 5000
    assert body["service_zone"] == "Metro-Center-PA"
    assert body["estimated_install_days"] == 5
    assert body["available_products"] and all(isinstance(s, str) for s in body["available_products"])
    assert "FIB-1G" in body["available_products"]
    assert body["infrastructure"]["network_element"]["switch_id"] == "PHI-SW-002"
    assert body["address"] == PHILLY
    assert "reason" not in body


def test_unserviceable_address(client):
    response = client.post(
        "/api/v1/serviceability/check",
        json={"street": "1 Nowhere Rd", "city": "Remote", "state": "AK", "zip_code": "99999"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["serviceable"] is False
    assert body["available_products"] == []
    assert body["reason"]


def test_previously_sparse_zip_has_infrastructure(client):
    body = client.post(
        "/api/v1/serviceability/check", json={**PHILLY, "city": "Seattle", "state": "WA", "zip_code": "98101"}
    ).json()
    assert body["serviceable"] is True
    assert body["infrastructure"]["speed_capability"]["max_speed_mbps"] == 5000
    assert body["infrastructure"]["type"] == "Fiber"


def test_po_box_rejected(client):
    response = client.post(
        "/api/v1/addresses/validate", json={"address": "PO Box 12, Philadelphia, PA 19103"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert "PO Boxes are not supported" in body["error"]


def test_validate_valid_address(client):
    body = client.post(
        "/api/v1/addresses/validate", json={"address": "123 Main St, Philadelphia, PA 19103"}
    ).json()
    assert body == {"valid": True, "address": PHILLY}


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/v1/serviceability/check", {**PHILLY, "state": "ZZ"}),
        ("/api/v1/serviceability/check", {**PHILLY, "zip_code": "1910"}),
        ("/api/v1/serviceability/check", {"street": "123 Main St"}),
        ("/api/v1/addresses/normalize", {**PHILLY, "state": "Pennsylvania"}),
        ("/api/v1/addresses/validate", {"address": "   "}),
        ("/api/v1/addresses/validate", {}),
    ],
)
def test_invalid_input_is_422(client, path, payload):
    response = client.post(path, json=payload)
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()


def test_normalize(client):
    body = client.post(
        "/api/v1/addresses/normalize",
        json={"street": "123 market st", "city": "philadelphia", "state": "pa", "zip_code": "19107"},
    ).json()
    assert body == {"normalized_address": "123 Market St, Philadelphia, PA 19107"}


def test_infrastructure(client):
    body = client.get("/api/v1/infrastructure/fiber").json()
    assert body["technology"] == "FTTP"
    assert body["infrastructure"][0]["max_speed_mbps"] == 10000
    assert client.get("/api/v1/infrastructure/satellite").json()["infrastructure"] == []


def test_coverage_zones(client):
    body = client.get("/api/v1/coverage-zones").json()
    assert "Metro-East-PA" in body["zones"]
    assert body["count"] == len(body["zones"])
