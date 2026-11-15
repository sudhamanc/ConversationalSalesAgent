# Proposal: Fix MCP service authentication on Cloud Run

## Why

On Cloud Run, every MCP call from an agent to a tool service fails with HTTP 403 ("Empty Authorization header value"). The agent then runs without its MCP tools, and its turns hang or fail. Found while verifying `langfuse-observability` on GCP (2026-11-15): the FAQ agent's `search_faq` never loaded. `sales_common.mcp_client.mcp_toolset` sends the Google ID token through `McpToolset(header_provider=...)`, but ADK 2.10 applies `header_provider` only when a request context exists (`McpToolset._get_headers`: `if self._header_provider and readonly_context`). The tool-list fetch on a fresh instance has no context, so it goes out without a token. Local runs use `SERVICE_AUTH=none`, which hides the defect.

## What Changes

- `mcp_toolset()` passes `StreamableHTTPConnectionParams(httpx_client_factory=...)`. The factory builds the MCP SDK's HTTP client (`mcp.shared._httpx_utils.create_mcp_http_client`) with an `httpx2.Auth` flow. That flow adds a cached Google ID token, with the target service as audience, to **every** request: session creation, tool listing and tool calls. It does nothing when `SERVICE_AUTH=none`.
- `header_provider` is no longer used for service auth.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-services`: "Service authentication in cloud" now also covers MCP requests made without a request context (tool listing at startup).

## BASELINE.md sections affected

None (no service, port, tool or command changes).

## Non-goals

- Changing Cloud Run IAM or the A2A client auth (`ServiceAuth` on the gateway's httpx client works).
- Upgrading ADK.

## Impact

- **Agents:** the product, FAQ and serviceability agents (the MCP consumers) load their tools on Cloud Run. No prompt or tool change.
- **APIs / MCP servers:** none. **Data:** none. **Scripts:** none.
- **Documentation:** none needed beyond this change (behavior now matches the existing docs).
