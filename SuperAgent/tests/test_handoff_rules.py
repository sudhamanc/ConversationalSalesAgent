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
