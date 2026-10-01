from datetime import date
from types import SimpleNamespace

from sales_common.context import (
    CONTEXT_UPDATE_KEY,
    current_date_text,
    build_forwarded_metadata,
    export_context_delta,
    extract_context_updates,
    import_forwarded_context,
)


def _cb_ctx(meta):
    return SimpleNamespace(
        state={}, run_config=SimpleNamespace(custom_metadata={"a2a_metadata": meta})
    )


def test_round_trip_metadata_into_state():
    state = {"customer_context": {"customer_id": "CUST-1", "address": {"zip_code": "19103"}}, "other": 1}
    meta = build_forwarded_metadata(state, session_id="s1", transcript="user: hi", user_profile={"company_name": "Acme"})
    ctx = _cb_ctx(meta)
    assert import_forwarded_context(ctx) is None
    assert ctx.state["customer_context"]["address"]["zip_code"] == "19103"
    assert ctx.state["journey_transcript"] == "user: hi"
    assert ctx.state["user_profile"] == {"company_name": "Acme"}
    assert "other" not in ctx.state


def test_import_ignores_non_dict_values():
    ctx = _cb_ctx({"journey": {"context": {"offer_context": "not-a-dict"}}})
    import_forwarded_context(ctx)
    assert "offer_context" not in ctx.state


def test_import_without_metadata_only_sets_current_date():
    ctx = SimpleNamespace(state={}, run_config=None)
    assert import_forwarded_context(ctx) is None
    assert ctx.state == {"current_date": current_date_text()}


def test_current_date_text():
    assert current_date_text(date(2026, 10, 1)) == "2026-10-01 (Thursday)"
    assert current_date_text().startswith(date.today().isoformat())


def test_journey_instruction_includes_current_date():
    from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

    assert "{current_date?}" in JOURNEY_CONTEXT_INSTRUCTION


def test_export_adds_update_only_for_journey_keys():
    tc = SimpleNamespace(actions=SimpleNamespace(state_delta={"offer_context": {"offer_id": "OFF-1"}, "x": 1}))
    out = export_context_delta(None, {}, tc, {"success": True})
    assert out[CONTEXT_UPDATE_KEY] == {"offer_context": {"offer_id": "OFF-1"}}
    assert out["success"] is True
    tc2 = SimpleNamespace(actions=SimpleNamespace(state_delta={"x": 1}))
    assert export_context_delta(None, {}, tc2, {"success": True}) is None


def test_export_wraps_json_string_response():
    tc = SimpleNamespace(actions=SimpleNamespace(state_delta={"customer_context": {"customer_id": "C"}}))
    out = export_context_delta(None, {}, tc, '{"success": true}')
    assert out["success"] is True and out[CONTEXT_UPDATE_KEY]["customer_context"]["customer_id"] == "C"


def test_extract_updates_from_responses():
    responses = [
        {"success": True, CONTEXT_UPDATE_KEY: {"offer_context": {"offer_id": "OFF-1"}}},
        {"result": '{"_context_update": {"order_context": {"order_id": "ORD-1"}}}'},
        {"nothing": True},
    ]
    merged = extract_context_updates(responses)
    assert merged == {"offer_context": {"offer_id": "OFF-1"}, "order_context": {"order_id": "ORD-1"}}
