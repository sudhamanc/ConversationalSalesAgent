from sales_common.mcp_client import mcp_result_payload


def test_structured_content_object():
    assert mcp_result_payload({"structuredContent": {"found": True}}) == {"found": True}


def test_structured_content_result_wrapper_unwrapped():
    raw = {"structuredContent": {"result": {"found": True, "product_id": "FIB-1G"}}, "isError": False}
    assert mcp_result_payload(raw) == {"found": True, "product_id": "FIB-1G"}
    assert mcp_result_payload({"structured_content": {"result": {"a": 1}}}) == {"a": 1}


def test_result_wrapper_kept_for_non_objects_or_extra_keys():
    assert mcp_result_payload({"structuredContent": {"result": [1, 2]}}) == {"result": [1, 2]}
    both = {"result": {"a": 1}, "count": 1}
    assert mcp_result_payload({"structuredContent": both}) == both


def test_text_fallback_and_errors():
    assert mcp_result_payload({"content": [{"type": "text", "text": '{"x": 1}'}]}) == {"x": 1}
    assert mcp_result_payload({"isError": True, "structuredContent": {"x": 1}}) is None
    assert mcp_result_payload("nope") is None



async def test_mcp_client_sends_id_token_without_request_context(monkeypatch):
    """Cold-start tool listing has no ADK context; the client itself must authenticate."""
    import httpx2

    from sales_common import auth
    from sales_common.mcp_client import authed_mcp_http_client, mcp_toolset

    monkeypatch.setenv("SERVICE_AUTH", "gcp_id_token")
    auth._cache.clear()
    seen = {}
    monkeypatch.setattr(auth, "_default_fetcher", lambda audience: f"tok-for-{audience}")

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx2.Response(200, json={})

    client = authed_mcp_http_client(headers={"x": "1"})
    client._transport = httpx2.MockTransport(handler)
    async with client:
        await client.post("https://csa-catalog-abc.a.run.app/mcp/")
    assert seen["auth"] == "Bearer tok-for-https://csa-catalog-abc.a.run.app"
    toolset = mcp_toolset("https://csa-catalog-abc.a.run.app/mcp/")
    assert toolset._connection_params.httpx_client_factory is authed_mcp_http_client


async def test_mcp_client_no_token_locally(monkeypatch):
    import httpx2

    from sales_common.mcp_client import authed_mcp_http_client

    monkeypatch.setenv("SERVICE_AUTH", "none")
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx2.Response(200, json={})

    client = authed_mcp_http_client()
    client._transport = httpx2.MockTransport(handler)
    async with client:
        await client.post("http://127.0.0.1:8101/mcp/")
    assert seen["auth"] is None
