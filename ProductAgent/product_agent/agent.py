"""
Product Agent - Info/RAG agent for product specifications & documentation.

This agent is an information retrieval agent that:
1. Queries product documentation via RAG (ChromaDB)
2. Provides technical specifications and features
3. Compares products and suggests alternatives
4. Answers product-related questions with zero hallucination

It is designed to be integrated into the Super Agent orchestration system
as a sub-agent for the Configuration cluster.
"""

import os
from google.adk.agents import Agent
from google.genai import types
from dotenv import load_dotenv

from .prompts import PRODUCT_AGENT_INSTRUCTION, PRODUCT_SHORT_DESCRIPTION
from .tools.rag_tools import (
    query_product_documentation,
    search_technical_specs,
    get_product_features,
    get_sla_terms,
)
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
from .utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# Agent configuration from environment
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
AGENT_NAME = os.getenv("AGENT_NAME", "product_agent")

logger.info(f"Initializing Product Agent with model: {GEMINI_MODEL}")


# Create the product agent following ADK pattern
product_agent = Agent(
    name=AGENT_NAME,
    model=GEMINI_MODEL,
    instruction=PRODUCT_AGENT_INSTRUCTION,
    description=PRODUCT_SHORT_DESCRIPTION,
    tools=[
        # RAG tools - primary source of truth
        query_product_documentation,
        search_technical_specs,
        get_product_features,
        get_sla_terms,
        # Product catalog tools - structured data
        list_available_products,
        get_product_by_id,
        search_products_by_criteria,
        get_product_categories,
        # Comparison tools
        compare_products,
        suggest_alternatives,
        get_best_value_product,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,  # Low temperature for accurate, factual responses
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


logger.info(f"Product Agent initialized: {AGENT_NAME}")
