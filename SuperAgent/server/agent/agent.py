"""
Super Agent – the central orchestrator for the B2B Sales system.

Uses Google ADK Agent with Gemini as the backbone LLM.
Sub-agents are conditionally loaded based on configuration.
"""

import os

from google.adk.agents import Agent
from google.genai import types

from config import settings
from .prompts import ORCHESTRATOR_INSTRUCTION
from .sub_agents.greeting_agent import greeting_agent
from .sub_agents.product_agent import product_agent
from .sub_agents.faq_agent import faq_agent
from .tools.sales_tools import (
    check_service_availability,
    get_product_catalog,
    lookup_customer,
)

_safety = settings.safety
_model = settings.model


def _build_safety_settings() -> list[types.SafetySetting]:
    """Map config strings to google.genai safety setting objects."""
    mapping = {
        "BLOCK_NONE": types.HarmBlockThreshold.BLOCK_NONE,
        "BLOCK_LOW_AND_ABOVE": types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        "BLOCK_MEDIUM_AND_ABOVE": types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        "BLOCK_ONLY_HIGH": types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }
    return [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=mapping.get(_safety.dangerous_content, types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE),
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=mapping.get(_safety.harassment, types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE),
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=mapping.get(_safety.hate_speech, types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE),
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=mapping.get(_safety.sexually_explicit, types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE),
        ),
    ]


def _build_sub_agents() -> list[Agent]:
    """Return the list of active sub-agents based on config."""
    agents: list[Agent] = []
    if settings.agent.enable_sub_agents:
        agents.extend([greeting_agent, product_agent, faq_agent])
    return agents


root_agent = Agent(
    name=settings.agent.agent_name,
    model=_model.model_name,
    instruction=ORCHESTRATOR_INSTRUCTION,
    description=settings.agent.agent_description,
    sub_agents=_build_sub_agents(),
    tools=[check_service_availability, get_product_catalog, lookup_customer],
    generate_content_config=types.GenerateContentConfig(
        temperature=_model.temperature,
        top_p=_model.top_p,
        top_k=_model.top_k,
        max_output_tokens=_model.max_output_tokens,
        safety_settings=_build_safety_settings(),
    ),
)


def get_agent() -> Agent:
    """Public accessor used by the FastAPI app."""
    return root_agent
