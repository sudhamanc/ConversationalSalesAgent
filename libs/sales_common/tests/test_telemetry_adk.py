"""ADK instrumentation: one agent, LLM and tool observation each, with input/output (no network)."""

from __future__ import annotations

import pytest
from google.adk import Runner
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.genai import types
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from opentelemetry import context
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sales_common import telemetry
from sales_common.telemetry import TelemetrySettings, build_tracer_provider
from sales_common.testing import ScriptLlm


def get_quote_total(term_months: int) -> dict:
    """Return a quote total for a term."""
    return {"total": 99.0 * term_months}


@pytest.fixture
def instrumented():
    settings = TelemetrySettings(
        host="https://lf.example", public_key="pk", secret_key="sk", environment="local", release="",
        capture_content=True, flush_per_request=False, flush_timeout_ms=500,
    )
    exporter = InMemorySpanExporter()
    provider = build_tracer_provider("agent-test", settings, exporter=exporter)
    instrumentor = GoogleADKInstrumentor()
    instrumentor.instrument(tracer_provider=provider, skip_dep_check=True)
    try:
        yield provider, exporter
    finally:
        instrumentor.uninstrument()


async def test_agent_llm_and_tool_spans(instrumented):
    provider, exporter = instrumented
    llm = ScriptLlm(steps=[{"call": "get_quote_total", "args": {"term_months": 12}}, {"text": "Your total is $1188."}])
    agent = Agent(name="quote_agent", model=llm, instruction="Quote.", tools=[get_quote_total])
    runner = Runner(app_name="t", agent=agent, session_service=InMemorySessionService(), auto_create_session=True)

    token = context.attach(telemetry.turn_baggage_context("gw-session-1", "CUST-1"))
    try:
        async for _ in runner.run_async(
            user_id="u1",
            session_id="s1",
            new_message=types.Content(role="user", parts=[types.Part(text="Quote 12 months")]),
        ):
            pass
    finally:
        context.detach(token)

    provider.force_flush()
    spans = exporter.get_finished_spans()
    kinds = {}
    for span in spans:
        kind = span.attributes.get("openinference.span.kind")
        kinds.setdefault(kind, []).append(span)

    assert len(kinds.get("AGENT", [])) == 1
    assert len(kinds.get("TOOL", [])) == 1
    assert len(kinds.get("LLM", [])) == 2  # tool call turn + final answer turn
    tool = kinds["TOOL"][0]
    assert "12" in tool.attributes["input.value"] and "1188" in tool.attributes["output.value"]
    assert all(s.attributes.get("llm.model_name") == "script-llm" for s in kinds["LLM"])
    # one trace, every span stamped with the conversation session from baggage
    assert len({s.context.trace_id for s in spans}) == 1
    assert all(s.attributes.get("langfuse.session.id") == "gw-session-1" for s in spans)
    # no duplicate ADK-native call_llm/execute_tool spans
    native = [s for s in spans if s.name.startswith(("call_llm", "generate_content")) and "openinference.span.kind" not in s.attributes]
    assert native == []
