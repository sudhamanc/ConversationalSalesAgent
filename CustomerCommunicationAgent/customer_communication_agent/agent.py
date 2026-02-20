"""
Customer Communication Agent - Automated notification system for order lifecycle events.
"""

import os
from google.adk.agents import Agent
from google.genai import types

from .prompts import (
    CUSTOMER_COMMUNICATION_AGENT_INSTRUCTION,
    CUSTOMER_COMMUNICATION_SHORT_DESCRIPTION,
)
from .tools import (
    send_order_confirmation,
    send_payment_notification,
    send_installation_reminder,
    send_service_activated_notification,
    send_abandoned_cart_reminder,
    send_order_status_update,
    get_notification_history,
)
from .utils.logger import logger

# Model configuration from environment
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
if not GEMINI_MODEL:
    raise ValueError("GEMINI_MODEL environment variable not set")

logger.info(f"Initializing CustomerCommunicationAgent with model: {GEMINI_MODEL}")

# Create CustomerCommunicationAgent with all notification tools
customer_communication_agent = Agent(
    name="customer_communication_agent",
    model=GEMINI_MODEL,
    instruction=CUSTOMER_COMMUNICATION_AGENT_INSTRUCTION,
    description=CUSTOMER_COMMUNICATION_SHORT_DESCRIPTION,
    tools=[
        # Order lifecycle notifications
        send_order_confirmation,
        send_payment_notification,
        send_installation_reminder,
        send_service_activated_notification,
        send_abandoned_cart_reminder,
        send_order_status_update,
        
        # Notification history query
        get_notification_history,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,  # Deterministic - no creativity needed for notifications
        max_output_tokens=2048,
    ),
)

logger.info(
    f"CustomerCommunicationAgent initialized successfully with {len(customer_communication_agent.tools)} tools"
)

# Export agent instance
__all__ = ["customer_communication_agent"]
