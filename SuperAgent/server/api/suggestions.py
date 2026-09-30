"""Next-step suggestion chips (direct Gemini call; best effort)."""

import json
import logging
import os
import re

from utils.logger import get_logger

logger = get_logger(__name__)


def _parse_suggestion_payload(raw_text: str) -> list[str]:
    """Parse JSON suggestions payload into a cleaned list."""
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

    cleaned: list[str] = []
    for item in candidates:
        text = str(item).strip()
        if not text:
            continue
        # Keep suggestions editable and generic; avoid over-specific hard values.
        text = text.replace("\n", " ").strip()
        if text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= 3:
            break

    return cleaned


def generate_suggestions(user_message: str, assistant_message: str, author: str | None) -> list[str]:
    """Generate sales-flow-aware next-step suggestions using LLM; return empty list on failure."""
    if not assistant_message.strip():
        return []

    # Sales flow context per agent — guides LLM toward domain-appropriate suggestions
    _AGENT_FLOW_HINTS = {
        "greeting_agent": "User just started. Suggest: introducing their company/location, asking about products, checking serviceability.",
        "discovery_agent": "Company info was gathered. Suggest: check serviceability for address, ask about product needs, provide budget/timeline.",
        "serviceability_agent": "Address was validated. Suggest: view available products, get technical specs, request a pricing quote.",
        "product_agent": "Products were shown. Suggest: generate a pricing quote, compare products, ask about term discounts (12/24/36 month).",
        "offer_management_agent": "A pricing quote was generated. Suggest: proceed with this quote, show different term length (e.g. 24 or 36 month), add/remove products and requote.",
        "order_agent": "Order was created. Suggest: schedule installation, review order details, proceed to payment.",
        "payment_agent": "Payment was processed. Suggest: schedule installation, send payment confirmation, show order status.",
        "service_fulfillment_agent": "Installation/fulfillment in progress. Suggest: simulate install day, activate service, show fulfillment status.",
        "customer_communication_agent": "Notification was sent. Suggest: show notification history, resend confirmation, send status update.",
        "faq_agent": "FAQ was answered. Suggest: ask about products, check serviceability, get a pricing quote.",
    }

    flow_hint = _AGENT_FLOW_HINTS.get(author or "", "Suggest logical next steps in a B2B telecom sales conversation.")

    try:
        from google import genai
        from google.genai import types as genai_types
        client = genai.Client()
        prompt = (
            "You are a JSON API. Output ONLY a JSON object, nothing else.\n"
            "Generate 3 short next-step suggestions for a B2B telecom sales chat.\n"
            "Output: {\"suggestions\": [\"action1\", \"action2\", \"action3\"]}\n"
            "Rules:\n"
            "- Each suggestion under 60 chars\n"
            "- Suggestions must be specific to the current sales stage\n"
            "- No customer names, addresses, or IDs\n"
            "- Actionable and directly useful as clickable buttons\n"
            f"Sales context: {flow_hint}\n"
            f"Agent: {author or 'agent'}\n"
            f"User said: {user_message[:200]}\n"
            f"Agent response (excerpt): {assistant_message[:400]}\n"
        )

        # Use configured model for suggestions; disable thinking to avoid
        # budget consumption, and bump token limit for reliable JSON output.
        response = client.models.generate_content(
            model=os.environ["GEMINI_MODEL"],
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1024,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )

        response_text = getattr(response, "text", "") or ""
        # Try direct parse; fall back to extracting JSON from markdown/preamble
        result = _parse_suggestion_payload(response_text)
        if not result:
            match = re.search(r'\{[^{}]*"suggestions"\s*:\s*\[.*?\]\s*\}', response_text, re.DOTALL)
            if match:
                result = _parse_suggestion_payload(match.group())
        if result:
            logger.info("Dynamic suggestions generated: %s", result)
        else:
            logger.warning("Dynamic suggestions: LLM returned unparseable response: %s", response_text[:200])
        return result
    except Exception as error:
        logger.warning("Dynamic suggestion generation failed: %s", error)
        return []
