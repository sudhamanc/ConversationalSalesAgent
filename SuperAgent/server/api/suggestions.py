"""Next-step suggestion chips: the customer's likely next messages (Gemini + deterministic playbook)."""

import json
import logging
import os
import re

from api import suggestion_playbook as playbook
from sales_common import telemetry
from utils.logger import get_logger

logger = get_logger(__name__)


def _record_usage(span, response, response_text: str) -> None:
    """Output and token counts on the suggestions generation span (no-op span when tracing is off)."""
    span.set_attribute("output.value", response_text)
    usage = getattr(response, "usage_metadata", None)
    for attr, field in (
        ("llm.token_count.prompt", "prompt_token_count"),
        ("llm.token_count.completion", "candidates_token_count"),
        ("llm.token_count.total", "total_token_count"),
    ):
        value = getattr(usage, field, None) if usage is not None else None
        if isinstance(value, int):
            span.set_attribute(attr, value)


def _parse_suggestion_payload(raw_text: str) -> list[str]:
    """Parse the JSON suggestions payload into a raw list (validation happens in ``finalize``)."""
    if not raw_text:
        return []

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return []

    candidates = []
    if isinstance(parsed, list):
        candidates = parsed
    elif isinstance(parsed, dict):
        suggestions = parsed.get("suggestions")
        if isinstance(suggestions, list):
            candidates = suggestions

    return [" ".join(str(item).split()) for item in candidates if str(item).strip()]


def _reply_excerpt(assistant_message: str) -> str:
    """Head and tail of the agent reply, so its closing question is always included."""
    text = assistant_message.strip()
    if len(text) <= 700:
        return text
    return f"{text[:300]} … {text[-400:]}"


def build_prompt(user_message: str, assistant_message: str, author: str | None, state=None) -> str:
    """Customer-voice suggestion prompt (see ``suggestion_playbook`` for the contract)."""
    stage = playbook.journey_stage(state)
    facts = playbook.journey_facts(state)
    template = playbook.reply_template(assistant_message)
    examples = "\n".join(f"  - {chip}" for chip in playbook.PLAYBOOK[stage])
    reply_rule = (
        f"- The agent just asked the customer for something. Suggestion 1 MUST answer it, "
        f"as a fill-in like: {template}\n"
        if template
        else "- If the agent asked a question, suggestion 1 MUST answer it.\n"
    )
    return (
        "You are a JSON API. Output ONLY a JSON object, nothing else.\n"
        "A business customer is chatting with a telecom sales agent. Write the 3 messages the CUSTOMER "
        "is most likely to send next. The customer clicks one and it is sent as THEIR message.\n"
        'Output: {"suggestions": ["message1", "message2", "message3"]}\n'
        "Rules:\n"
        "- Write in the customer's voice: first person (I, we, our, my), speaking TO the agent.\n"
        "- NEVER write what the agent would say: no questions about the customer's company, address or "
        'needs, no "your company", no "the customer", no back-office actions.\n'
        f"{reply_rule}"
        "- Where the customer must supply their own details, use short [bracketed placeholders] "
        "such as [company name], [street, city, state ZIP], [email], [phone], [date], [number].\n"
        "- Never ask to give information listed as known. Move the customer toward what is missing.\n"
        "- Each message under 80 characters; no real names, addresses or IDs; no filler like \"Continue\".\n"
        "Bad -> good:\n"
        '  "Tell me about your company and location" -> "We\'re [company name], located at [street, city, state ZIP]"\n'
        '  "Send order confirmation to customer" -> "Email me the order confirmation"\n'
        '  "Continue" -> "I\'d like to go ahead with this quote"\n'
        f"Journey stage: {stage} ({playbook.STAGE_HINTS[stage]})\n"
        f"Known: {', '.join(facts['known']) or 'nothing yet'}\n"
        f"Missing: {', '.join(facts['missing']) or 'nothing'}\n"
        f"Typical customer messages at this stage:\n{examples}\n"
        f"Agent: {author or 'agent'}\n"
        f"Customer said: {user_message[:200]}\n"
        f"Agent reply: {_reply_excerpt(assistant_message)}\n"
    )


def generate_suggestions(
    user_message: str, assistant_message: str, author: str | None, state=None
) -> list[str]:
    """Three customer-voice next messages for this journey stage.

    The LLM proposes; ``suggestion_playbook.finalize`` enforces the contract and tops up
    from the stage playbook, so a model failure still yields suggestions.
    """
    if not assistant_message.strip():
        return []

    stage = playbook.journey_stage(state)
    candidates: list[str] = []
    try:
        from google import genai
        from google.genai import types as genai_types
        client = genai.Client()
        prompt = build_prompt(user_message, assistant_message, author, state)

        # Use configured model for suggestions; disable thinking to avoid
        # budget consumption, and bump token limit for reliable JSON output.
        model = os.environ["GEMINI_MODEL"]
        # Outside ADK, so not auto-instrumented: record it as a generation on the turn's trace.
        with telemetry.get_tracer("gateway.suggestions").start_as_current_span(
            "generate_suggestions",
            attributes={"openinference.span.kind": "LLM", "llm.model_name": model, "input.value": prompt},
        ) as span:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1024,
                    thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
                ),
            )
            response_text = getattr(response, "text", "") or ""
            _record_usage(span, response, response_text)

        # Try direct parse; fall back to extracting JSON from markdown/preamble
        candidates = _parse_suggestion_payload(response_text)
        if not candidates:
            match = re.search(r'\{[^{}]*"suggestions"\s*:\s*\[.*?\]\s*\}', response_text, re.DOTALL)
            if match:
                candidates = _parse_suggestion_payload(match.group())
        if not candidates:
            logger.warning("Dynamic suggestions: LLM returned unparseable response: %s", response_text[:200])
    except Exception as error:
        logger.warning("Dynamic suggestion generation failed: %s", error)

    result = playbook.finalize(candidates, assistant_message, stage)
    logger.info("Suggestions (stage=%s): %s", stage, result)
    return result
