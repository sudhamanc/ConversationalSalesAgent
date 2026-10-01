"""Customer Communication Agent service - customer notifications for order lifecycle events."""

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name
from sales_common.models import agent_model
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import (
    CUSTOMER_COMMUNICATION_AGENT_INSTRUCTION,
    CUSTOMER_COMMUNICATION_SHORT_DESCRIPTION,
)
from .tools import (
    get_notification_history,
    send_abandoned_cart_reminder,
    send_installation_reminder,
    send_order_confirmation,
    send_order_status_update,
    send_payment_notification,
    send_quote_confirmation,
    send_service_activated_notification,
)

TOOLS = [
    # Order lifecycle notifications (enqueue to the outbox + immediate dispatch)
    send_order_confirmation,
    send_quote_confirmation,
    send_payment_notification,
    send_installation_reminder,
    send_service_activated_notification,
    send_abandoned_cart_reminder,
    send_order_status_update,
    # Notification history query
    get_notification_history,
]


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    """Build the customer_communication_agent."""
    return Agent(
        name="customer_communication_agent",
        model=model or agent_model(),
        description=CUSTOMER_COMMUNICATION_SHORT_DESCRIPTION,
        static_instruction=CUSTOMER_COMMUNICATION_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=list(TOOLS),
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        generate_content_config=generate_config(temperature=0.0, max_output_tokens=2048),
    )


root_agent = build_agent()
