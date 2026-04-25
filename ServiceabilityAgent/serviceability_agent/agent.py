"""
Serviceability Agent - PRE-SALE address validation & network infrastructure verification.

This agent is a deterministic, tool-based agent that:
1. Validates customer addresses
2. Checks GIS/Coverage Map for network infrastructure availability
3. Returns infrastructure details, network elements, and speed capabilities (NOT product plans/pricing)

It is designed to be integrated into the Super Agent orchestration system
as a sub-agent for the Configuration cluster.
"""

import os
from google.adk.agents import Agent
from google.genai import types

from .prompts import SERVICEABILITY_AGENT_INSTRUCTION, SERVICEABILITY_SHORT_DESCRIPTION
from .tools.address_tools import (
    validate_and_parse_address,
    normalize_address,
    extract_zip_code,
)
from .tools.gis_tools import (
    check_service_availability,
    get_infrastructure_by_technology,
    get_coverage_zones,
)
from .utils.logger import get_logger

# Load environment variables
# Note: load_dotenv() removed - sub-agents should not load root .env to avoid conflicts
# load_dotenv()

logger = get_logger(__name__)

# Agent configuration from environment
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
if not GEMINI_MODEL:
    raise ValueError("GEMINI_MODEL environment variable is not set")
# AGENT_NAME no longer needed - using hardcoded name for sub-agent consistency

logger.info(f"Initializing Serviceability Agent with model: {GEMINI_MODEL}")


# Create the serviceability agent following ADK pattern
serviceability_agent = Agent(
    name="serviceability_agent",  # Hardcoded to avoid .env conflicts when loaded as sub-agent
    model=GEMINI_MODEL,
    instruction=SERVICEABILITY_AGENT_INSTRUCTION,
    description=SERVICEABILITY_SHORT_DESCRIPTION,
    tools=[
        # Address validation tools
        validate_and_parse_address,
        normalize_address,
        extract_zip_code,
        # GIS/Coverage tools - return infrastructure details, not products
        check_service_availability,
        get_infrastructure_by_technology,
        get_coverage_zones,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,  # Deterministic - no creativity needed
        max_output_tokens=2048,  # Sufficient for detailed responses
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
    """
    Public accessor for the serviceability agent.
    
    This function is used when integrating the agent as a sub-agent
    in the Super Agent orchestration system.
    
    Returns:
        Configured serviceability Agent instance
    """
    return serviceability_agent


logger.info(f"Serviceability Agent initialized: {serviceability_agent.name}")
