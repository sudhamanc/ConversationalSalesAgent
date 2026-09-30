"""Agent-level tests with a scripted model (no network)."""

import asyncio
import json
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

from offer_management import build_agent, root_agent
from offer_management.prompts import OFFER_MANAGEMENT_AGENT_INSTRUCTION


def test_construction():
    assert root_agent.name == "offer_management_agent"
    assert {t.__name__ for t in root_agent.tools} == {
        "find_best_bundle_offer", "generate_offer_quote", "get_existing_quotes", "get_quote_details",
    }
    assert root_agent.static_instruction == OFFER_MANAGEMENT_AGENT_INSTRUCTION
    assert root_agent.instruction == JOURNEY_CONTEXT_INSTRUCTION
    assert root_agent.generate_content_config.temperature == 0.0
    assert root_agent.generate_content_config.max_output_tokens == 2048
    assert "transfer_to_agent" not in OFFER_MANAGEMENT_AGENT_INSTRUCTION


def _run(agent, text, metadata=None):
    runner = Runner(app_name="t", agent=agent, session_service=InMemorySessionService(),
                    auto_create_session=True)
    run_config = RunConfig(custom_metadata={"a2a_metadata": metadata}) if metadata else None

    async def go():
        events = []
        async for event in runner.run_async(
            user_id="u", session_id="s",
            new_message=types.Content(role="user", parts=[types.Part(text=text)]),
            run_config=run_config,
        ):
            events.append(event)
        return events

    return asyncio.run(go())


def test_generate_quote_exports_offer_context(pg):
    from sales_common import db

    cid = f"CUST-AG-{uuid.uuid4().hex[:6]}"
    llm = ScriptLlm(
        steps=[
            {"call": "generate_offer_quote",
             "args": {"items": json.dumps([{"product_id": "FIB-5G"}]), "term_months": 24,
                      "customer_email": "buyer@example.com"}},
            {"text": "Here is your quote."},
        ],
        requests=[],
    )
    metadata = {"journey": {"context": {"customer_context": {"customer_id": cid,
                                                             "company_name": "Agent Test Co"}}}}
    events = _run(build_agent(model=llm), "Price FIB-5G for 24 months", metadata)

    responses = [p.function_response for e in events for p in (e.content.parts if e.content else [])
                 if p.function_response]
    assert responses and responses[0].name == "generate_offer_quote"
    body = responses[0].response
    offer_ctx = body["_context_update"]["offer_context"]
    assert offer_ctx["offer_id"] == body["offer_id"]
    assert offer_ctx["customer_id"] == cid  # read from forwarded customer_context
    assert offer_ctx["company_name"] == "Agent Test Co"
    assert body["notification_sent"]["type"] == "QUOTE_CONFIRMATION"
    assert db.fetch_one("SELECT 1 FROM quotes WHERE offer_id = %s AND customer_id = %s",
                        (body["offer_id"], cid))
    texts = [p.text for e in events for p in (e.content.parts if e.content else []) if p.text]
    assert texts[-1] == "Here is your quote."
    assert all(e.author in ("offer_management_agent", "user") for e in events)


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")
def test_server_module_imports():
    # Separate process: create_a2a_app registers the a2a_tasks table in
    # process-global SQLAlchemy metadata, so it can only be built once per process.
    code = (
        "import offer_management.server as s; "
        "paths = {getattr(r, 'path', None) for r in s.app.router.routes}; "
        "assert '/healthz' in paths, paths; print('ok')"
    )
    out = subprocess.run([sys.executable, "-c", code], env=dict(os.environ),
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip().endswith("ok")
