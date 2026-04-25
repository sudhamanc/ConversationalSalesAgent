"""
Product Agent - deterministic catalog/specification agent.

This agent:
1. Retrieves product specifications from structured catalog tools
2. Compares products and suggests alternatives
3. Provides technical fit guidance (non-commercial)

It is designed to be integrated into the Super Agent orchestration system
as a sub-agent for the Configuration cluster.
"""

import os
from google.adk.agents import Agent
from google.genai import types

from .prompts import PRODUCT_AGENT_INSTRUCTION, PRODUCT_SHORT_DESCRIPTION
from .tools.product_tools import (
    list_available_products,
    get_product_by_id,
    search_products_by_criteria,
    get_product_categories,
)
from .tools.comparison_tools import (
    compare_products,
    suggest_alternatives,
    get_best_value_product,
)
from .tools.rag_tools import search_product_knowledge
from .utils.logger import get_logger

# Load environment variables
# Note: load_dotenv() removed - sub-agents should not load root .env to avoid conflicts
# load_dotenv()

logger = get_logger(__name__)

# Agent configuration from environment
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
# AGENT_NAME no longer needed - using hardcoded name for sub-agent consistency

logger.info(f"Initializing Product Agent with model: {GEMINI_MODEL}")


# Create the product agent following ADK pattern
product_agent = Agent(
    name="product_agent",  # Hardcoded to avoid .env conflicts when loaded as sub-agent
    model=GEMINI_MODEL,
    instruction=PRODUCT_AGENT_INSTRUCTION,
    description=PRODUCT_SHORT_DESCRIPTION,
    tools=[
        # Product catalog tools - structured data
        list_available_products,
        get_product_by_id,
        search_products_by_criteria,
        get_product_categories,
        # Comparison tools
        compare_products,
        suggest_alternatives,
        get_best_value_product,
        # RAG knowledge base — narrative Q&A, SLAs, use cases, install details
        search_product_knowledge,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,  # Deterministic - no creativity needed for factual responses
        top_p=0.2,        # Low sampling for determinism
        top_k=20,         # Restrict token selection
        max_output_tokens=2048,  # Sufficient for detailed product explanations
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
    Public accessor for the product agent.
    
    This function is used when integrating the agent as a sub-agent
    in the Super Agent orchestration system.
    
    Returns:
        Configured product Agent instance
    """
    return product_agent


logger.info(f"Product Agent initialized: {product_agent.name}")
