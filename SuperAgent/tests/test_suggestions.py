"""Customer-voice, journey-aware suggestion chips (spec: conversation-orchestration)."""

from types import SimpleNamespace

import pytest

from api import suggestion_playbook as pb
from api import suggestions

CUSTOMER = {"customer_context": {"customer_id": "C1", "company_name": "Acme", "address": {"zip_code": "21201"}}}
SERVICEABLE = {**CUSTOMER, "serviceability_context": {"is_serviceable": True}}
QUOTE = {**SERVICEABLE, "offer_context": {"offer_id": "OFF-1"}}
ORDER = {**QUOTE, "order_context": {"order_id": "ORD-1", "status": "pending_payment"}}
SCHEDULED = {**ORDER, "installation_scheduled_order": "ORD-1"}
PAID = {**SCHEDULED, "payment_context": {"status": "completed"}}


@pytest.mark.parametrize(
    "state, stage",
    [
        (None, "new"),
        ({}, "new"),
        (CUSTOMER, "address"),
        (SERVICEABLE, "products"),
        ({**CUSTOMER, "serviceability_context": {"is_serviceable": False}}, "not_serviceable"),
        (QUOTE, "quote"),
        (ORDER, "schedule"),
        (SCHEDULED, "payment"),
        (PAID, "provisioning"),
    ],
)
def test_journey_stage(state, stage):
    assert pb.journey_stage(state) == stage


def test_every_playbook_chip_meets_the_contract():
    for stage, chips in pb.PLAYBOOK.items():
        assert len(chips) == 3, stage
        assert all(pb.is_valid(c) for c in chips), stage
    assert set(pb.STAGE_HINTS) == set(pb.PLAYBOOK)


@pytest.mark.parametrize(
    "reply, expected",
    [
        ("Welcome! What is your company name and business address?", "We're [company name]"),
        ("Thanks. Could you share the service address including ZIP code?", "Our address is"),
        ("What email address and phone number should we use?", "[email]"),
        ("I'll need your payment details to complete the order.", "[card number]"),
        ("Which date works best for your installation appointment?", "[date]"),
        ("How many employees do you have, and what speed do you need?", "[number] employees"),
        ("Would you like to add any other products or services before we proceed?", "that's everything"),
        ("Here is your quote. Would you like to proceed with this quote?", "Yes, let's go ahead"),
    ],
)
def test_reply_template_answers_the_question(reply, expected):
    assert expected in (pb.reply_template(reply) or "")


def test_no_reply_template_without_a_question():
    assert pb.reply_template("Great news: fiber up to 5 Gbps is available at 21201.") is None


def test_topic_comes_from_the_question_not_earlier_text():
    reply = "Your address at 234 Charles Street is serviceable. Would you like a quote on a 36-month term?"
    assert pb.reply_template(reply) == "Yes, let's go ahead"


@pytest.mark.parametrize(
    "chip",
    [
        "Tell me about your company and location",
        "What is your business address?",
        "Send order confirmation to customer",
        "Send a status update to the customer",
        "Continue",
        "Show me next best step",
        "x" * 81,
    ],
)
def test_validator_rejects_rep_voice_and_filler(chip):
    assert not pb.is_valid(chip)


@pytest.mark.parametrize(
    "chip",
    ["We're [company name], located at [street, city, state ZIP]", "Email me the order confirmation", "Simulate my install day"],
)
def test_validator_keeps_customer_voice(chip):
    assert pb.is_valid(chip)


def test_finalize_puts_fill_in_first_when_agent_asked():
    reply = "Thanks! What is your company name and address?"
    out = pb.finalize(["Show me plans", "Tell me about your company"], reply, "new")
    assert out[0].startswith("We're [company name]")
    assert "Show me plans" in out
    assert len(out) == 3
    assert not any("your company" in c.lower() for c in out)


def test_finalize_keeps_llm_fill_in_in_first_place():
    reply = "What is your company name and address?"
    llm = ["We're [company name] at [address]", "What plans do you offer?"]
    assert pb.finalize(llm, reply, "new")[0] == llm[0]


