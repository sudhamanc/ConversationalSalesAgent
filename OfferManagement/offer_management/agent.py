"""
Offer Management Agent - deterministic quote and discount engine (A2A service).

All pricing math lives in ``tools/pricing_tools.py``; the model only chooses
tools and formats their output.
"""

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import OFFER_MANAGEMENT_AGENT_INSTRUCTION, OFFER_MANAGEMENT_SHORT_DESCRIPTION
from .tools.pricing_tools import (
    find_best_bundle_offer,
    generate_offer_quote,
    get_existing_quotes,
    get_quote_details,
)

AGENT_NAME = "offer_management_agent"


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    """Build the offer_management_agent."""
    return Agent(
        name=AGENT_NAME,
        model=model or model_name(),
        description=OFFER_MANAGEMENT_SHORT_DESCRIPTION,
        static_instruction=OFFER_MANAGEMENT_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=[
            find_best_bundle_offer,
            generate_offer_quote,
            get_existing_quotes,
            get_quote_details,
        ],
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        generate_content_config=generate_config(temperature=0.0, max_output_tokens=2048),
    )


root_agent = build_agent()
