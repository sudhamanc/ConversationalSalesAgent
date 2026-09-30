"""Agent construction and scripted-runner tests (no network, no API key)."""

import os
import subprocess
import sys

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION
from sales_common.testing import ScriptLlm

from customer_communication_agent import build_agent, root_agent
from customer_communication_agent.prompts import CUSTOMER_COMMUNICATION_AGENT_INSTRUCTION

EXPECTED_TOOLS = {
    "send_order_confirmation",
    "send_quote_confirmation",
    "send_payment_notification",
    "send_installation_reminder",
    "send_service_activated_notification",
    "send_abandoned_cart_reminder",
    "send_order_status_update",
    "get_notification_history",
}


def test_construction():
    assert root_agent.name == "customer_communication_agent"
    assert {t.__name__ for t in root_agent.tools} == EXPECTED_TOOLS
    assert root_agent.static_instruction == CUSTOMER_COMMUNICATION_AGENT_INSTRUCTION
    assert root_agent.instruction == JOURNEY_CONTEXT_INSTRUCTION
    assert root_agent.generate_content_config.temperature == 0.0
    assert "transfer_to_agent" not in CUSTOMER_COMMUNICATION_AGENT_INSTRUCTION
    assert "sys.modules" not in CUSTOMER_COMMUNICATION_AGENT_INSTRUCTION


async def _run(agent, text):
    runner = Runner(app_name="t", agent=agent, session_service=InMemorySessionService(),
                    auto_create_session=True)
    events = []
    async for event in runner.run_async(
        user_id="u", session_id="s",
        new_message=types.Content(role="user", parts=[types.Part(text=text)]),
    ):
        events.append(event)
    return events


async def test_runner_text_reply():
    llm = ScriptLlm(steps=[{"text": "Which notification should I send?"}], requests=[])
    events = await _run(build_agent(model=llm), "Hi")
    texts = [(e.author, p.text) for e in events if e.content for p in e.content.parts or [] if p.text]
    assert texts == [("customer_communication_agent", "Which notification should I send?")]
    assert llm.requests


@pytest.mark.pg
async def test_runner_calls_send_tool(clean_db):
    llm = ScriptLlm(
        steps=[
            {"call": "send_order_confirmation",
             "args": {"order_id": "ORD-R1", "customer_name": "Acme",
                      "customer_email": "r@acme.example"}},
            {"text": "Order confirmation sent."},
        ],
        requests=[],
    )
    events = await _run(build_agent(model=llm), "Resend the order confirmation for ORD-R1")
    responses = [p.function_response.response for e in events if e.content
                 for p in e.content.parts or [] if p.function_response]
    assert responses and responses[0]["success"] is True
    assert responses[0]["status"] == "simulated"
    row = clean_db.fetch_one("SELECT status FROM notifications WHERE order_id='ORD-R1'")
    assert row["status"] == "simulated"


@pytest.mark.pg
def test_server_module_imports():
    # Subprocess: a2a-sdk's DatabaseTaskStore registers the "a2a_tasks" table in
    # process-global SQLAlchemy metadata, so only one server app per process.
    code = (
        "from customer_communication_agent.server import app; "
        "paths = {getattr(r, 'path', None) for r in app.router.routes}; "
        "assert '/healthz' in paths, paths; print('ok')"
    )
    env = dict(os.environ)
    env.pop("SMTP_ENABLED", None)
    result = subprocess.run([sys.executable, "-c", code], env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("ok")
