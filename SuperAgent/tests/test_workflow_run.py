"""Run the real sales_journey graph with in-process scripted agents."""

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from fakes import build_fake_agents, router
from super_agent.agent import build_gateway_app


async def _turn(runner, session, text):
    events = []
    async for ev in runner.run_async(user_id=session.user_id, session_id=session.id,
                                     new_message=types.Content(role="user", parts=[types.Part(text=text)])):
        events.append(ev)
    return events


def _texts(events):
    """Texts authored by domain agents (router/workflow output is internal)."""
    from super_agent.registry import AGENT_NAMES

    return [(e.author, p.text) for e in events if e.author in AGENT_NAMES and e.content and e.content.parts
            for p in e.content.parts if p.text]


async def _setup(target, state=None):
    router_llm = router(target)
    app = build_gateway_app(agents=build_fake_agents(), router_model=router_llm)
    ss = InMemorySessionService()
    runner = Runner(app=app, session_service=ss)
    session = await ss.create_session(app_name=app.name, user_id="web:u1", state=state or {})
    return runner, ss, session, router_llm


async def test_routes_to_router_choice():
    runner, ss, session, router_llm = await _setup("product_agent")
    events = await _turn(runner, session, "What internet products do you offer?")
    assert ("product_agent", "product_agent reply") in _texts(events)
    s = await ss.get_session(app_name=runner.app_name, user_id="web:u1", session_id=session.id)
    assert s.state["last_agent"] == "product_agent"
    assert len(router_llm.requests) == 1


async def test_greeting_fast_path_skips_router():
    runner, _, session, router_llm = await _setup("order_agent")
    events = await _turn(runner, session, "hello")
    assert ("greeting_agent", "greeting_agent reply") in _texts(events)
    assert router_llm.requests == []


async def test_unknown_route_falls_back_to_faq():
    runner, _, session, _ = await _setup("billing_bot")
    events = await _turn(runner, session, "what is your cancellation policy?")
    assert ("faq_agent", "faq_agent reply") in _texts(events)


async def test_discovery_then_serviceability_same_turn():
    runner, ss, session, _ = await _setup("discovery_agent")
    events = await _turn(runner, session, "We're Crane.io at 123 Main St, Philadelphia PA 19103")
    authors = [a for a, _ in _texts(events)]
    assert "discovery_agent" in authors and "serviceability_agent" in authors
    assert authors.index("discovery_agent") < authors.index("serviceability_agent")
    s = await ss.get_session(app_name=runner.app_name, user_id="web:u1", session_id=session.id)
    assert s.state["serviceability_context"]["service_address"]["zip_code"] == "19103"
    assert s.state["user:company_name"] == "Crane.io"
    assert s.state["last_agent"] == "serviceability_agent"


async def test_scheduling_then_payment_same_turn():
    state = {"order_context": {"order_id": "ORD-1", "status": "pending_payment", "total_amount": 500.0}}
    runner, ss, session, _ = await _setup("service_fulfillment_agent", state)
    events = await _turn(runner, session, "Schedule installation for Oct 2")
    authors = [a for a, _ in _texts(events)]
    assert authors[:1] == ["service_fulfillment_agent"] and "payment_agent" in authors
    s = await ss.get_session(app_name=runner.app_name, user_id="web:u1", session_id=session.id)
    assert s.state.get("appointment_confirmed_order") is None


async def test_no_payment_handoff_when_already_paid():
    state = {"order_context": {"order_id": "ORD-1", "status": "pending_payment"}, "payment_context": {"status": "completed"}}
    runner, _, session, _ = await _setup("service_fulfillment_agent", state)
    authors = [a for a, _ in _texts(await _turn(runner, session, "reschedule please"))]
    assert "payment_agent" not in authors


async def test_quote_context_update_reaches_gateway_state():
    runner, ss, session, _ = await _setup("offer_management_agent")
    await _turn(runner, session, "Give me a quote for FIB-1G")
    s = await ss.get_session(app_name=runner.app_name, user_id="web:u1", session_id=session.id)
    assert s.state["offer_context"]["offer_id"] == "OFF-1"
