import pytest
from google.adk.events import Event, EventActions
from google.genai import types

from api.sse import EventMapper


def _text_event(author, text):
    return Event(author=author, invocation_id="i", content=types.Content(role="model", parts=[types.Part(text=text)]))


def _fr_event(author, name, response):
    return Event(author=author, invocation_id="i", content=types.Content(role="user", parts=[
        types.Part(function_response=types.FunctionResponse(name=name, response=response))]))


def _no_progress(payloads):
    return [p for p in payloads if p["type"] != "progress"]


def test_only_domain_agents_stream_and_duplicates_dropped():
    m = EventMapper()
    assert m.consume(_text_event("route_intent", '{"target": "x"}')) == []
    assert m.consume(_text_event("sales_journey", "internal")) == []
    first = m.consume(_text_event("order_agent", "Order ORD-1 created"))
    dup = m.consume(_text_event("order_agent", "Order ORD-1 created"))
    assert first == [{"type": "progress", "stage": "agent", "agent": "order_agent"},
                     {"type": "token", "content": "Order ORD-1 created", "author": "order_agent"}]
    assert dup == []


def test_separator_between_agents():
    m = EventMapper()
    m.consume(_text_event("discovery_agent", "Welcome"))
    out = _no_progress(m.consume(_text_event("serviceability_agent", "Serviceable")))
    assert out[0]["content"] == "\n\n" and out[1]["author"] == "serviceability_agent"


def test_quote_card_and_context_update_stripped():
    m = EventMapper()
    out = m.consume(_fr_event("offer_management_agent", "generate_offer_quote",
                              {"offer_id": "OFF-1", "total_price": 10.0, "_context_update": {"offer_context": {}}}))
    card = [p for p in out if p["type"] == "structured_card"][0]
    assert card["card_type"] == "quote" and "_context_update" not in card["data"]


def test_payment_completed_updates_order_status():
    m = EventMapper()
    out = m.consume(_fr_event("payment_agent", "process_payment", {"success": True, "status": "completed"}))
    assert {"type": "activity_update", "category": "order", "tool": "payment_update",
            "data": {"payment_status": "paid", "status": "confirmed"}} in out


def test_current_target_tracked_from_route():
    m = EventMapper()
    m.consume(Event(author="sales_journey", invocation_id="i", actions=EventActions(route="payment_agent")))
    assert m.current_target == "payment_agent"


def test_cart_update():
    m = EventMapper()
    out = m.consume(_fr_event("order_agent", "add_to_cart", {"success": True, "cart": {"cart_id": "C1", "items": [1]}}))
    assert out[-1]["type"] == "cart_update" and out[-1]["data"]["cart_id"] == "C1"


_QUOTE = {"offer_id": "OFF-1", "monthly_total": 450.0, "items": [
    {"product_name": "Fiber 1 Gbps", "quantity": 1, "price_points": {"unit_price": 450.0}, "final_price": 450.0}]}


def test_a2ui_surface_emitted_next_to_quote_card():
    m = EventMapper()
    out = m.consume(_fr_event("offer_management_agent", "generate_offer_quote",
                              {**_QUOTE, "_context_update": {"offer_context": {}}}))
    types_ = [p["type"] for p in out]
    assert "structured_card" in types_
    a2ui = [p for p in out if p["type"] == "a2ui"]
    assert len(a2ui) == 1
    event = a2ui[0]
    assert event["tool"] == "generate_offer_quote" and event["author"] == "offer_management_agent"
    assert event["kind"] == "quote"
    assert event["operations"][0]["createSurface"]["surfaceId"] == event["surface_id"]
    assert "_context_update" not in str(event["operations"])


def test_a2ui_repeated_result_sent_once():
    m = EventMapper()
    first = m.consume(_fr_event("offer_management_agent", "generate_offer_quote", _QUOTE))
    again = m.consume(_fr_event("offer_management_agent", "generate_offer_quote", _QUOTE))
    assert [p["type"] for p in first].count("a2ui") == 1
    assert [p["type"] for p in again].count("a2ui") == 0


def test_a2ui_disabled():
    m = EventMapper(a2ui_enabled=False)
    out = m.consume(_fr_event("offer_management_agent", "generate_offer_quote", _QUOTE))
    assert "structured_card" in [p["type"] for p in out]
    assert all(p["type"] != "a2ui" for p in out)


