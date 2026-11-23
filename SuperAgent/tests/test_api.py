"""HTTP-level test: session creation + SSE chat against PostgreSQL (revocation table)."""

import json

import pytest
from fastapi.testclient import TestClient
from google.adk.sessions import InMemorySessionService

pytestmark = pytest.mark.pg


@pytest.fixture
def client():
    from sales_common import db, migrate

    db.close_pool()
    migrate.run(seed=False)
    import runtime
    from fakes import build_fake_agents, router
    from super_agent.agent import build_gateway_app

    runtime.init_runtime(
        app=build_gateway_app(agents=build_fake_agents(), router_model=router("discovery_agent")),
        session_service=InMemorySessionService(),
        memory_service=None,
    )
    runtime.get_runner().memory_service = None
    import main

    with TestClient(main.app) as c:
        yield c
    runtime._runner = None
    db.close_pool()


def _events(resp):
    return [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]


def test_session_and_chat_stream(client):
    s = client.post("/api/session", json={"client_id": "0b7c9a4e-8f1d-4c2a-9d3e-2f6a7b8c9d0e"}).json()
    r = client.post("/api/chat", json={"message": "We're Crane.io at 123 Main St, Philadelphia PA 19103"},
                    headers={"Authorization": f"Bearer {s['token']}"})
    assert r.status_code == 200
    events = _events(r)
    authors = [e["author"] for e in events if e["type"] == "token" and e["content"].strip()]
    assert authors[0] == "discovery_agent" and "serviceability_agent" in authors
    assert any(e["type"] == "activity_update" and e["category"] == "customer" for e in events)
    assert events[-1] == {"type": "done"}


def test_revoked_token_rejected(client):
    s = client.post("/api/session").json()
    h = {"Authorization": f"Bearer {s['token']}"}
    assert client.delete("/api/session", headers=h).json() == {"status": "revoked"}
    r = client.post("/api/chat", json={"message": "hi"}, headers=h)
    assert r.status_code == 401


def test_bad_token_and_empty_message(client):
    assert client.post("/api/chat", json={"message": "hi"}, headers={"Authorization": "Bearer nope"}).status_code == 401
    s = client.post("/api/session").json()
    r = client.post("/api/chat", json={"message": "  "}, headers={"Authorization": f"Bearer {s['token']}"})
    assert r.status_code == 400


