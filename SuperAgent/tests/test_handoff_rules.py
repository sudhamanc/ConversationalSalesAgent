from super_agent.workflow import (
    MAX_HANDOFF_HOPS,
    append_transcript,
    evaluate_handoff,
    is_pure_greeting,
    normalize_target,
)

CUSTOMER = {"customer_id": "C1", "company_name": "Crane", "address": {"street": "1 A St", "city": "X", "state": "PA", "zip_code": "19103"}}


def test_greeting_detection():
    assert is_pure_greeting("Hi!")
    assert is_pure_greeting("good morning")
    assert is_pure_greeting("[GREETING] hello")
    assert not is_pure_greeting("hi, we're Crane.io at 1 A St")


def test_unknown_target_falls_back_to_faq():
    assert normalize_target({"target": "order_agent"}) == "order_agent"
    assert normalize_target({"target": "billing_bot"}) == "faq_agent"
    assert normalize_target(None) == "faq_agent"


def test_discovery_to_serviceability_uses_exact_zip():
    h = evaluate_handoff({"customer_context": CUSTOMER}, "discovery_agent", 0)
    assert h.target == "serviceability_agent"
    assert '"zip_code": "19103"' in h.message


def test_no_discovery_handoff_when_already_checked():
    state = {"customer_context": CUSTOMER, "serviceability_context": {"is_serviceable": True, "service_address": {"zip_code": "19103"}}}
    assert evaluate_handoff(state, "discovery_agent", 0) is None


def test_discovery_handoff_when_address_changed():
    state = {"customer_context": CUSTOMER, "serviceability_context": {"service_address": {"zip_code": "10001"}}}
    assert evaluate_handoff(state, "discovery_agent", 0).target == "serviceability_agent"


def test_scheduling_to_payment():
    state = {"appointment_confirmed_order": "ORD-1", "order_context": {"order_id": "ORD-1", "status": "pending_payment", "total_amount": 1250.5}}
    h = evaluate_handoff(state, "service_fulfillment_agent", 0)
    assert h.target == "payment_agent" and "ORD-1" in h.message and "$1,250.50" in h.message
    assert h.clear_keys == ("appointment_confirmed_order",)


def test_no_payment_handoff_when_paid():
    for status in ("completed", "approved"):
        state = {"appointment_confirmed_order": "ORD-1", "order_context": {"status": "pending_payment"}, "payment_context": {"status": status}}
        assert evaluate_handoff(state, "service_fulfillment_agent", 0) is None


def test_hop_cap():
    assert evaluate_handoff({"customer_context": CUSTOMER}, "discovery_agent", MAX_HANDOFF_HOPS) is None


def test_transcript_is_bounded():
    t = ""
    for i in range(500):
        t = append_transcript(t, "user", f"message {i}")
    assert len(t) <= 2000 and t.endswith("message 499")


# --- returning customers (spec: conversation-orchestration) -----------------------

RETURNING = {"customer_id": "C1", "status": "known"}


def test_returning_customer_defers_serviceability_handoff():
    from super_agent.workflow import ACK_KEY, unacknowledged_returning_customer

    state = {"customer_context": CUSTOMER, "returning_customer_context": RETURNING}
    assert unacknowledged_returning_customer(state) == "C1"
    assert evaluate_handoff(state, "discovery_agent", 0) is None
    acknowledged = {**state, ACK_KEY: "C1"}
    assert unacknowledged_returning_customer(acknowledged) is None
    assert evaluate_handoff(acknowledged, "discovery_agent", 0).target == "serviceability_agent"


def test_returning_context_for_another_customer_does_not_defer():
    state = {"customer_context": CUSTOMER, "returning_customer_context": {"customer_id": "OTHER"}}
    assert evaluate_handoff(state, "discovery_agent", 0).target == "serviceability_agent"


def test_handoff_node_records_acknowledgement():
    import asyncio
    from types import SimpleNamespace

    from super_agent.workflow import ACK_KEY, HandoffPolicyNode

    node = HandoffPolicyNode(name="handoff_policy")
    ctx = SimpleNamespace(state={"last_agent": "discovery_agent", "customer_context": CUSTOMER, "returning_customer_context": RETURNING})

    async def run():
        return [e async for e in node.run_node_impl(ctx=ctx, node_input="Welcome back!")]

    (event,) = asyncio.run(run())
    assert event.actions.state_delta[ACK_KEY] == "C1"
    assert "handoff_hops" not in event.actions.state_delta  # no serviceability handoff this turn