def test_a2ui_from_mcp_serviceability_result():
    payload = {"serviceable": True, "address": {"street": "1 Main St", "city": "Philadelphia", "state": "PA",
                                                 "zip_code": "19103"},
               "infrastructure_type": "FTTP", "max_speed_mbps": 5000}
    m = EventMapper()
    out = m.consume(_fr_event("serviceability_agent", "check_service_availability",
                              {"content": [{"type": "text", "text": "{}"}], "structuredContent": payload}))
    assert [p["kind"] for p in out if p["type"] == "a2ui"] == ["serviceability"]


def test_payment_tokens_never_reach_the_browser():
    m = EventMapper()
    out = m.consume(_fr_event("payment_agent", "process_payment", {
        "success": True, "status": "completed", "amount": 10.0, "order_id": "ORD-1",
        "payment_method_token": "tok_abc", "payment_method": "tok_abc", "transaction_id": "TXN-1"}))
    assert out and "tok_" not in str(out)


def test_selected_quote_updates_the_quote_panel():
    m = EventMapper()
    offer = {"offer_id": "OFF-11EB15AA3C", "term_months": 24, "monthly_total": 236.55, "selected": True}
    out = m.consume(Event(author="prepare_turn", invocation_id="i", actions=EventActions(state_delta={"offer_context": offer})))
    assert out == [{"type": "activity_update", "category": "quote", "tool": "select_quote", "data": offer}]
    assert m.state["offer_context"]["offer_id"] == "OFF-11EB15AA3C"


# --- progress (spec: conversation-orchestration, turn progress events) -------

def _route_event(target):
    return Event(author="sales_journey", invocation_id="i", actions=EventActions(route=target))


def test_progress_once_per_agent_across_a_handoff():
    m = EventMapper()
    out = m.consume(_route_event("discovery_agent"))
    out += m.consume(_text_event("discovery_agent", "Welcome"))
    out += m.consume(_fr_event("discovery_agent", "add_new_company", {"success": True}))
    out += m.consume(_route_event("serviceability_agent"))
    out += m.consume(_text_event("serviceability_agent", "Serviceable"))
    progress = [p for p in out if p["type"] == "progress"]
    assert progress == [
        {"type": "progress", "stage": "agent", "agent": "discovery_agent"},
        {"type": "progress", "stage": "agent", "agent": "serviceability_agent"},
    ]


def test_routing_bookkeeping_gives_no_progress():
    m = EventMapper()
    assert m.consume(_text_event("route_intent", '{"target": "x"}')) == []
    assert m.consume(_route_event("not_an_agent")) == []


# --- queued notifications (spec: conversation-orchestration, email dispatch) -

@pytest.mark.parametrize("tool,response", [
    ("process_payment", {"success": True, "status": "completed", "notification_id": "NTF-1"}),
    ("create_order", {"success": True, "order_id": "ORD-1", "email_notification_id": "NTF-2"}),
    ("schedule_installation", {"success": True, "notification_queued": True}),
    ("process_payment", {"success": True, "email_confirmation_queued": True}),
    ("generate_offer_quote", {"offer_id": "OFF-1", "notification_sent": {"notification_id": "NTF-3"}}),
])
def test_queued_notification_detected(tool, response):
    m = EventMapper()
    m.consume(_fr_event("order_agent", tool, response))
    assert m.notification_queued is True


@pytest.mark.parametrize("response", [
    {"success": True, "notification_queued": False},
    {"success": True, "email_confirmation_queued": False, "notification_id": None},
    {"offer_id": "OFF-1"},
])
def test_no_queued_notification(response):
    m = EventMapper()
    m.consume(_fr_event("order_agent", "create_order", response))
    assert m.notification_queued is False


@pytest.mark.parametrize("tool,response,ids", [
    ("create_order", {"success": True, "email_notification_id": "N-O"}, ["N-O"]),
    ("process_payment", {"success": True, "notification_id": "N-P", "email_confirmation_queued": True}, ["N-P"]),
    ("schedule_installation", {"success": True, "notification_queued": True, "notification_id": "N-S"}, ["N-S"]),
    ("generate_offer_quote", {"offer_id": "OFF-1", "notification_sent": {"notification_id": "N-Q"}}, ["N-Q"]),
    ("create_order", {"success": False, "error": "contact_email_required"}, []),
])
def test_notification_ids_collected(tool, response, ids):
    m = EventMapper(a2ui_enabled=False)
    m.consume(_fr_event("order_agent", tool, response))
    assert m.notification_ids == ids
