# Tasks: Fix MCP service authentication on Cloud Run

## 1. Shared library

- [x] 1.1 `sales_common.auth`: add `ServiceAuthHttpx2` (an `httpx2.Auth` that adds the cached ID token per request; no-op when `SERVICE_AUTH=none`). `sales_common.mcp_client.mcp_toolset`: build `StreamableHTTPConnectionParams(httpx_client_factory=...)`, using `create_mcp_http_client(headers, timeout, auth or ServiceAuthHttpx2())`, and drop `header_provider`. Verify: unit tests show the factory's client sends `Authorization: Bearer <token>` on a request with no context (`httpx2.MockTransport`, fake fetcher) and sends none with `SERVICE_AUTH=none`; `pytest libs/sales_common/tests` and the MCP agents' tests pass.

## 2. Verification

- [x] 2.1 Deploy the MCP consumers (`scripts/deploy_cloud.sh --only product,faq,serviceability-agent`). Verify: no `403` from the tool services in the agents' logs after a cold start, and an FAQ turn ("What is your cancellation policy?") is answered from `search_faq`, with an MCP `tools/call search_faq` span in its Langfuse trace.
- [x] 2.2 `openspec validate fix-mcp-service-auth` passes. Commit, then `openspec archive fix-mcp-service-auth -y`.
