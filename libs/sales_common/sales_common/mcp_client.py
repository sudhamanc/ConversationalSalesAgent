"""``McpToolset`` factory for agents consuming the REST+MCP tool services."""

from __future__ import annotations

import json
from typing import Any, Optional, Sequence

from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

from .auth import service_headers
from .config import env_int


def mcp_toolset(url: str, *, tool_filter: Optional[Sequence[str]] = None) -> McpToolset:
    """Streamable-HTTP MCP toolset for ``url`` (e.g. ``http://catalog:8101/mcp/``)."""
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=url,
            timeout=float(env_int("MCP_TIMEOUT_SECONDS", 15)),
        ),
        tool_filter=list(tool_filter) if tool_filter else None,
        tool_list_cache_ttl_seconds=env_int("MCP_TOOL_CACHE_SECONDS", 300),
        header_provider=lambda _ctx: service_headers(url),
    )


def mcp_result_payload(tool_response: Any) -> Optional[dict]:
    """Extract the JSON object from an MCP ``CallToolResult``-shaped dict.

    Prefers ``structuredContent``; falls back to parsing the first JSON text part.
    """
    if not isinstance(tool_response, dict):
        return None
    if tool_response.get("isError"):
        return None
    structured = tool_response.get("structuredContent") or tool_response.get("structured_content")
    if isinstance(structured, dict):
        # FastMCP/MCPServer wraps non-object returns as {"result": ...}
        return structured
    for part in tool_response.get("content") or []:
        if isinstance(part, dict) and part.get("type") == "text":
            try:
                parsed = json.loads(part.get("text") or "")
            except ValueError:
                continue
            if isinstance(parsed, dict):
                return parsed
    return None
