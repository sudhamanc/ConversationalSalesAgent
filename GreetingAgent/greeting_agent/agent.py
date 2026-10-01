"""Greeting agent service - handles greetings and introductions (Connectivity Max phone-script greeting)."""

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name
from sales_common.models import agent_model
from sales_common.context import import_forwarded_context
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import GREETING_AGENT_INSTRUCTION, GREETING_SHORT_DESCRIPTION


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    """Build the greeting_agent (no tools)."""
    return Agent(
        name="greeting_agent",
        model=model or agent_model(),
        description=GREETING_SHORT_DESCRIPTION,
        static_instruction=GREETING_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=[],
        before_agent_callback=[import_forwarded_context],
        generate_content_config=generate_config(temperature=0.7, max_output_tokens=2048),
    )


root_agent = build_agent()
