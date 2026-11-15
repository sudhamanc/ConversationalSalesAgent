"""Trace context crosses the A2A hop: gateway client -> agent service (no network, no database).

The agent app is served in a fresh ``contextvars.Context`` so only the HTTP
``traceparent``/``baggage`` headers can link its spans to the caller's trace.
"""

from __future__ import annotations

import asyncio
import contextvars

import httpx
import pytest
from google.adk import Runner
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.genai import types
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from opentelemetry import context
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sales_common import telemetry
from sales_common.a2a_client import remote_agent
from sales_common.telemetry import TelemetrySettings, TraceContextMiddleware, build_tracer_provider
from sales_common.testing import ScriptLlm


@pytest.fixture
def traced(monkeypatch):
    monkeypatch.setenv("SERVICE_AUTH", "none")
    settings = TelemetrySettings(
        host="https://lf.example", public_key="pk", secret_key="sk", environment="local", release="",
        capture_content=True, flush_per_request=False, flush_timeout_ms=500,
    )
    exporter = InMemorySpanExporter()
    provider = build_tracer_provider("a2a-test", settings, exporter=exporter)
    telemetry.activate(provider, settings)
    instrumentor = GoogleADKInstrumentor()
    instrumentor.instrument(tracer_provider=provider, skip_dep_check=True)
    try:
        yield provider, exporter
    finally:
        instrumentor.uninstrument()
        telemetry.activate(None)


def _isolated(app):
    """Run each ASGI call in an empty context, like a separate process."""

    async def isolated(scope, receive, send):
        await asyncio.create_task(app(scope, receive, send), context=contextvars.Context())

    return isolated


async def _run_turn(provider, exporter):
    agent = Agent(name="order_agent", model=ScriptLlm(steps=[{"text": "Cart created."}]), instruction="Orders.")
    agent_runner = Runner(
        app_name="order_agent", agent=agent, session_service=InMemorySessionService(), auto_create_session=True
    )
    agent_app = to_a2a(agent, host="localhost", port=8299, protocol="http", runner=agent_runner)
    agent_app.add_middleware(TraceContextMiddleware)

    async with agent_app.router.lifespan_context(agent_app):
        remote = remote_agent(
            "order_agent", "http://localhost:8299", transport=httpx.ASGITransport(app=_isolated(agent_app))
        )
        gw_runner = Runner(
            app_name="gateway", agent=remote, session_service=InMemorySessionService(), auto_create_session=True
        )
        token = context.attach(telemetry.turn_baggage_context("gw-sess-42", "CUST-7"))
        try:
            with telemetry.get_tracer("test").start_as_current_span("chat_turn") as root:
                root_trace = telemetry.trace_id_hex(root)
                replies = [
                    e
                    async for e in gw_runner.run_async(
                        user_id="u",
                        session_id="gw-sess-42",
                        new_message=types.Content(role="user", parts=[types.Part(text="create a cart")]),
                    )
                ]
        finally:
            context.detach(token)
    provider.force_flush()
    return root_trace, exporter.get_finished_spans(), replies


async def test_agent_spans_join_gateway_trace(traced):
    root_trace, spans, replies = await _run_turn(*traced)
    assert any(e.content and e.content.parts and "Cart created." in (e.content.parts[0].text or "") for e in replies)
    remote_side = [s for s in spans if s.attributes.get("openinference.span.kind") == "LLM"]
    assert remote_side, "agent-side LLM span missing"
    assert {format(s.context.trace_id, "032x") for s in spans} == {root_trace}
    assert all(s.attributes.get("langfuse.session.id") == "gw-sess-42" for s in spans)
    assert all(s.attributes.get("langfuse.user.id") == "CUST-7" for s in spans)


async def test_without_headers_agent_starts_its_own_trace(traced, monkeypatch):
    """Control: the isolation is real, so the headers are what links the two sides."""
    monkeypatch.setattr(telemetry.propagate, "inject", lambda *args, **kwargs: None)
    root_trace, spans, _ = await _run_turn(*traced)
    llm = [s for s in spans if s.attributes.get("openinference.span.kind") == "LLM"]
    assert llm and all(format(s.context.trace_id, "032x") != root_trace for s in llm)
    assert all(s.attributes.get("langfuse.session.id") is None for s in llm)
