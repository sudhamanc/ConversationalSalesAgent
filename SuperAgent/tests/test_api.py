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