def test_finalize_tops_up_from_stage_playbook():
    out = pb.finalize([], "Here is your quote.", "quote")
    assert out == pb.PLAYBOOK["quote"]


def _fake_genai(monkeypatch, text=None, error=None, captured=None):
    class FakeModels:
        def generate_content(self, **kwargs):
            if captured is not None:
                captured.append(kwargs["contents"])
            if error:
                raise error
            return SimpleNamespace(text=text, usage_metadata=None)

    monkeypatch.setattr("google.genai.Client", lambda *a, **k: SimpleNamespace(models=FakeModels()))


def test_prompt_is_customer_voice_and_includes_closing_question(monkeypatch):
    prompts: list[str] = []
    _fake_genai(monkeypatch, text='{"suggestions": []}', captured=prompts)
    reply = "Here are our plans. " + "Details. " * 150 + "What email should we use for confirmations?"
    suggestions.generate_suggestions("hi", reply, "discovery_agent", QUOTE)
    (prompt,) = prompts
    assert "CUSTOMER" in prompt and "first person" in prompt
    assert "What email should we use for confirmations?" in prompt
    assert "Journey stage: quote" in prompt
    assert "Known: company, service address, serviceable, quote" in prompt
    assert "[email]" in prompt


def test_rep_voice_model_output_is_replaced(monkeypatch):
    _fake_genai(monkeypatch, text='{"suggestions": ["Send order confirmation to customer", "Continue", "Show my order details"]}')
    out = suggestions.generate_suggestions("ok", "Your order ORD-1 has been created.", "order_agent", ORDER)
    assert out[0] == "Show my order details"
    assert len(out) == 3
    assert all(pb.is_valid(c) for c in out)


def test_model_failure_still_yields_three_chips(monkeypatch):
    _fake_genai(monkeypatch, error=RuntimeError("boom"))
    out = suggestions.generate_suggestions("hi", "What email and phone should we use?", "discovery_agent", CUSTOMER)
    assert out[0] == "You can reach me at [email] or [phone]"
    assert len(out) == 3


def test_faq_mid_quote_gets_quote_chips_not_discovery(monkeypatch):
    _fake_genai(monkeypatch, text="not json")
    out = suggestions.generate_suggestions("cancellation policy?", "You can cancel within 30 days.", "faq_agent", QUOTE)
    assert out == pb.PLAYBOOK["quote"]
    assert not any("company name" in c for c in out)


def test_empty_reply_yields_nothing():
    assert suggestions.generate_suggestions("hi", "   ", "faq_agent", {}) == []


# --- review fixes (returning-customer-resume) ------------------------------------

SESSION_QUOTE_REPLY = (
    "This quote is now active and saved to your account. Would you like to:\n"
    "1.  **See pricing for a longer term?** (We offer additional discounts for 24 or 36-month commitments).\n"
    "2.  **Add other services?** (We also have Voice, SD-WAN, and Mobile options available at your location).\n"
    "3.  **Proceed with this quote?** (I can help you move forward to the ordering stage)."
)


def test_location_mentioned_in_offer_is_not_an_address_request():
    assert "[street" not in (pb.reply_template(SESSION_QUOTE_REPLY) or "")
    out = pb.finalize([], SESSION_QUOTE_REPLY, "quote")
    assert not any("[street" in c for c in out)


def test_this_location_question_gets_confirmation_chip():
    reply = "Welcome back! I found **Acme** at 1 A St, Philadelphia PA 19103. Are you calling about service for this location?"
    assert pb.reply_template(reply) == "Yes, service at this address"


def test_returning_active_service_stage():
    state = {**CUSTOMER, "returning_customer_context": {"customer_id": "C1", "status": "active_service"}}
    assert pb.journey_stage(state) == "returning_active"
    with_quote = {**state, "offer_context": {"offer_id": "OFF-1"}}
    assert pb.journey_stage(with_quote) == "quote"
    other = {**CUSTOMER, "returning_customer_context": {"customer_id": "ZZ", "status": "active_service"}}
    assert pb.journey_stage(other) == "address"
