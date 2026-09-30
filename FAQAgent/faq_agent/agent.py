"""FAQ agent service - answers common questions about products, contracts, SLAs, installation, support and policies as a phone script."""

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name
from sales_common.context import import_forwarded_context
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import FAQ_AGENT_INSTRUCTION, FAQ_SHORT_DESCRIPTION


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    """Build the faq_agent (no tools)."""
    return Agent(
        name="faq_agent",
        model=model or model_name(),
        description=FAQ_SHORT_DESCRIPTION,
        static_instruction=FAQ_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=[],
        before_agent_callback=[import_forwarded_context],
        generate_content_config=generate_config(temperature=0.7, max_output_tokens=2048),
    )


root_agent = build_agent()
