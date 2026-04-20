"""
Offer Management Agent - deterministic quote and discount engine.
"""

import os
from google.adk.agents import Agent
from google.genai import types

from .prompts import OFFER_MANAGEMENT_AGENT_INSTRUCTION, OFFER_MANAGEMENT_SHORT_DESCRIPTION
from .tools.pricing_tools import find_best_bundle_offer, generate_offer_quote, save_quote, get_saved_quote
from .utils.logger import get_logger

logger = get_logger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL")
if not GEMINI_MODEL:
    raise ValueError("GEMINI_MODEL environment variable is not set")

logger.info(f"Initializing Offer Management Agent with model: {GEMINI_MODEL}")

offer_management_agent = Agent(
    name="offer_management_agent",
    model=GEMINI_MODEL,
    instruction=OFFER_MANAGEMENT_AGENT_INSTRUCTION,
    description=OFFER_MANAGEMENT_SHORT_DESCRIPTION,
    tools=[
        find_best_bundle_offer,
        generate_offer_quote,
        save_quote,
        get_saved_quote,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=2048,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
        ],
    ),
)


def get_agent() -> Agent:
    return offer_management_agent


logger.info(
    f"Offer Management Agent initialized: {offer_management_agent.name} with {len(offer_management_agent.tools)} tools"
)
