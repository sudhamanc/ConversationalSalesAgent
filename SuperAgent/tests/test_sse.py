from google.adk.events import Event, EventActions
from google.genai import types

from api.sse import EventMapper


def _text_event(author, text):
    return Event(author=author, invocation_id="i", content=types.Content(role="model", parts=[types.Part(text=text)]))


def _fr_event(author, name, response):
    return Event(author=author, invocation_id="i", content=types.Content(role="user", parts=[
        types.Part(function_response=types.FunctionResponse(name=name, response=response))]))


def test_only_domain_agents_stream_and_duplicates_dropped():
    m = EventMapper()
    assert m.consume(_text_event("route_intent", '{"target": "x"}')) == []
    assert m.consume(_text_event("sales_journey", "internal")) == []
    first = m.consume(_text_event("order_agent", "Order ORD-1 created"))
    dup = m.consume(_text_event("order_agent", "Order ORD-1 created"))
    assert first == [{"type": "token", "content": "Order ORD-1 created", "author": "order_agent"}]
    assert dup == []


def test_separator_between_agents():
    m = EventMapper()
    m.consume(_text_event("discovery_agent", "Welcome"))
    out = m.consume(_text_event("serviceability_agent", "Serviceable"))
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
