"""FAQ agent service - answers policy and support questions from the FAQ corpus (RAG).

Answers are grounded in the Connectivity Max FAQ documents indexed by the catalog
service (``services/catalog/data/faq_docs``) and retrieved with the ``search_faq``
MCP tool at ``CATALOG_MCP_URL``. The agent states only what the passages say.
"""

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name, require_env
from sales_common.models import agent_model
from sales_common.context import import_forwarded_context
from sales_common.mcp_client import mcp_toolset
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import FAQ_AGENT_INSTRUCTION, FAQ_SHORT_DESCRIPTION

#: The only catalog MCP tool this agent uses.
FAQ_TOOLS = ("search_faq",)


def build_agent(model: Optional[str | BaseLlm] = None, *, catalog_mcp_url: Optional[str] = None) -> Agent:
    """Build the faq_agent with the FAQ retrieval tool."""
    url = catalog_mcp_url or require_env("CATALOG_MCP_URL")
    return Agent(
        name="faq_agent",
        model=model or agent_model(),
        description=FAQ_SHORT_DESCRIPTION,
        static_instruction=FAQ_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=[mcp_toolset(url, tool_filter=FAQ_TOOLS)],
        before_agent_callback=[import_forwarded_context],
        generate_content_config=generate_config(temperature=0.2, max_output_tokens=2048),
    )


root_agent = build_agent()
