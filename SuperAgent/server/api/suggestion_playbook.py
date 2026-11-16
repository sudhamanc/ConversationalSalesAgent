"""Customer-voice suggestion playbook (deterministic; no LLM).

Suggestion chips are clicked by the *customer* and pre-fill the chat input, so
every chip is a first-person message the customer would send. This module owns
the chip contract shared by the LLM prompt and the fallback:

- ``journey_stage(state)``: one stage derived from the gateway session state.
- ``PLAYBOOK[stage]``: customer-voice request chips for that stage.
- ``reply_template(reply)``: a fill-in reply chip when the agent asked for something.
- ``finalize(candidates, reply, stage)``: validate, enforce the reply chip, top up to 3.

Spec: openspec/specs/conversation-orchestration ("Suggestions are customer-voice
and journey-aware").
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from super_agent.workflow import PAYMENT_DONE_STATUSES, journey_flags

MAX_SUGGESTIONS = 3
MAX_CHARS = 80

PLAYBOOK: dict[str, list[str]] = {
    "new": [
        "We're [company name], located at [street, city, state ZIP]",
        "I need business internet for my office",
        "What plans do you offer for small businesses?",
    ],
    "address": [
        "Our service address is [street, city, state ZIP]",
        "We have [number] employees and need [internet/voice/both]",
        "What plans do you offer for small businesses?",
    ],
    "products": [
        "Show me the plans available at my address",
        "Which plan fits [number] employees?",
        "Quote me [plan] on a [12/24/36]-month term",
    ],
    "not_serviceable": [
        "Check a different address: [street, city, state ZIP]",
        "What options do I have at this location?",
        "Let me know when service reaches my area",
    ],
    "quote": [
        "I'd like to go ahead with this quote",
        "Requote this on a [12/24/36]-month term",
        "Remove [product] and requote",
    ],
    "schedule": [
        "Schedule my installation for [date]",
        "What installation dates are available?",
        "Show my order details",
    ],
    "payment": [
        "I'm ready to pay for my order",
        "What payment methods do you accept?",
        "Show my order total",
    ],
    "provisioning": [
        "Simulate my install day",
        "Show my order details",
        "Email me the installation confirmation",
    ],
}

# Short descriptions the LLM sees for each stage.
STAGE_HINTS: dict[str, str] = {
    "new": "Customer has not introduced their business yet.",
    "address": "Business is known; service address/needs not yet checked.",
    "products": "Address is serviceable; customer is choosing plans, no quote yet.",
    "not_serviceable": "Address is NOT serviceable.",
    "quote": "A quote exists; customer may accept, change term, or adjust products.",
    "schedule": "Order created; installation not scheduled yet.",
    "payment": "Installation scheduled; order not paid yet.",
    "provisioning": "Order paid; installation/activation in progress.",
}


def journey_stage(state: Mapping[str, Any] | None) -> str:
    """Derive the customer's journey stage from gateway session state."""
    state = state or {}
    flags = journey_flags(state)
    if str(flags["payment_status"] or "").lower() in PAYMENT_DONE_STATUSES:
        return "provisioning"
    if flags["order_created"]:
        return "payment" if flags["installation_scheduled"] else "schedule"
    if flags["quote_ready"]:
        return "quote"
    if flags["serviceability_checked"]:
        return "products" if flags["serviceable"] else "not_serviceable"
    if flags["customer_identified"]:
        return "address"
    return "new"


def journey_facts(state: Mapping[str, Any] | None) -> dict[str, list[str]]:
    """Human-readable known / missing facts for the prompt (no names or IDs)."""
    state = state or {}
    flags = journey_flags(state)
    customer = state.get("customer_context") or {}
    known, missing = [], []
    (known if flags["customer_identified"] else missing).append("company")
    (known if (customer.get("address") or {}).get("zip_code") else missing).append("service address")
    if flags["serviceability_checked"]:
        known.append("serviceable" if flags["serviceable"] else "not serviceable")
    (known if flags["quote_ready"] else missing).append("quote")
    (known if flags["order_created"] else missing).append("order")
    (known if flags["installation_scheduled"] else missing).append("installation date")
    paid = str(flags["payment_status"] or "").lower() in PAYMENT_DONE_STATUSES
    (known if paid else missing).append("payment")
    return {"known": known, "missing": missing}


