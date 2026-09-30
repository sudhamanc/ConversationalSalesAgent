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
