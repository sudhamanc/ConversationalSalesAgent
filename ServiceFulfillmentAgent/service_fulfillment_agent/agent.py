"""
Service Fulfillment Agent - POST-ORDER installation scheduling and service activation.

This agent is a deterministic, tool-based agent that:
1. Schedules installation appointments
2. Coordinates equipment provisioning
3. Dispatches technicians
4. Activates services
5. Tracks installation completion

SEPARATION OF CONCERNS:
- OrderAgent handles PRE-FULFILLMENT: cart management, order creation, contract generation
- ServiceFulfillmentAgent (THIS) handles POST-ORDER: installation, equipment, activation

It is designed to be integrated into the Super Agent orchestration system
as a sub-agent for the Fulfillment cluster.
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

from .prompts import SERVICE_FULFILLMENT_AGENT_INSTRUCTION, SERVICE_FULFILLMENT_SHORT_DESCRIPTION
from .tools.scheduling_tools import (
    check_availability,
    schedule_installation,
    reschedule_appointment,
    cancel_appointment,
)
from .tools.equipment_tools import (
    provision_equipment,
    track_equipment,
    verify_equipment_delivery,
)
from .tools.installation_tools import (
    dispatch_technician,
    update_installation_status,
    complete_installation,
)
from .tools.activation_tools import (
    activate_service,
    run_service_tests,
    get_service_details,
)
# Note: order_tools removed - order creation is now handled by OrderAgent
# from .tools.order_tools import (
#     create_order,
#     get_order_status,
#     update_order_status,
# )
from .utils.logger import get_logger

# Load environment variables
# Note: load_dotenv() removed - sub-agents should not load root .env to avoid conflicts
# load_dotenv()

logger = get_logger(__name__)

# Agent configuration from environment
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
# AGENT_NAME no longer needed - using hardcoded name for sub-agent consistency

logger.info(f"Initializing Service Fulfillment Agent with model: {GEMINI_MODEL}")


# Create the service fulfillment agent following ADK pattern
service_fulfillment_agent = Agent(
    name="service_fulfillment_agent",  # Hardcoded to avoid .env conflicts when loaded as sub-agent
    model=GEMINI_MODEL,
    instruction=SERVICE_FULFILLMENT_AGENT_INSTRUCTION,
    description=SERVICE_FULFILLMENT_SHORT_DESCRIPTION,
    tools=[
        # Scheduling tools
        check_availability,
        schedule_installation,
        reschedule_appointment,
        cancel_appointment,
        # Equipment tools
        provision_equipment,
        track_equipment,
        verify_equipment_delivery,
        # Installation tools
        dispatch_technician,
        update_installation_status,
        complete_installation,
        # Activation tools
        activate_service,
        run_service_tests,
        # NOTE: Order creation tools removed - now handled by OrderAgent
        # update_order_status tool also removed - OrderAgent handles all order status management
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,  # Deterministic - critical for fulfillment accuracy
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
    Public accessor for the service fulfillment agent.
    
    This function is used when integrating the agent as a sub-agent
    in the Super Agent orchestration system.
    
    Returns:
        Configured service fulfillment Agent instance
    """
    return service_fulfillment_agent


logger.info(f"Service Fulfillment Agent initialized: {service_fulfillment_agent.name}")
