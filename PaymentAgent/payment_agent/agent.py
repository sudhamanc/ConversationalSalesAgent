"""
Payment Agent - Payment processing and billing management.

This agent is a deterministic, tool-based agent that:
1. Validates payment methods (credit cards, ACH, etc.)
2. Processes payments securely
3. Performs business credit checks
4. Generates invoices and manages billing

It is designed to be integrated into the Super Agent orchestration system
as a sub-agent for the Payment cluster.
"""

import os
from dotenv import load_dotenv

# Try importing Google ADK dependencies (may not be available in test environments)
try:
    from google.adk.agents import Agent
    from google.genai import types
    HAS_GOOGLE_ADK = True
except (ImportError, ModuleNotFoundError):
    HAS_GOOGLE_ADK = False
    print("WARNING: Google ADK not available. Using mock agent for testing.")
    # Mock Agent class for testing
    class Agent:
        def __init__(self, **kwargs):
            self.name = kwargs.get('name', 'mock_agent')
            self.model = kwargs.get('model', 'mock_model')
            self.instruction = kwargs.get('instruction', '')
            self.description = kwargs.get('description', '')
            self.tools = kwargs.get('tools', [])
        
        def run(self, message: str) -> str:
            return f"Mock response for: {message}"
    
    class types:
        class GenerateContentConfig:
            def __init__(self, **kwargs):
                pass
        class SafetySetting:
            def __init__(self, **kwargs):
                pass
        class HarmCategory:
            HARM_CATEGORY_DANGEROUS_CONTENT = "dangerous"
            HARM_CATEGORY_HARASSMENT = "harassment"
            HARM_CATEGORY_HATE_SPEECH = "hate_speech"
            HARM_CATEGORY_SEXUALLY_EXPLICIT = "sexually_explicit"
        class HarmBlockThreshold:
            BLOCK_LOW_AND_ABOVE = "block_low"
            BLOCK_MEDIUM_AND_ABOVE = "block_medium"

from .prompts import PAYMENT_AGENT_INSTRUCTION, PAYMENT_SHORT_DESCRIPTION
from .tools.payment_tools import (
    validate_payment_method,
    process_payment,
    get_payment_methods,
    tokenize_payment_method,
)
from .tools.credit_tools import (
    check_business_credit,
    get_credit_report,
)
from .tools.billing_tools import (
    generate_invoice,
    get_payment_history,
    setup_payment_plan,
)
from .utils.logger import get_logger

# Load environment variables
# Note: load_dotenv() removed - sub-agents should not load root .env to avoid conflicts
# load_dotenv()

logger = get_logger(__name__)

# Agent configuration from environment
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
# AGENT_NAME no longer needed - using hardcoded name for sub-agent consistency

logger.info(f"Initializing Payment Agent with model: {GEMINI_MODEL}")


# Create the payment agent following ADK pattern
payment_agent = Agent(
    name="payment_agent",  # Hardcoded to avoid .env conflicts when loaded as sub-agent
    model=GEMINI_MODEL,
    instruction=PAYMENT_AGENT_INSTRUCTION,
    description=PAYMENT_SHORT_DESCRIPTION,
    tools=[
        # Payment processing tools
        validate_payment_method,
        process_payment,
        get_payment_methods,
        tokenize_payment_method,
        # Credit check tools
        check_business_credit,
        get_credit_report,
        # Billing tools
        generate_invoice,
        get_payment_history,
        setup_payment_plan,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,  # Deterministic - critical for payment accuracy
        top_p=0.1,        # Low sampling for determinism
        top_k=10,         # Restrict token selection
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
    Public accessor for the payment agent.
    
    This function is used when integrating the agent as a sub-agent
    in the Super Agent orchestration system.
    
    Returns:
        Configured payment Agent instance
    """
    return payment_agent


logger.info(f"Payment Agent initialized: {payment_agent.name}")
