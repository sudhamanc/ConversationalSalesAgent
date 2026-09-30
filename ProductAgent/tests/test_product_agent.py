"""Construction, prompt and MCP-consumption tests for product_agent."""

import asyncio
import os
import socket
import threading
import time
from typing import Any, Optional

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.genai import types

from sales_common.config import ConfigError
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.mcp_client import mcp_result_payload
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION
from sales_common.testing import ScriptLlm

from product_agent import build_agent, root_agent
from product_agent.agent import CATALOG_TOOLS
from product_agent.prompts import PRODUCT_AGENT_INSTRUCTION


def _toolset(agent) -> McpToolset:
    assert len(agent.tools) == 1
    toolset = agent.tools[0]
    assert isinstance(toolset, McpToolset)
    return toolset


def test_root_agent_uses_catalog_mcp_url_env():
    assert root_agent.name == "product_agent"
    assert _toolset(root_agent)._connection_params.url == os.environ["CATALOG_MCP_URL"]


def test_build_agent_with_explicit_url():
    agent = build_agent(catalog_mcp_url="http://catalog:8101/mcp/")
    toolset = _toolset(agent)
    assert toolset._connection_params.url == "http://catalog:8101/mcp/"
    assert list(toolset.tool_filter) == list(CATALOG_TOOLS)
    assert len(CATALOG_TOOLS) == 8


def test_catalog_url_is_required(monkeypatch):
    monkeypatch.delenv("CATALOG_MCP_URL", raising=False)
    with pytest.raises(ConfigError):
        build_agent()


def test_model_is_required(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    with pytest.raises(ConfigError):
        build_agent(catalog_mcp_url="http://catalog:8101/mcp/")


def test_agent_configuration():
    agent = build_agent(catalog_mcp_url="http://catalog:8101/mcp/")
    assert agent.static_instruction == PRODUCT_AGENT_INSTRUCTION
    assert agent.instruction == JOURNEY_CONTEXT_INSTRUCTION
    assert import_forwarded_context in agent.before_agent_callback
    assert export_context_delta in agent.after_tool_callback
    config = agent.generate_content_config
    assert config.temperature == 0.0 and config.top_p == 0.2 and config.top_k == 20
    assert config.max_output_tokens == 2048
    assert "catalog" in agent.description.lower()


def test_prompt_has_no_transfer_mechanics():
    assert "transfer_to_agent" not in PRODUCT_AGENT_INSTRUCTION
    assert "transfer" not in PRODUCT_AGENT_INSTRUCTION.lower()
    for name in CATALOG_TOOLS:
        assert name in PRODUCT_AGENT_INSTRUCTION


def test_server_import():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not set")
    from product_agent import server

    paths = {getattr(r, "path", None) for r in server.app.router.routes}
    assert "/healthz" in paths


# ---------------------------------------------------------------------------
# End to end with a stub MCP server (no catalog package, no database)
# ---------------------------------------------------------------------------


def _stub_catalog_app():
    import contextlib

    from mcp.server.mcpserver import MCPServer
    from starlette.applications import Starlette
    from starlette.routing import Mount

    mcp = MCPServer(name="catalog-stub")

    @mcp.tool()
    async def get_product_by_id(product_id: str) -> dict[str, Any]:
        """Stub product lookup."""
        return {"found": True, "product_id": product_id.upper(), "product_name": "Stub Fiber"}

    @mcp.tool()
    async def list_available_products(category: Optional[str] = None) -> dict[str, Any]:
        """Stub listing."""
        return {"products": [], "count": 0}

    @mcp.tool()
    async def not_a_catalog_tool() -> dict[str, Any]:
        """Filtered out by the agent's tool_filter."""
        return {}

    inner = mcp.streamable_http_app(
        streamable_http_path="/", stateless_http=True, json_response=True, host="0.0.0.0"
    )

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        async with mcp.session_manager.run():
            yield

    return Starlette(routes=[Mount("/mcp", app=inner)], lifespan=lifespan)


@pytest.fixture(scope="module")
def stub_url():
    import uvicorn

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(_stub_catalog_app(), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not server.started:
        if time.time() > deadline:
            pytest.fail("stub MCP server did not start")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/mcp/"
    server.should_exit = True
    thread.join(timeout=10)


def test_agent_calls_catalog_over_mcp(stub_url):
    llm = ScriptLlm(
        steps=[
            {"call": "get_product_by_id", "args": {"product_id": "fib-1g"}},
            {"text": "**Stub Fiber (FIB-1G)**"},
        ]
    )
    agent = build_agent(model=llm, catalog_mcp_url=stub_url)

    async def run():
        runner = Runner(
            agent=agent, app_name="product_agent", session_service=InMemorySessionService(),
            auto_create_session=True,
        )
        responses, texts = [], []
        try:
            async for event in runner.run_async(
                user_id="u", session_id="s",
                new_message=types.Content(role="user", parts=[types.Part(text="FIB-1G specs?")]),
            ):
                for part in (event.content.parts if event.content else None) or []:
                    if part.function_response:
                        responses.append(part.function_response.response)
                    if part.text:
                        texts.append(part.text)
            tools = await agent.tools[0].get_tools()
        finally:
            await agent.tools[0].close()
        return responses, texts, tools

    responses, texts, tools = asyncio.run(run())
    assert {t.name for t in tools} == {"get_product_by_id", "list_available_products"}
    payload = mcp_result_payload(responses[0])
    assert payload == {"found": True, "product_id": "FIB-1G", "product_name": "Stub Fiber"}
    assert "_context_update" not in responses[0]
    assert texts[-1] == "**Stub Fiber (FIB-1G)**"
