"""Discovery agent: identifies the customer, registers companies/locations and gathers BANT.

Served as an A2A service (``discovery_agent.server:app``). The gateway workflow
performs the Discovery -> Serviceability hand-off deterministically once
``customer_context`` carries a confirmed address, so this agent never transfers.
"""

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.tools import FunctionTool

from sales_common.config import generate_config, model_name
from sales_common.models import agent_model
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import DISCOVERY_AGENT_INSTRUCTION, DISCOVERY_SHORT_DESCRIPTION
from .tools import ALL_TOOLS

AGENT_NAME = "discovery_agent"


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    """Build a fresh, unbound discovery agent (``model`` overrides ``GEMINI_MODEL``)."""
    return Agent(
        name=AGENT_NAME,
        model=model or agent_model(),
        description=DISCOVERY_SHORT_DESCRIPTION,
        static_instruction=DISCOVERY_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=[FunctionTool(tool) for tool in ALL_TOOLS],
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        generate_content_config=generate_config(temperature=0.0),
    )


root_agent = build_agent()
