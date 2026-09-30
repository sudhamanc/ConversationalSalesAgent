"""Agent-level tests with a scripted model (no network, no API key)."""

import uuid

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from sales_common.testing import ScriptLlm

from discovery_agent import build_agent, root_agent
from discovery_agent.prompts import DISCOVERY_AGENT_INSTRUCTION


def test_agent_definition():
    assert root_agent.name == "discovery_agent"
    assert len(root_agent.tools) == 13
    assert "transfer_to_agent" not in DISCOVERY_AGENT_INSTRUCTION
    assert root_agent.generate_content_config.temperature == 0.0


async def _run(agent, text: str):
    runner = Runner(agent=agent, app_name="discovery_test", session_service=InMemorySessionService())
    session = await runner.session_service.create_session(app_name="discovery_test", user_id="u1")
    events = []
    async for event in runner.run_async(
        user_id="u1",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=text)]),
    ):
        events.append(event)
    session = await runner.session_service.get_session(
        app_name="discovery_test", user_id="u1", session_id=session.id
    )
    return events, session


@pytest.mark.asyncio
async def test_add_new_company_exports_customer_context(seeded_db):
    name = f"Scripted Bakery {uuid.uuid4().hex[:8]}"
    llm = ScriptLlm(steps=[
        {"call": "add_new_company", "args": {
            "company_name": name, "industry": "Restaurant/Food Service", "region": "Northeast",
            "street": "10 Elm St", "city": "Boston", "state": "MA", "zip_code": "02110",
        }},
        {"text": f"Welcome! I've registered {name}. I'll check service availability for this address now..."},
    ])
    events, session = await _run(build_agent(model=llm), "We're a bakery at 10 Elm St, Boston MA 02110")

    responses = [
        part.function_response.response
        for event in events
        for part in (event.content.parts if event.content else [])
        if part.function_response and part.function_response.name == "add_new_company"
    ]
    assert len(responses) == 1
    response = responses[0]
    assert response["success"] is True
    update = response["_context_update"]["customer_context"]
    assert update["company_name"] == name
    assert update["customer_id"] == response["customer_id"]
    assert update["address"]["zip_code"] == "02110"
    assert session.state["customer_context"] == update

    final_text = "".join(
        p.text for e in events if e.content for p in e.content.parts if p.text
    )
    assert "check service availability" in final_text


def test_every_tool_has_a_description_for_the_model():
    """Regression: a log line placed before each docstring left tool descriptions empty."""
    from discovery_agent.agent import build_agent
    from sales_common.testing import ScriptLlm

    agent = build_agent(model=ScriptLlm())
    from google.adk.tools import FunctionTool

    tools = [t if isinstance(t, FunctionTool) else FunctionTool(t) for t in agent.tools]
    assert len(tools) == 13
    for tool in tools:
        declaration = tool._get_declaration()
        assert declaration.description and len(declaration.description) > 20, tool.name
