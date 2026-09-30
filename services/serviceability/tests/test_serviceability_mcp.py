"""MCP round trip through ADK ``McpToolset`` against the app served by uvicorn."""

import asyncio
import os
import socket
import threading
import time

import httpx
import pytest

pytestmark = [pytest.mark.pg, pytest.mark.usefixtures("migrated_db")]

os.environ.setdefault("MCP_TIMEOUT_SECONDS", "15")

EXPECTED_TOOLS = {
    "validate_and_parse_address",
    "normalize_address",
    "extract_zip_code",
    "check_service_availability",
    "get_infrastructure_by_technology",
    "get_coverage_zones",
}
PHILLY = {"street": "123 Main St", "city": "Philadelphia", "state": "PA", "zip_code": "19103"}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    import uvicorn

    from serviceability_service.app import create_app

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{base}/healthz", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    else:
        pytest.fail("serviceability service did not start")
    yield base
    server.should_exit = True
    thread.join(timeout=10)


async def _run_tool_via_agent(url: str, tool: str, args: dict) -> tuple[set[str], dict]:
    """Call ``tool`` through an ADK agent (scripted model) using ``McpToolset``."""
    from google.adk import Agent, Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from sales_common.mcp_client import mcp_toolset
    from sales_common.testing import ScriptLlm

    toolset = mcp_toolset(url)
    try:
        names = {t.name for t in await toolset.get_tools()}
        agent = Agent(
            name="probe",
            model=ScriptLlm(steps=[{"call": tool, "args": args}, {"text": "done"}]),
            tools=[toolset],
        )
        runner = Runner(app_name="probe", agent=agent, session_service=InMemorySessionService(),
                        auto_create_session=True)
        response = None
        async for event in runner.run_async(
            user_id="u", session_id="s",
            new_message=types.Content(role="user", parts=[types.Part(text="go")]),
        ):
            for part in (event.content.parts if event.content else None) or []:
                if part.function_response and part.function_response.name == tool:
                    response = part.function_response.response
        return names, response
    finally:
        await toolset.close()


def test_lists_six_tools_and_check_matches_rest(server_url):
    names, response = asyncio.run(
        _run_tool_via_agent(f"{server_url}/mcp/", "check_service_availability", PHILLY)
    )
    assert names == EXPECTED_TOOLS

    from sales_common.mcp_client import mcp_result_payload

    assert response is not None and not response.get("isError")
    payload = mcp_result_payload(response)
    rest = httpx.post(f"{server_url}/api/v1/serviceability/check", json=PHILLY).json()
    assert payload == rest
    assert payload["serviceable"] is True and payload["available_products"]


def test_invalid_state_is_tool_error(server_url):
    _, response = asyncio.run(
        _run_tool_via_agent(f"{server_url}/mcp/", "check_service_availability", {**PHILLY, "state": "ZZ"})
    )
    assert response.get("isError") is True
    assert "state" in response["content"][0]["text"]


def test_coverage_zones_matches_rest(server_url):
    from sales_common.mcp_client import mcp_result_payload

    _, response = asyncio.run(_run_tool_via_agent(f"{server_url}/mcp/", "get_coverage_zones", {}))
    assert mcp_result_payload(response) == httpx.get(f"{server_url}/api/v1/coverage-zones").json()
