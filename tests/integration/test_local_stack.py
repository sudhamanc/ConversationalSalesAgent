"""Multi-process integration test: 2 tool services + 10 A2A agents + gateway.

Real PostgreSQL, real A2A (JSON-RPC over HTTP), real MCP (streamable HTTP); the
LLM is the scripted ``fake-sales`` model from ``fake_llm/sitecustomize.py``.

Run::

    TEST_DATABASE_URL=postgresql://... venv/bin/python -m pytest tests/integration -q -s
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
DB = os.getenv("TEST_DATABASE_URL", "")
LOGS = ROOT / "logs" / "integration"

TOOLS = [("catalog", "services/catalog", "catalog_service.app:app", 18101),
         ("serviceability", "services/serviceability", "serviceability_service.app:app", 18102)]
AGENTS = [
    ("discovery_agent", "DiscoveryAgent", "discovery_agent.server:app", 18201),
    ("serviceability_agent", "ServiceabilityAgent", "serviceability_agent.server:app", 18202),
    ("product_agent", "ProductAgent", "product_agent.server:app", 18203),
    ("offer_management_agent", "OfferManagement", "offer_management.server:app", 18204),
    ("order_agent", "OrderAgent", "order_agent.server:app", 18205),
    ("payment_agent", "PaymentAgent", "payment_agent.server:app", 18206),
    ("service_fulfillment_agent", "ServiceFulfillmentAgent", "service_fulfillment_agent.server:app", 18207),
    ("customer_communication_agent", "CustomerCommunicationAgent", "customer_communication_agent.server:app", 18208),
    ("greeting_agent", "GreetingAgent", "greeting_agent.server:app", 18209),
    ("faq_agent", "FAQAgent", "faq_agent.server:app", 18210),
]
GATEWAY_PORT = 18000

pytestmark = pytest.mark.skipif(not DB, reason="TEST_DATABASE_URL not set")


def _env(**extra) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AGENT_URL_", "PUBLIC_URL"))}
    env.update(
        DATABASE_URL=DB,
        GEMINI_MODEL="fake-sales",
        SERVICE_AUTH="none",
        LOG_LEVEL="INFO",
        PYTHONPATH=os.pathsep.join([str(ROOT / "tests/integration/fake_llm"), env.get("PYTHONPATH", "")]),
        CATALOG_MCP_URL=f"http://127.0.0.1:{TOOLS[0][3]}/mcp/",
        SERVICEABILITY_MCP_URL=f"http://127.0.0.1:{TOOLS[1][3]}/mcp/",
        SMTP_ENABLED="false",
        NOTIFY_POLL_SECONDS="2",
    )
    env.update(extra)
    return env


def _start(name, cwd, module, port, env):
    LOGS.mkdir(parents=True, exist_ok=True)
    log = open(LOGS / f"{name}.log", "w")
    return subprocess.Popen(
        [PY, "-m", "uvicorn", module, "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT / cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
    )


def _wait(url, name, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    tail = (LOGS / f"{name}.log").read_text()[-3000:]
    raise AssertionError(f"{name} not healthy at {url}\n{tail}")


@pytest.fixture(scope="module")
def stack():
    subprocess.run([PY, "-m", "sales_common.migrate", "--seed"], cwd=ROOT, env=_env(), check=True)
    procs = []
    try:
        for name, cwd, module, port in TOOLS:
            procs.append(_start(name, cwd, module, port, _env()))
        for name, _, _, port in TOOLS:
            _wait(f"http://127.0.0.1:{port}/healthz", name)
        for name, cwd, module, port in AGENTS:
            procs.append(_start(name, cwd, module, port, _env(PUBLIC_URL=f"http://127.0.0.1:{port}")))
        for name, _, _, port in AGENTS:
            _wait(f"http://127.0.0.1:{port}/healthz", name)
        gw_env = _env(SESSION_SECRET_KEY="integration-secret", SUGGESTIONS_ENABLED="false", DEBUG="true",
                      **{f"AGENT_URL_{n.upper()}": f"http://127.0.0.1:{p}" for n, _, _, p in AGENTS})
        procs.append(_start("gateway", "SuperAgent/server", "main:app", GATEWAY_PORT, gw_env))
        _wait(f"http://127.0.0.1:{GATEWAY_PORT}/health", "gateway")
        yield f"http://127.0.0.1:{GATEWAY_PORT}"
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


def _chat(base, token, message):
    r = httpx.post(f"{base}/api/chat", json={"message": message},
                   headers={"Authorization": f"Bearer {token}"}, timeout=180)
    assert r.status_code == 200, r.text
    return [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]


def _authors(events):
    return [e["author"] for e in events if e["type"] == "token" and e["content"].strip()]


def test_agent_cards_and_mcp_tools(stack):
    for name, _, _, port in AGENTS:
        card = httpx.get(f"http://127.0.0.1:{port}/.well-known/agent-card.json", timeout=5).json()
        assert card["name"] == name
    r = httpx.post(f"http://127.0.0.1:{TOOLS[1][3]}/api/v1/serviceability/check",
                   json={"street": "123 Main St", "city": "Philadelphia", "state": "PA", "zip_code": "19103"}, timeout=10)
    assert r.json()["serviceable"] is True and r.json()["available_products"]


def test_conversation_over_a2a(stack):
    token = httpx.post(f"{stack}/api/session", json={"client_id": "0b7c9a4e-8f1d-4c2a-9d3e-2f6a7b8c9d0e"}).json()["token"]

    greet = _chat(stack, token, "hi")
    assert _authors(greet) and set(_authors(greet)) == {"greeting_agent"}

    reg = _chat(stack, token, "We're Crane.io at 123 Main St, Philadelphia, PA 19103")
    authors = _authors(reg)
    assert "discovery_agent" in authors and "serviceability_agent" in authors, reg
    assert authors.index("discovery_agent") < authors.index("serviceability_agent")
    assert any(e["type"] == "activity_update" and e["category"] == "customer" for e in reg)
    svc_text = " ".join(e["content"] for e in reg if e["type"] == "token" and e["author"] == "serviceability_agent")
    assert "check_service_availability" in svc_text and "19103" in svc_text

    # Journey context crossed the A2A boundary back into the gateway session.
    state = httpx.get(f"{stack}/api/debug/session", headers={"Authorization": f"Bearer {token}"}).json()["state"]
    assert state["customer_context"]["address"]["zip_code"] == "19103"
    assert state["serviceability_context"]["is_serviceable"] is True
    assert any(sku.startswith("FIB-") for sku in state["serviceability_context"]["available_products"])
    assert state["user:company_name"].startswith("Crane.io")

    prod = _chat(stack, token, "Show me your internet products")
    assert set(_authors(prod)) == {"product_agent"}
    assert "FIB-1G" in " ".join(e["content"] for e in prod if e["type"] == "token")
    assert prod[-1] == {"type": "done"}