# --- order -> scheduling (spec: guided-checkout) ------------------------------

ORDER = {"order_id": "ORD-1", "status": "pending_payment", "service_type": "Business Fiber 1 Gbps",
         "service_address": "314 Main Street, Philadelphia, PA 19103", "total_amount": 224.1}


def test_order_created_hands_off_to_scheduling():
    h = evaluate_handoff({"order_created_order": "ORD-1", "order_context": ORDER}, "order_agent", 0)
    assert h.target == "service_fulfillment_agent"
    assert "ORD-1" in h.message and "check_availability" in h.message and "314 Main Street" in h.message
    assert h.clear_keys == ("order_created_order",)


def test_no_scheduling_handoff_without_new_order_or_when_scheduled():
    assert evaluate_handoff({"order_context": ORDER}, "order_agent", 0) is None
    scheduled = {**ORDER, "installation": {"status": "scheduled"}}
    assert evaluate_handoff({"order_created_order": "ORD-1", "order_context": scheduled}, "order_agent", 0) is None
    assert evaluate_handoff({"order_created_order": "ORD-1", "order_context": ORDER,
                             "installation_scheduled_order": "ORD-1"}, "order_agent", 0) is None
    paid = {**ORDER, "status": "paid"}
    assert evaluate_handoff({"order_created_order": "ORD-1", "order_context": paid}, "order_agent", 0) is None
    assert evaluate_handoff({"order_created_order": "ORD-1", "order_context": ORDER}, "order_agent",
                            MAX_HANDOFF_HOPS) is None


def test_payment_handoff_asks_for_the_secure_form():
    state = {"appointment_confirmed_order": "ORD-1", "order_context": ORDER}
    h = evaluate_handoff(state, "service_fulfillment_agent", 0)
    assert h.target == "payment_agent" and "get_payment_methods" in h.message and "$224.10" in h.message


# --- quote selection ----------------------------------------------------------

import asyncio  # noqa: E402

from super_agent import workflow  # noqa: E402


def _select(state, message, monkeypatch, found=None):
    calls = []

    def fake_load(offer_id, customer_id):
        calls.append((offer_id, customer_id))
        return found

    monkeypatch.setattr(workflow, "_load_offer", fake_load)
    return asyncio.run(workflow._selected_offer(state, message)), calls


def test_named_quote_becomes_offer_context(monkeypatch):
    state = {"customer_context": CUSTOMER, "offer_context": {"offer_id": "OFF-520C223CCB"}}
    chosen = {"offer_id": "OFF-11EB15AA3C", "term_months": 24, "selected": True}
    result, calls = _select(state, "I'll take quote OFF-11EB15AA3C (24 months). Please place my order.",
                            monkeypatch, chosen)
    assert result == chosen and calls == [("OFF-11EB15AA3C", "C1")]


def test_current_or_unknown_quote_is_not_loaded(monkeypatch):
    state = {"customer_context": CUSTOMER, "offer_context": {"offer_id": "OFF-520C223CCB"}}
    assert _select(state, "I'll take quote OFF-520C223CCB", monkeypatch, {"x": 1}) == (None, [])
    assert _select(state, "place my order", monkeypatch, {"x": 1}) == (None, [])
    assert _select({"offer_context": {}}, "quote OFF-11EB15AA3C", monkeypatch, {"x": 1}) == (None, [])
    assert _select(state, "quote OFF-11EB15AA3C", monkeypatch, None)[0] is None


# --- contact before order (spec: guided-checkout) -----------------------------

def test_saved_contact_resumes_the_waiting_order():
    customer = {**CUSTOMER, "contact": {"name": "Jane", "email": "jane@crane.io"}}
    h = evaluate_handoff({"customer_context": customer, "order_waiting_for_contact": True}, "discovery_agent", 0)
    assert h.target == "order_agent" and "create_order" in h.message and "jane@crane.io" in h.message
    assert h.clear_keys == ("order_waiting_for_contact",)


