"""
Order Agent - Order lifecycle management and contract generation.

This agent is a deterministic, tool-based agent that:
1. Manages shopping cart (add, remove, clear items)
2. Creates orders with auto-generated customer IDs
3. Modifies orders (before confirmation)
4. Generates service contracts
5. Updates order status through lifecycle
6. Cancels orders when needed

It is designed to be integrated into the Super Agent orchestration system
as a sub-agent for the Transaction cluster.

SEPARATION OF CONCERNS:
- OrderAgent: Cart management, order creation, contract generation (PRE-FULFILLMENT)
- ServiceFulfillmentAgent: Installation scheduling, provisioning, activation (POST-ORDER)
"""

import os
from google.adk.agents import Agent
from google.genai import types

from .prompts import ORDER_AGENT_INSTRUCTION, ORDER_SHORT_DESCRIPTION
from .tools.cart_tools import (
    create_cart,
    add_to_cart,
    remove_from_cart,
    get_cart,
    clear_cart,
)
from .tools.order_tools import (
    create_order,
    update_order_status,
    get_order,
    modify_order,
    generate_contract,
    cancel_order,
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

logger.info(f"Initializing Order Agent with model: {GEMINI_MODEL}")


# Create the order agent following ADK pattern
order_agent = Agent(
    name="order_agent",  # Hardcoded to avoid .env conflicts when loaded as sub-agent
    model=GEMINI_MODEL,
    instruction=ORDER_AGENT_INSTRUCTION,
    description=ORDER_SHORT_DESCRIPTION,
    tools=[
        # Cart management tools
        create_cart,
        add_to_cart,
        remove_from_cart,
        get_cart,
        clear_cart,
        # Order management tools
        create_order,
        update_order_status,
        get_order,
        modify_order,
        generate_contract,
        cancel_order,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,  # Deterministic - no creativity needed for order management
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
    Public accessor for the order agent.
    
    This function is used when integrating the agent as a sub-agent
    in the Super Agent orchestration system.
    
    Returns:
        Configured order Agent instance
    """
    return order_agent


logger.info(f"Order Agent '{order_agent.name}' initialized with {len(order_agent.tools)} tools")
