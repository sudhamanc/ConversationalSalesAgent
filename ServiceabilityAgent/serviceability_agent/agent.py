"""
Serviceability Agent - PRE-SALE address validation & coverage verification.

This agent is a deterministic, tool-based agent that:
1. Validates customer addresses
2. Checks GIS/Coverage Map for service availability
3. Returns available products for serviceable locations

It is designed to be integrated into the Super Agent orchestration system
as a sub-agent for the Configuration cluster.
"""

import os
from google.adk.agents import Agent
from google.genai import types
from dotenv import load_dotenv

from .prompts import SERVICEABILITY_AGENT_INSTRUCTION, SERVICEABILITY_SHORT_DESCRIPTION
from .tools.address_tools import (
    validate_and_parse_address,
    normalize_address,
    extract_zip_code,
)
from .tools.gis_tools import (
    check_service_availability,
    get_products_by_technology,
    get_coverage_zones,
)
from .utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# Agent configuration from environment
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
AGENT_NAME = os.getenv("AGENT_NAME", "serviceability_agent")

logger.info(f"Initializing Serviceability Agent with model: {GEMINI_MODEL}")


# Create the serviceability agent following ADK pattern
serviceability_agent = Agent(
    name=AGENT_NAME,
    model=GEMINI_MODEL,
    instruction=SERVICEABILITY_AGENT_INSTRUCTION,
    description=SERVICEABILITY_SHORT_DESCRIPTION,
    tools=[
        # Address validation tools
        validate_and_parse_address,
        normalize_address,
        extract_zip_code,
        # GIS/Coverage tools
        check_service_availability,
        get_products_by_technology,
        get_coverage_zones,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,  # Deterministic - no creativity needed
        top_p=0.1,        # Low sampling for determinism
        top_k=10,         # Restrict token selection
        max_output_tokens=2048,  # Sufficient for detailed responses
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ],
    ),
)


def get_agent() -> Agent:
    """
    Public accessor for the serviceability agent.
    
    This function is used when integrating the agent as a sub-agent
    in the Super Agent orchestration system.
    
    Returns:
        Configured serviceability Agent instance
    """
    return serviceability_agent


logger.info(f"Serviceability Agent initialized: {AGENT_NAME}")