def test_no_order_handoff_without_email_or_waiting_order():
    waiting = {"customer_context": CUSTOMER, "order_waiting_for_contact": True,
               "serviceability_context": {"service_address": {"zip_code": "19103"}}}
    assert evaluate_handoff(waiting, "discovery_agent", 0) is None
    customer = {**CUSTOMER, "contact": {"email": "jane@crane.io"}}
    state = {"customer_context": customer, "serviceability_context": {"service_address": {"zip_code": "19103"}}}
    assert evaluate_handoff(state, "discovery_agent", 0) is None


# --- contact before coverage (spec: conversation-orchestration) ---------------

def test_new_registration_waits_for_the_contact_before_coverage():
    waiting = {"customer_context": CUSTOMER, "registration_waiting_for_contact": True}
    assert evaluate_handoff(waiting, "discovery_agent", 0) is None

    saved = {"customer_context": {**CUSTOMER, "contact": {"name": "Jane", "email": "jane@crane.io"}},
             "registration_waiting_for_contact": True}
    h = evaluate_handoff(saved, "discovery_agent", 0)
    assert h.target == "serviceability_agent" and '"zip_code": "19103"' in h.message
    assert h.clear_keys == ("registration_waiting_for_contact",)

    plain = evaluate_handoff({"customer_context": CUSTOMER}, "discovery_agent", 0)
    assert plain.target == "serviceability_agent" and plain.clear_keys == ()


def _plugin_event(name, response, state=None):
    import asyncio
    from types import SimpleNamespace

    from super_agent.plugins import ContextBridgePlugin

    part = SimpleNamespace(function_response=SimpleNamespace(name=name, response=response))
    event = SimpleNamespace(author="discovery_agent", content=SimpleNamespace(parts=[part]),
                            actions=SimpleNamespace(state_delta={}))
    ctx = SimpleNamespace(session=SimpleNamespace(id="s1", state=state or {}))
    asyncio.run(ContextBridgePlugin().on_event_callback(invocation_context=ctx, event=event))
    return event.actions.state_delta


def test_plugin_flags_registration_without_contact():
    from sales_common.context import CONTEXT_UPDATE_KEY

    registered = {"success": True, "customer_id": "C1", "company_name": "Crane",
                  CONTEXT_UPDATE_KEY: {"customer_context": CUSTOMER}}
    assert _plugin_event("add_new_company", registered)["registration_waiting_for_contact"] is True

    with_contact = {"customer_context": {**CUSTOMER, "contact": {"email": "jane@crane.io"}}}
    assert "registration_waiting_for_contact" not in _plugin_event("add_new_company", {"success": True}, with_contact)
    assert "registration_waiting_for_contact" not in _plugin_event("add_new_company", {"success": False})


# --- provisioning after payment (spec: conversation-orchestration) ------------

def _paid(installation_status):
    order = {"order_id": "ORD-1", "status": "paid"}
    if installation_status:
        order["installation"] = {"appointment_id": "APT-1", "status": installation_status}
    return {"order_context": order, "payment_completed_order": "ORD-1"}


def test_payment_hands_off_to_provisioning():
    h = evaluate_handoff(_paid("scheduled"), "payment_agent", 0)
    assert h.target == "service_fulfillment_agent"
    assert "ORD-1" in h.message and "provision_equipment" in h.message and "dispatch_technician" in h.message
    assert "Do not activate" in h.message
    assert h.clear_keys == ("payment_completed_order",)


def test_no_provisioning_handoff_when_dispatched_or_unscheduled():
    assert evaluate_handoff(_paid("dispatched"), "payment_agent", 0) is None
    assert evaluate_handoff(_paid(None), "payment_agent", 0) is None
    no_payment = {"order_context": {"installation": {"status": "scheduled"}}}
    assert evaluate_handoff(no_payment, "payment_agent", 0) is None
    assert evaluate_handoff(_paid("scheduled"), "payment_agent", 2) is None  # hop limit


def test_plugin_records_completed_payment():
    paid = {"success": True, "order_id": "ORD-1", "status": "completed", "transaction_id": "TXN-1"}
    assert _plugin_event("process_payment", paid)["payment_completed_order"] == "ORD-1"
    declined = {"success": False, "order_id": "ORD-1", "status": "declined"}
    assert "payment_completed_order" not in _plugin_event("process_payment", declined)
