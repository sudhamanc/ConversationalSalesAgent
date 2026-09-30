"""Product agent: catalog-driven technical specifications and comparisons.

All product data comes from the catalog service over MCP (``CATALOG_MCP_URL``,
e.g. ``http://catalog:8101/mcp/``). The agent holds no catalog data and no
tool implementations; tool names are unchanged from the in-process version.
"""

from __future__ import annotations

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name, require_env
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.mcp_client import mcp_toolset
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import PRODUCT_AGENT_INSTRUCTION, PRODUCT_SHORT_DESCRIPTION

AGENT_NAME = "product_agent"

#: Tools served by the catalog MCP server (services/catalog).
CATALOG_TOOLS = (
    "list_available_products",
    "get_product_by_id",
    "search_products_by_criteria",
    "get_product_categories",
    "compare_products",
    "suggest_alternatives",
    "get_best_value_product",
    "search_product_knowledge",
)


def _generate_config():
    config = generate_config(temperature=0.0, max_output_tokens=2048)
    # Deterministic sampling, unchanged from the pre-MCP agent.
    config.top_p = 0.2
    config.top_k = 20
    return config


def build_agent(
    model: Optional[str | BaseLlm] = None,
    *,
    catalog_mcp_url: Optional[str] = None,
) -> Agent:
    url = catalog_mcp_url or require_env("CATALOG_MCP_URL")
    return Agent(
        name=AGENT_NAME,
        model=model or model_name(),
        description=PRODUCT_SHORT_DESCRIPTION,
        static_instruction=PRODUCT_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=[mcp_toolset(url, tool_filter=CATALOG_TOOLS)],
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        generate_content_config=_generate_config(),
    )


root_agent = build_agent()
