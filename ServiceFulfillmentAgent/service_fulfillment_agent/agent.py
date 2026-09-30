"""Service fulfillment agent: installation scheduling, provisioning, dispatch and activation.

Served over A2A by ``service_fulfillment_agent.server``. The gateway workflow
hands off to ``payment_agent`` after a successful ``schedule_installation``;
this agent never transfers itself.
"""

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import SERVICE_FULFILLMENT_AGENT_INSTRUCTION, SERVICE_FULFILLMENT_SHORT_DESCRIPTION
from .tools.activation_tools import activate_service, run_service_tests
from .tools.equipment_tools import provision_equipment, track_equipment, verify_equipment_delivery
from .tools.installation_tools import complete_installation, dispatch_technician, update_installation_status
from .tools.order_tools import get_fulfillment_status
from .tools.scheduling_tools import (
    cancel_appointment,
    check_availability,
    reschedule_appointment,
    schedule_installation,
)

AGENT_NAME = "service_fulfillment_agent"


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    """Build the service_fulfillment_agent."""
    return Agent(
        name=AGENT_NAME,
        model=model or model_name(),
        description=SERVICE_FULFILLMENT_SHORT_DESCRIPTION,
        static_instruction=SERVICE_FULFILLMENT_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=[
            # Scheduling
            check_availability,
            schedule_installation,
            reschedule_appointment,
            cancel_appointment,
            # Equipment
            provision_equipment,
            track_equipment,
            verify_equipment_delivery,
            # Installation
            dispatch_technician,
            update_installation_status,
            complete_installation,
            # Activation
            activate_service,
            run_service_tests,
            # Status (read-only)
            get_fulfillment_status,
        ],
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        # 0.3 (not 0.0) avoids empty responses after tool calls.
        generate_content_config=generate_config(temperature=0.3, max_output_tokens=2048),
    )


root_agent = build_agent()
