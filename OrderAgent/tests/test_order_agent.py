"""Agent-level tests with a scripted model (no network)."""

import asyncio
import os
import subprocess
import sys
import uuid

import pytest
from google.adk import Runner
from google.adk.agents.run_config import RunConfig
from google.adk.sessions import InMemorySessionService
from google.genai import types

from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION
from sales_common.testing import ScriptLlm

from order_agent import build_agent, root_agent
from order_agent.prompts import ORDER_AGENT_INSTRUCTION


def test_construction():
    assert root_agent.name == "order_agent"
    assert len(root_agent.tools) == 11
    assert root_agent.static_instruction == ORDER_AGENT_INSTRUCTION
    assert root_agent.instruction == JOURNEY_CONTEXT_INSTRUCTION
    assert root_agent.generate_content_config.temperature == 0.0
    assert "transfer_to_agent" not in ORDER_AGENT_INSTRUCTION
    assert '"order_confirmation": true' in ORDER_AGENT_INSTRUCTION


def _run(agent, text, metadata):
    runner = Runner(app_name="t", agent=agent, session_service=InMemorySessionService(),
                    auto_create_session=True)

    async def go():
        events = []
        async for event in runner.run_async(
            user_id="u", session_id="s",
            new_message=types.Content(role="user", parts=[types.Part(text=text)]),
            run_config=RunConfig(custom_metadata={"a2a_metadata": metadata}),
        ):
            events.append(event)
        return events

    return asyncio.run(go())


def test_create_order_exports_order_context(pg, quote):
    from sales_common import db

    name = f"Agent Order {uuid.uuid4().hex[:6]}"
    llm = ScriptLlm(
        steps=[
            {"call": "create_order",
             "args": {"customer_name": name, "service_address": "9 Elm St, Boston MA 02108",
                      "service_type": "Business Fiber 1 Gbps", "contact_email": "agent@example.com"}},
            {"text": "✅ Order Created! Next step: let's schedule your installation appointment."},
        ],
        requests=[],
    )
    metadata = {"journey": {"context": {
        "customer_context": {"customer_id": "CUST-AGENT-1", "company_name": name},
        "offer_context": {"offer_id": quote, "total_price": 249.0},
    }}}
    events = _run(build_agent(model=llm), "I'm ready to proceed", metadata)

    responses = [p.function_response for e in events for p in (e.content.parts if e.content else [])
                 if p.function_response]
    assert responses and responses[0].name == "create_order"
    body = responses[0].response
    oc = body["_context_update"]["order_context"]
    assert oc["order_id"] == body["order_id"]
    assert oc["customer_id"] == "CUST-AGENT-1"
    assert oc["offer_id"] == quote and oc["total_amount"] == 249.0
    assert oc["status"] == "pending_payment"

    notif = db.fetch_one(
        "SELECT status FROM notifications WHERE order_id=%s AND notification_type='order_confirmation'",
        (body["order_id"],),
    )
    assert notif and notif["status"] == "pending"
    texts = [p.text for e in events for p in (e.content.parts if e.content else []) if p.text]
    assert texts[-1].startswith("✅ Order Created!")


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")
def test_server_module_imports():
    # Separate process: create_a2a_app registers the a2a_tasks table in
    # process-global SQLAlchemy metadata, so it can only be built once per process.
    code = (
        "import order_agent.server as s; "
        "paths = {getattr(r, 'path', None) for r in s.app.router.routes}; "
        "assert '/healthz' in paths, paths; print('ok')"
    )
    out = subprocess.run([sys.executable, "-c", code], env=dict(os.environ),
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip().endswith("ok")
