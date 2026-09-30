"""Tests for serviceability_agent: construction (MCP toolset) and the
``serviceability_context`` after_tool_callback, using a recorded MCP result."""

import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.adk.tools.mcp_tool import McpToolset

from sales_common.config import ConfigError
from sales_common.context import CONTEXT_UPDATE_KEY, export_context_delta

from serviceability_agent import build_agent, root_agent
from serviceability_agent.callbacks import record_serviceability_context

RECORDED = json.loads((Path(__file__).parent / "recorded_check_19103.json").read_text())
ARGS = {"street": "123 Main St", "city": "Philadelphia", "state": "PA", "zip_code": "19103"}
EXPECTED_CONTEXT = {
    "is_serviceable": True,
    "infrastructure_type": "FTTP",
    "max_speed_mbps": 5000,
    "available_products": [
        "FIB-1G", "FIB-5G", "VOICE-BAS", "VOICE-STD", "VOICE-ENT", "VOICE-UCAAS",
        "SDWAN-ESS", "SDWAN-PRO", "MOB-BAS", "MOB-UNL", "MOB-PREM",
    ],
    "available_product_categories": ["Internet", "Voice", "SD-WAN", "Mobile"],
    "service_zone": "Metro-Center-PA",
    "estimated_install_days": 5,
    "service_address": "123 Main St, Philadelphia, PA 19103",
}


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_root_agent_uses_serviceability_mcp_toolset():
    assert root_agent.name == "serviceability_agent"
    assert len(root_agent.tools) == 1
    toolset = root_agent.tools[0]
    assert isinstance(toolset, McpToolset)
    assert toolset.connection_params.url == "http://serviceability.test:8102/mcp/"
    assert root_agent.after_tool_callback == [record_serviceability_context, export_context_delta]
    assert root_agent.generate_content_config.temperature == 0.0
    assert "transfer_to_agent" not in root_agent.static_instruction


def test_mcp_url_is_required(monkeypatch):
    monkeypatch.delenv("SERVICEABILITY_MCP_URL", raising=False)
    with pytest.raises(ConfigError):
        build_agent(model="gemini-test")


def test_prompt_keeps_ui_output_format():
    prompt = root_agent.static_instruction
    for key in ("Infrastructure Type:", "Service Zone:", "Maximum Speed:", "Installation Timeline:"):
        assert key in prompt
    assert "• **FIB-1G** - Business Fiber 1 Gbps" in prompt
    assert "location is serviceable" in prompt and "location is not serviceable" in prompt


# ---------------------------------------------------------------------------
# Callback unit tests (fake tool context that tracks state_delta like ADK)
# ---------------------------------------------------------------------------

class FakeToolContext:
    def __init__(self):
        self.actions = SimpleNamespace(state_delta={})
        self.state = self.actions.state_delta


def run_callbacks(tool_name, response, args=ARGS):
    tool = SimpleNamespace(name=tool_name)
    ctx = FakeToolContext()
    for callback in root_agent.after_tool_callback:
        result = callback(tool, args, ctx, response)
        if result:
            return ctx, result
    return ctx, None


def test_callback_records_context_and_exports_update():
    ctx, response = run_callbacks("check_service_availability", copy.deepcopy(RECORDED))
    assert ctx.state["serviceability_context"] == EXPECTED_CONTEXT
    assert response[CONTEXT_UPDATE_KEY] == {"serviceability_context": EXPECTED_CONTEXT}
    assert response["structuredContent"] == RECORDED["structuredContent"]


def test_callback_parses_text_content_without_structured_content():
    text_only = {"content": RECORDED["content"], "isError": False}
    ctx, _ = run_callbacks("check_service_availability", text_only)
    assert ctx.state["serviceability_context"] == EXPECTED_CONTEXT


def test_callback_records_unserviceable_result():
    response = {
        "structuredContent": {
            "serviceable": False,
            "address": {"street": "1 Nowhere Rd", "city": "Remote", "state": "AK", "zip_code": "99999"},
            "available_product_categories": [],
            "available_products": [],
            "reason": "No infrastructure at location.",
        },
        "isError": False,
    }
    ctx, result = run_callbacks("check_service_availability", response)
    context = ctx.state["serviceability_context"]
    assert context["is_serviceable"] is False
    assert context["available_products"] == []
    assert context["service_address"] == "1 Nowhere Rd, Remote, AK 99999"
    assert result[CONTEXT_UPDATE_KEY]["serviceability_context"] == context


@pytest.mark.parametrize(
    "tool_name,response",
    [
        ("validate_and_parse_address", {"structuredContent": {"valid": True}, "isError": False}),
        ("check_service_availability", {"content": [{"type": "text", "text": "Invalid address"}],
                                        "isError": True}),
    ],
)
def test_callback_ignores_other_tools_and_errors(tool_name, response):
    ctx, result = run_callbacks(tool_name, response)
    assert "serviceability_context" not in ctx.state
    assert result is None


# ---------------------------------------------------------------------------
# End to end through the ADK runner (scripted model, recorded MCP result)
# ---------------------------------------------------------------------------

def test_runner_writes_state_and_context_update():
    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools.base_tool import BaseTool
    from google.genai import types

    from sales_common.testing import ScriptLlm

    class RecordedMcpTool(BaseTool):
        """Stands in for the MCP tool: same name, returns the recorded MCP result."""

        def __init__(self):
            super().__init__(name="check_service_availability", description="recorded")

        def _get_declaration(self):
            return types.FunctionDeclaration(
                name=self.name,
                description=self.description,
                parameters_json_schema={
                    "type": "object",
                    "properties": {k: {"type": "string"} for k in ARGS},
                },
            )

        async def run_async(self, *, args, tool_context):
            return copy.deepcopy(RECORDED)

    agent = build_agent(
        model=ScriptLlm(steps=[{"call": "check_service_availability", "args": ARGS}, {"text": "done"}])
    )
    agent.tools = [RecordedMcpTool()]

    async def run():
        sessions = InMemorySessionService()
        runner = Runner(app_name="t", agent=agent, session_service=sessions, auto_create_session=True)
        responses = []
        async for event in runner.run_async(
            user_id="u", session_id="s",
            new_message=types.Content(role="user", parts=[types.Part(text="check 19103")]),
        ):
            for part in (event.content.parts if event.content else None) or []:
                if part.function_response:
                    responses.append(part.function_response.response)
        session = await sessions.get_session(app_name="t", user_id="u", session_id="s")
        return responses, session.state

    responses, state = asyncio.run(run())
    assert state["serviceability_context"] == EXPECTED_CONTEXT
    assert responses[0][CONTEXT_UPDATE_KEY]["serviceability_context"]["is_serviceable"] is True