# --- reply templates -------------------------------------------------------

_ASK_RE = re.compile(
    r"\?|\b(please (provide|share|confirm|enter|send|tell)|could you (provide|share|tell|confirm)|"
    r"may i have|let me know|i'll need|i will need|i need your)\b",
    re.IGNORECASE,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.?!])\s+|\n+")

# Ordered: the first matching topic wins.
_REPLY_TOPICS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(card|cvv|expir|payment (details|method|information)|routing|ach)\b", re.I),
     "My card is [card number], exp [MM/YY], CVV [CVV]"),
    (re.compile(r"\b(e-?mail|phone|contact)\b", re.I),
     "You can reach me at [email] or [phone]"),
    (re.compile(r"\b(date|time slot|appointment|schedul\w*|availability|morning|afternoon)\b", re.I),
     "[date] in the [morning/afternoon] works for me"),
    (re.compile(r"\b(company name|business name|name of your (company|business)|who you are)\b", re.I),
     "We're [company name], located at [street, city, state ZIP]"),
    (re.compile(r"\b(address|zip|location|street)\b", re.I),
     "Our address is [street, city, state ZIP]"),
    (re.compile(r"\b(employees|staff|users|bandwidth|speed|needs?|looking for|use case|timeline|budget)\b", re.I),
     "We have [number] employees and need [internet/voice/both]"),
    (re.compile(r"\b(anything else|any other|add (any|more|another))\b", re.I),
     "No, that's everything. Let's proceed"),
    (re.compile(r"\b(proceed|confirm|go ahead|would you like|shall i|should i)\b", re.I),
     "Yes, let's go ahead"),
]

_PLACEHOLDER_RE = re.compile(r"\[[^\[\]]+\]")


def _tail(reply: str, chars: int = 400) -> str:
    return (reply or "")[-chars:]


def ask_sentences(reply: str) -> list[str]:
    """Sentences near the end of the reply that ask the customer for something."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(_tail(reply)) if s.strip()]
    return [s for s in sentences if _ASK_RE.search(s)]


def asks_customer(reply: str) -> bool:
    """True when the end of the agent reply asks the customer for something."""
    return bool(ask_sentences(reply))


def reply_template(reply: str) -> str | None:
    """Fill-in chip answering what the agent just asked for, if anything."""
    asks = " ".join(ask_sentences(reply))
    if not asks:
        return None
    for pattern, template in _REPLY_TOPICS:
        if pattern.search(asks):
            return template
    return None


# --- validation ------------------------------------------------------------

_REJECT_RES = [
    re.compile(r"\byour (company|business|address|location|name|email|phone|employees|needs)\b", re.I),
    re.compile(r"\btell me about your\b", re.I),
    re.compile(r"\b(the|to|notify|for) customers?\b", re.I),
    re.compile(r"^(continue|next|ok(ay)?|summary|give me a summary|show me (the )?next best step)\W*$", re.I),
]


def is_valid(chip: str) -> bool:
    """A chip satisfies the customer-voice contract."""
    text = chip.strip()
    if not text or len(text) > MAX_CHARS:
        return False
    return not any(rx.search(text) for rx in _REJECT_RES)


def is_template(chip: str) -> bool:
    return bool(_PLACEHOLDER_RE.search(chip))


def finalize(candidates: list[str], reply: str, stage: str) -> list[str]:
    """Validate candidates, put a reply chip first when the agent asked something, top up to 3."""
    out: list[str] = []

    def add(text: str) -> None:
        text = " ".join(str(text).split())
        if is_valid(text) and text.lower() not in {c.lower() for c in out}:
            out.append(text)

    for chip in candidates:
        add(chip)

    template = reply_template(reply)
    if template and is_template(template):
        # The agent asked for details: chip 1 must be a fill-in. Keep the LLM's if it put one first.
        if not (out and is_template(out[0])):
            out = [template] + [c for c in out if c.lower() != template.lower()]
    elif template and not out:
        # Yes/no question and nothing usable from the LLM.
        out.append(template)

    for chip in PLAYBOOK.get(stage, PLAYBOOK["new"]):
        if len(out) >= MAX_SUGGESTIONS:
            break
        add(chip)
    return out[:MAX_SUGGESTIONS]
