"""MCP round trip: run the service with uvicorn and call it through ADK McpToolset."""

import asyncio
import socket
import threading
import time

import pytest
import uvicorn
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from catalog_service.app import create_app
from catalog_service.mcp_server import TOOL_NAMES
from sales_common.mcp_client import mcp_result_payload, mcp_toolset
from sales_common.testing import ScriptLlm

pytestmark = pytest.mark.usefixtures("seeded_db")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def mcp_url(seeded_db):
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(create_app(rag_warmup=False), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not server.started:
        if time.time() > deadline or not thread.is_alive():
            pytest.fail("catalog service did not start")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/mcp/"
    server.should_exit = True
    thread.join(timeout=10)


def test_tools_list(mcp_url):
    async def run():
        toolset = mcp_toolset(mcp_url)
        try:
            tools = await toolset.get_tools()
            return {t.name: t for t in tools}
        finally:
            await toolset.close()

    tools = asyncio.run(run())
    assert set(tools) == set(TOOL_NAMES)
    assert len(tools) == 8
    for tool in tools.values():
        decl = tool._get_declaration()
        assert decl.description
    compare_decl = tools["compare_products"]._get_declaration()
    assert compare_decl.parameters_json_schema or compare_decl.parameters


async def _run_agent(url: str, steps: list[dict]) -> list[dict]:
    toolset = mcp_toolset(url)
    agent = Agent(name="probe", model=ScriptLlm(steps=steps), instruction="probe", tools=[toolset])
    runner = Runner(agent=agent, app_name="probe", session_service=InMemorySessionService(), auto_create_session=True)
    responses = []
    try:
        async for event in runner.run_async(
            user_id="u1",
            session_id="s1",
            new_message=types.Content(role="user", parts=[types.Part(text="go")]),
        ):
            for part in (event.content.parts if event.content else None) or []:
                if part.function_response:
                    responses.append(part.function_response.response)
    finally:
        await toolset.close()
    return responses


def test_get_product_by_id_round_trip(mcp_url):
    responses = asyncio.run(
        _run_agent(
            mcp_url,
            [{"call": "get_product_by_id", "args": {"product_id": "FIB-1G"}}, {"text": "done"}],
        )
    )
    assert len(responses) == 1
    raw = responses[0]
    payload = mcp_result_payload(raw)
    assert payload is not None, raw
    assert payload["found"] is True
    assert payload["product_id"] == "FIB-1G"
    assert "unit_price" not in payload and "price" not in payload
    assert raw.get("structuredContent") or raw.get("structured_content")


def test_error_results_are_data(mcp_url):
    responses = asyncio.run(
        _run_agent(
            mcp_url,
            [
                {"call": "get_product_by_id", "args": {"product_id": "nope-1"}},
                {"call": "compare_products", "args": {"product_ids": ["FIB-1G", "fib-5g", "FIB-10G"]}},
                {"text": "done"},
            ],
        )
    )
    missing, compared = (mcp_result_payload(r) for r in responses)
    assert missing["found"] is False
    assert compared["fastest_product_id"] == "FIB-10G"
