"""
Order Agent - cart, order creation, contracts and order status (A2A service).

SEPARATION OF CONCERNS:
- OrderAgent: Cart management, order creation, contract generation (PRE-FULFILLMENT)
- ServiceFulfillmentAgent: Installation scheduling, provisioning, activation (POST-ORDER)
"""

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name
from sales_common.models import agent_model
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import ORDER_AGENT_INSTRUCTION, ORDER_SHORT_DESCRIPTION
from .tools.cart_tools import add_to_cart, clear_cart, create_cart, get_cart, remove_from_cart
from .tools.order_tools import (
    cancel_order,
    create_order,
    generate_contract,
    get_order,
    modify_order,
    update_order_status,
)

AGENT_NAME = "order_agent"


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    """Build the order_agent."""
    return Agent(
        name=AGENT_NAME,
        model=model or agent_model(),
        description=ORDER_SHORT_DESCRIPTION,
        static_instruction=ORDER_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
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
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        generate_content_config=generate_config(temperature=0.0, max_output_tokens=2048),
    )


root_agent = build_agent()
