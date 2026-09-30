"""Agent tests with a scripted model (no network, no API key)."""

import json
import os
import subprocess
import sys

import pytest
from google.adk import Runner
from google.adk.agents.run_config import RunConfig
from google.adk.sessions import InMemorySessionService
from google.genai import types

from sales_common.context import build_forwarded_metadata
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION
from sales_common.testing import ScriptLlm

from payment_agent import build_agent, root_agent
from payment_agent.prompts import PAYMENT_AGENT_INSTRUCTION

requires_db = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")

EXPECTED_TOOLS = {
    "validate_payment_method", "process_payment", "get_payment_methods", "tokenize_payment_method",
    "add_payment_method", "check_business_credit", "get_credit_report", "generate_invoice",
    "get_payment_history", "setup_payment_plan",
}


def test_construction():
    assert root_agent.name == "payment_agent"
    assert {t.__name__ for t in root_agent.tools} == EXPECTED_TOOLS
    assert root_agent.static_instruction == PAYMENT_AGENT_INSTRUCTION
    assert root_agent.instruction == JOURNEY_CONTEXT_INSTRUCTION
    assert root_agent.generate_content_config.temperature == 0.0
    assert root_agent.generate_content_config.max_output_tokens == 2048
    assert "transfer_to_agent" not in PAYMENT_AGENT_INSTRUCTION
    assert '"payment_confirmation": true' in PAYMENT_AGENT_INSTRUCTION
    assert root_agent.after_agent_callback is None  # legacy payment opener removed


@requires_db
async def test_process_payment_via_runner_exports_payment_context(make_order):
    from sales_common import db

    order = make_order(total=249.0)
    order_context = {
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "customer_name": order["customer_name"],
        "contact_email": order["contact_email"],
        "contact_phone": order["contact_phone"],
        "total_amount": 249.0,
    }
    confirmation = (
        "✅ Payment Processed Successfully! Your payment is complete!\n\n"
        '{"payment_confirmation": true, "amount": 249.0, "payment_method": "Visa ending in 1111", '
        '"transaction_id": "TXN-X", "status": "Approved"}'
    )
    llm = ScriptLlm(
        steps=[
            {"call": "process_payment", "args": {"amount": 249.0, "payment_method_token": "tok_visa_1111",
                                                 "description": "Payment for Fiber"}},
            {"text": confirmation},
        ],
        requests=[],
    )
    agent = build_agent(model=llm)
    runner = Runner(app_name="t", agent=agent, session_service=InMemorySessionService(),
                    auto_create_session=True)
    run_config = RunConfig(custom_metadata={
        "a2a_metadata": build_forwarded_metadata({"order_context": order_context}, session_id="gw-1"),
    })
    responses, texts = [], []
    async for event in runner.run_async(
        user_id="u", session_id="s", run_config=run_config,
        new_message=types.Content(role="user", parts=[types.Part(
            text=f"Installation is scheduled for order {order['order_id']}; total 249.00. Start payment.")]),
    ):
        for part in (event.content.parts if event.content else None) or []:
            if part.function_response and part.function_response.name == "process_payment":
                responses.append(part.function_response.response)
            if part.text:
                texts.append((event.author, part.text))

    assert len(responses) == 1
    response = responses[0]
    assert response["success"] is True
    payment_context = response["_context_update"]["payment_context"]
    assert payment_context == {
        "transaction_id": response["transaction_id"],
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "amount": 249.0,
        "status": "completed",
        "payment_method": "tok_visa_1111",
    }
    assert texts == [("payment_agent", confirmation)]
    # order_context forwarded through A2A metadata reached the templated instruction
    assert order["order_id"] in (llm.requests[0].config.system_instruction or "") or any(
        order["order_id"] in (p.text or "") for c in llm.requests[0].contents for p in (c.parts or [])
    )

    notif = db.fetch_one(
        "SELECT status, recipient_email, metadata_json FROM notifications "
        "WHERE order_id=%s AND notification_type='payment_confirmation'",
        (order["order_id"],),
    )
    assert notif["status"] == "pending"
    assert notif["recipient_email"] == order["contact_email"]
    assert json.loads(notif["metadata_json"])["args"]["transaction_id"] == response["transaction_id"]
    assert db.fetch_one("SELECT status FROM orders WHERE order_id=%s", (order["order_id"],))["status"] == "paid"


@requires_db
def test_server_module_imports():
    # Subprocess: a2a-sdk's DatabaseTaskStore registers "a2a_tasks" in process-global metadata.
    code = (
        "from payment_agent.server import app; "
        "paths = {getattr(r, 'path', None) for r in app.router.routes}; "
        "assert '/healthz' in paths, paths; print('ok')"
    )
    result = subprocess.run([sys.executable, "-c", code], env=dict(os.environ),
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("ok")
