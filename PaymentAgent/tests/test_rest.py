"""POST /payment-methods: model-free tokenization behind the secure payment form."""

import os

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from payment_agent import rest

CARD = {"payment_type": "credit_card", "card_number": "4111 1111 1111 1111",
        "expiry_month": "12", "expiry_year": "2030", "cvv": "123"}


@pytest.fixture
def client():
    return TestClient(Starlette(routes=rest.ROUTES))


@pytest.mark.parametrize("body,error", [
    ({**CARD}, "customer_id is required"),
    ({**CARD, "customer_id": "C1", "payment_type": "bitcoin"}, "payment_type must be credit_card or ach"),
    ({**CARD, "customer_id": "C1", "card_number": "4111111111111112"}, "Invalid card number (failed Luhn check)"),
    ({**CARD, "customer_id": "C1", "expiry_month": "13"}, "Invalid expiry date values"),
    ({"customer_id": "C1", "payment_type": "ach", "routing_number": "021000021",
      "account_number": "123456789", "account_type": "brokerage"}, "account_type must be checking or savings"),
])
def test_invalid_requests_are_rejected(client, body, error):
    r = client.post("/payment-methods", json=body)
    assert r.status_code == 400
    assert r.json()["error"] == error
    assert "4111" not in r.text


def test_response_is_masked_and_has_no_token(client, monkeypatch):
    seen = {}

    def fake_tokenize(**kwargs):
        seen.update(kwargs)
        return {"success": True, "saved": True, "method_id": "PM-1", "token": "tok_secret",
                "card_brand": "visa", "last_four": "1111", "expiry": "12/2030"}

    monkeypatch.setattr(rest, "tokenize_payment_method", fake_tokenize)
    r = client.post("/payment-methods", json={**CARD, "customer_id": "CUST-1"})
    assert r.status_code == 200
    assert r.json() == {"success": True, "saved": True, "method_id": "PM-1", "payment_type": "credit_card",
                        "card_brand": "visa", "last_four": "1111", "expiry": "12/2030"}
    assert "tok_" not in r.text
    assert seen["customer_id"] == "CUST-1" and seen["card_number"] == "4111 1111 1111 1111"


def test_unsaved_method_is_an_error(client, monkeypatch):
    monkeypatch.setattr(rest, "tokenize_payment_method",
                        lambda **_: {"success": True, "saved": False, "token": "tok_x", "last_four": "1111"})
    r = client.post("/payment-methods", json={**CARD, "customer_id": "CUST-1"})
    assert r.status_code == 502 and "tok_" not in r.text


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")
def test_card_is_saved_to_the_account(client, migrated_db):
    from payment_agent.tools.payment_tools import get_payment_methods

    r = client.post("/payment-methods", json={**CARD, "customer_id": "CUST-REST-1"})
    assert r.status_code == 200 and r.json()["last_four"] == "1111"
    methods = get_payment_methods("CUST-REST-1")["payment_methods"]
    assert any(m["last_four"] == "1111" and m["token"].startswith("tok_") for m in methods)
