"""Serviceability Agent: PRE-SALE address validation and network coverage.

The deterministic tools (address validation, coverage lookup) live in the
serviceability service (``services/serviceability``) and are consumed over MCP
(streamable HTTP) at ``SERVICEABILITY_MCP_URL``. ``serviceability_context`` is
recorded by an agent-side ``after_tool_callback``.
"""

from __future__ import annotations

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name, require_env
from sales_common.models import agent_model
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.mcp_client import mcp_toolset
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .callbacks import record_serviceability_context
from .prompts import SERVICEABILITY_AGENT_INSTRUCTION, SERVICEABILITY_SHORT_DESCRIPTION

AGENT_NAME = "serviceability_agent"


def serviceability_mcp_url() -> str:
    """MCP endpoint of the serviceability service, e.g. ``http://serviceability:8102/mcp/``."""
    return require_env("SERVICEABILITY_MCP_URL")


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    return Agent(
        name=AGENT_NAME,
        model=model or agent_model(),
        description=SERVICEABILITY_SHORT_DESCRIPTION,
        static_instruction=SERVICEABILITY_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=[mcp_toolset(serviceability_mcp_url())],
        before_agent_callback=[import_forwarded_context],
        # record_serviceability_context returns None, so export_context_delta
        # always runs next and adds _context_update for the gateway.
        after_tool_callback=[record_serviceability_context, export_context_delta],
        generate_content_config=generate_config(temperature=0.0, max_output_tokens=2048),
    )


root_agent = build_agent()
