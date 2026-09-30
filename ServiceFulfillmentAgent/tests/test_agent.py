"""Agent construction and scripted-model (ScriptLlm) runner tests."""

import importlib

from google.adk import Runner
from google.adk.agents.run_config import RunConfig
from google.adk.sessions import InMemorySessionService
from google.genai import types

from sales_common import db
from sales_common.context import CONTEXT_UPDATE_KEY, build_forwarded_metadata, extract_context_updates
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION
from sales_common.testing import ScriptLlm

from service_fulfillment_agent import build_agent, root_agent
from service_fulfillment_agent.prompts import SERVICE_FULFILLMENT_AGENT_INSTRUCTION

from .conftest import requires_db

CONFIRMATION = (
    "✅ **Installation Scheduled!**\n\nYour installation is confirmed! Now let's proceed with payment."
)


def test_construction():
    assert root_agent.name == "service_fulfillment_agent"
    assert root_agent.static_instruction == SERVICE_FULFILLMENT_AGENT_INSTRUCTION
    assert root_agent.instruction == JOURNEY_CONTEXT_INSTRUCTION
    assert root_agent.generate_content_config.temperature == 0.3
    assert root_agent.after_agent_callback is None  # no Fulfillment->Payment transfer here
    names = {t.__name__ for t in root_agent.tools}
    assert {"check_availability", "schedule_installation", "activate_service",
            "dispatch_technician", "get_fulfillment_status"} <= names


def test_prompt_has_no_transfer_mechanics():
    assert "transfer_to_agent" not in SERVICE_FULFILLMENT_AGENT_INSTRUCTION
    assert "auto-route" not in SERVICE_FULFILLMENT_AGENT_INSTRUCTION
    assert "Now let's proceed with payment." in SERVICE_FULFILLMENT_AGENT_INSTRUCTION


async def test_schedule_installation_via_runner(order, next_weekday):
    llm = ScriptLlm(
        steps=[
            {"call": "schedule_installation", "args": {"scheduled_date": next_weekday, "window": "PM"}},
            {"text": CONFIRMATION},
        ],
        requests=[],
    )
    agent = build_agent(model=llm)
    sessions = InMemorySessionService()
    runner = Runner(app_name="t", agent=agent, session_service=sessions, auto_create_session=True)
    # Journey context arrives as A2A request metadata from the gateway.
    metadata = build_forwarded_metadata({"order_context": order}, session_id="gw-1")
    run_config = RunConfig(custom_metadata={"a2a_metadata": metadata})

    responses, texts = [], []
    async for event in runner.run_async(
        user_id="u", session_id="s",
        new_message=types.Content(role="user", parts=[types.Part(text=f"{next_weekday} afternoon please")]),
        run_config=run_config,
    ):
        for part in (event.content.parts if event.content and event.content.parts else []):
            if part.function_response and part.function_response.name == "schedule_installation":
                responses.append(part.function_response.response)
            if part.text:
                texts.append((event.author, part.text))

    assert len(responses) == 1
    response = responses[0]
    assert response["success"] is True
    assert response["order_id"] == order["order_id"]
    assert response["scheduled_date"] == next_weekday and response["window"] == "PM"
    assert response["appointment_id"].startswith("APT-")
    # Journey delta surfaced to the gateway: order_context with the installation, status unchanged.
    update = extract_context_updates([response])
    assert CONTEXT_UPDATE_KEY in response
    assert update["order_context"]["installation"]["appointment_id"] == response["appointment_id"]
    assert update["order_context"]["status"] == "pending_payment"
    assert texts == [("service_fulfillment_agent", CONFIRMATION)]

    row = db.fetch_one("SELECT status FROM fulfillments WHERE fulfillment_id = %s", (response["appointment_id"],))
    assert row["status"] == "scheduled"
    assert db.fetch_one(
        "SELECT count(*) AS n FROM notifications WHERE order_id = %s AND notification_type = 'installation_scheduled'",
        (order["order_id"],),
    )["n"] == 1


@requires_db
def test_server_module_imports():
    server = importlib.import_module("service_fulfillment_agent.server")
    paths = {getattr(r, "path", None) for r in server.app.router.routes}
    assert "/healthz" in paths