def test_client_log_requires_token_and_strips_newlines(client, tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    body = {"level": "error", "message": "boom\n[BROWSER ERROR] forged\r\x1b[31mline"}
    assert client.post("/api/client-log", json=body).status_code == 401
    assert client.post("/api/client-log", json=body, headers={"Authorization": "Bearer nope"}).status_code == 401
    assert not (tmp_path / "frontend.log").exists()

    s = client.post("/api/session").json()
    r = client.post("/api/client-log", json=body, headers={"Authorization": f"Bearer {s['token']}"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    lines = (tmp_path / "frontend.log").read_text().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("[BROWSER ERROR]") and "boom [BROWSER ERROR] forged  [31mline" in lines[0]
    assert "\x1b" not in lines[0] and "\r" not in lines[0]


def test_client_log_caps_message_and_rate_limits(client, tmp_path, monkeypatch):
    from api import client_log

    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setattr(client_log, "client_log_limiter", client_log.RateLimiter(rpm=60, rph=100, burst=1))
    s = client.post("/api/session").json()
    h = {"Authorization": f"Bearer {s['token']}"}
    assert client.post("/api/client-log", json={"message": "x" * 5000}, headers=h).status_code == 200
    assert client.post("/api/client-log", json={"message": "again"}, headers=h).status_code == 429
    line = (tmp_path / "frontend.log").read_text().splitlines()[0]
    assert line.endswith("x" * 4000) and "x" * 4001 not in line


def test_client_log_default_path_is_repo_logs(monkeypatch):
    import pathlib

    from api import client_log

    monkeypatch.delenv("LOG_DIR", raising=False)
    repo = pathlib.Path(__file__).resolve().parents[2]
    assert client_log.log_path() == repo / "logs" / "frontend.log"


def test_run_scenarios_client_against_app(client):
    """run_scenarios.py speaks the current API: JSON session body, Bearer token, SSE parse."""
    import asyncio

    import httpx

    import main
    import run_scenarios

    assert run_scenarios.parse_sse_line('data: {"type": "done"}') == {"type": "done"}
    assert run_scenarios.parse_sse_line(": keepalive") is None

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://gw") as c:
            s = await run_scenarios.get_session(c)
            assert s and s["token"]
            return await run_scenarios.run_chat(c, s["token"], "We're Crane.io at 123 Main St, Philadelphia PA 19103")

    events = asyncio.run(go())
    assert any(e["type"] == "token" for e in events) and events[-1] == {"type": "done"}


# --- guided checkout (spec: guided-checkout) ---------------------------------


def _auth(client):
    s = client.post("/api/session").json()
    return {"Authorization": f"Bearer {s['token']}"}


def test_card_numbers_are_masked_before_the_workflow(client, monkeypatch):
    import api.chat as chat

    seen = {}

    async def fake_stream(session, user_message):
        seen["message"] = user_message
        yield 'data: {"type": "done"}\n\n'

    monkeypatch.setattr(chat, "stream_turn", fake_stream)
    r = client.post("/api/chat", json={"message": "my card is 4111 1111 1111 1111 cvv 123"}, headers=_auth(client))
    assert r.status_code == 200
    assert "4111" not in seen["message"]
    assert "[REDACTED_CARD]" in seen["message"] and "[REDACTED_CVV]" in seen["message"]


def test_payment_method_proxy(client, monkeypatch):
    import httpx

    import api.payment_methods as pm

    forwarded = {}

    async def fake_customer(user_id, session_id):
        return "CUST-9"

    async def fake_post(self, url, json=None, headers=None):
        forwarded.update(url=url, body=json)
        return httpx.Response(200, json={"success": True, "saved": True, "method_id": "PM-1",
                                         "payment_type": "credit_card", "card_brand": "visa",
                                         "last_four": "1111", "token": "tok_should_not_leak"})

    monkeypatch.setattr(pm, "_customer_id", fake_customer)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    body = {"payment_type": "credit_card", "card_number": "4111111111111111", "expiry_month": 12,
            "expiry_year": 2030, "cvv": "123", "customer_id": "SOMEONE-ELSE"}
    r = client.post("/api/payment-methods", json=body, headers=_auth(client))
    assert r.status_code == 200
    assert r.json() == {"success": True, "payment_type": "credit_card", "card_brand": "visa", "last_four": "1111"}
    assert forwarded["url"].endswith("/payment-methods")
    assert forwarded["body"]["customer_id"] == "CUST-9", "customer comes from the session, not the browser"


def test_payment_method_needs_a_customer_and_a_session(client, monkeypatch):
    import api.payment_methods as pm

    async def no_customer(user_id, session_id):
        return None

    monkeypatch.setattr(pm, "_customer_id", no_customer)
    assert client.post("/api/payment-methods", json={"payment_type": "credit_card"}).status_code == 401
    r = client.post("/api/payment-methods", json={"payment_type": "credit_card"}, headers=_auth(client))
    assert r.status_code == 409


def test_payment_method_validation_error_is_passed_through(client, monkeypatch):
    import httpx

    import api.payment_methods as pm

    async def fake_customer(user_id, session_id):
        return "CUST-9"

    async def fake_post(self, url, json=None, headers=None):
        return httpx.Response(400, json={"success": False, "error": "Invalid card number (failed Luhn check)"})

    monkeypatch.setattr(pm, "_customer_id", fake_customer)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    r = client.post("/api/payment-methods", json={"payment_type": "credit_card", "card_number": "4111111111111112"},
                    headers=_auth(client))
    assert r.status_code == 400 and r.json()["error"] == "Invalid card number (failed Luhn check)"
