"""REST API tests (FastAPI TestClient) including the spec scenarios."""

import pytest
from fastapi.testclient import TestClient

from catalog_service.app import create_app

pytestmark = pytest.mark.usefixtures("seeded_db")


@pytest.fixture(scope="module")
def client(seeded_db):
    with TestClient(create_app(rag_warmup=False)) as c:
        yield c


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_seeded_catalog_has_16_products(client):
    body = client.get("/api/v1/products").json()
    ids = {p["product_id"] for p in body["products"]}
    assert body["count"] == 16 == len(ids)
    assert {"FIB-5G", "SDWAN-PRO"} <= ids


def test_list_by_category(client):
    body = client.get("/api/v1/products", params={"category": "fiber"}).json()
    assert body["category"] == "Fiber Internet" and body["count"] == 3


def test_case_insensitive_lookup(client):
    resp = client.get("/api/v1/products/fib-5g")
    assert resp.status_code == 200
    body = resp.json()
    assert body["product_id"] == "FIB-5G" and body["found"] is True
    assert "unit_price" not in body and "price" not in body


def test_unknown_product_404(client):
    resp = client.get("/api/v1/products/NOPE-9")
    assert resp.status_code == 404
    assert resp.json()["error"] == "not_found"


def test_search(client):
    resp = client.get("/api/v1/products/search", params={"speed": ">= 5 Gbps"})
    assert resp.status_code == 200
    assert [p["product_id"] for p in resp.json()["products"]] == ["FIB-5G", "FIB-10G"]


def test_search_invalid_speed_422(client):
    resp = client.get("/api/v1/products/search", params={"speed": "really fast"})
    assert resp.status_code == 422
    assert resp.json()["error"] == "invalid_input"


def test_categories(client):
    body = client.get("/api/v1/categories").json()
    assert body["count"] == 5 and "SD-WAN" in body["categories"]


def test_compare_fastest(client):
    resp = client.post("/api/v1/products/compare", json={"product_ids": ["FIB-1G", "FIB-5G", "FIB-10G"]})
    assert resp.status_code == 200
    assert resp.json()["fastest_product_id"] == "FIB-10G"


def test_compare_six_ids_422(client):
    ids = ["FIB-1G", "FIB-5G", "FIB-10G", "COAX-200M", "COAX-500M", "COAX-1G"]
    resp = client.post("/api/v1/products/compare", json={"product_ids": ids})
    assert resp.status_code == 422
    assert resp.json()["error"] == "invalid_input"


def test_compare_one_id_422(client):
    assert client.post("/api/v1/products/compare", json={"product_ids": ["FIB-1G"]}).status_code == 422


def test_compare_missing_body_422(client):
    assert client.post("/api/v1/products/compare", json={}).status_code == 422


def test_compare_all_unknown_404(client):
    resp = client.post("/api/v1/products/compare", json={"product_ids": ["A-1", "B-2"]})
    assert resp.status_code == 404


def test_alternatives(client):
    resp = client.get("/api/v1/products/fib-1g/alternatives", params={"criteria": "faster"})
    assert resp.status_code == 200
    assert [a["product_id"] for a in resp.json()["alternatives"]] == ["FIB-5G", "FIB-10G"]


def test_alternatives_invalid_criteria_422(client):
    resp = client.get("/api/v1/products/FIB-1G/alternatives", params={"criteria": "cheaper"})
    assert resp.status_code == 422


def test_alternatives_unknown_404(client):
    assert client.get("/api/v1/products/NOPE/alternatives").status_code == 404


def test_best_value(client):
    body = client.get("/api/v1/products/best-value").json()
    assert body["found"] is True and body["recommended"]["product_id"] == "FIB-10G"
    body = client.get("/api/v1/products/best-value", params={"category": "coax"}).json()
    assert body["recommended"]["product_id"] == "COAX-1G"
    assert "unit_price" not in body["recommended"]


def test_best_value_has_no_budget_parameter(client):
    # max_budget was removed (pricing is not disclosed by the catalog); unknown
    # query parameters are ignored, so old callers still get the category result.
    params = client.app.openapi()["paths"]["/api/v1/products/best-value"]["get"]["parameters"]
    assert [p["name"] for p in params] == ["category"]
    resp = client.get("/api/v1/products/best-value", params={"category": "coax", "max_budget": -1})
    assert resp.status_code == 200 and resp.json()["recommended"]["product_id"] == "COAX-1G"


def test_knowledge_validation_422(client):
    assert client.get("/api/v1/knowledge/search").status_code == 422
    assert client.get("/api/v1/knowledge/search", params={"q": "sla", "top_k": 11}).status_code == 422
    assert client.get("/api/v1/knowledge/search", params={"q": "sla", "top_k": 0}).status_code == 422


def test_knowledge_unavailable_is_explicit(client, no_rag):
    resp = client.get("/api/v1/knowledge/search", params={"q": "fiber SLA uptime"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False and body["passages"] == []


def test_no_price_fields_anywhere(client):
    for path in ["/api/v1/products", "/api/v1/products/search?technology=FTTP", "/api/v1/products/SDWAN-PRO"]:
        text = client.get(path).text
        assert "unit_price" not in text and '"price"' not in text and "family" not in text


def test_mcp_accepts_non_localhost_host_header(client):
    """host="0.0.0.0" on the MCP app: Cloud Run Host headers must not get HTTP 421."""
    headers = {
        "Host": "catalog-abc-uc.a.run.app",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "mcp-protocol-version": "2025-06-18",
    }
    resp = client.post(
        "/mcp/",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert resp.status_code == 200, resp.text
    names = {t["name"] for t in resp.json()["result"]["tools"]}
    assert len(names) == 9 and {"search_product_knowledge", "search_faq"} <= set(names)
