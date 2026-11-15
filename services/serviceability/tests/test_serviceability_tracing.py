"""MCP trace propagation: a tools/call joins the caller's trace (no database, no network).

The MCP SDK's server middleware and client dispatcher use the process-wide
OpenTelemetry provider, so this module installs one (in-memory exporter) once.
"""

from __future__ import annotations

import asyncio

import pytest
from mcp import Client
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sales_common import telemetry
from sales_common.telemetry import TelemetrySettings, build_tracer_provider


@pytest.fixture(scope="module")
def global_tracing():
    settings = TelemetrySettings(
        host="https://lf.example", public_key="pk", secret_key="sk", environment="local", release="",
        capture_content=True, flush_per_request=False, flush_timeout_ms=500,
    )
    exporter = InMemorySpanExporter()
    provider = build_tracer_provider("serviceability-service", settings, exporter=exporter)
    trace.set_tracer_provider(provider)
    if not isinstance(trace.get_tracer_provider(), TracerProvider) or trace.get_tracer_provider() is not provider:
        pytest.skip("another global tracer provider is already installed in this process")
    telemetry.activate(provider, settings)
    yield provider, exporter
    telemetry.activate(None)


def test_tools_call_joins_caller_trace(global_tracing):
    from serviceability_service.mcp_server import mcp

    provider, exporter = global_tracing
    exporter.clear()

    async def call():
        # Connect outside the caller span: the in-process server's tasks then carry no
        # ambient trace, so only the JSON-RPC ``_meta`` trace context can link the span.
        async with Client(mcp) as client:
            with telemetry.get_tracer("agent").start_as_current_span("execute_tool extract_zip_code") as caller:
                result = await client.call_tool(
                    "extract_zip_code", {"address_string": "1 Main St, Philadelphia, PA 19103"}
                )
            return telemetry.trace_id_hex(caller), result

    caller_trace, result = asyncio.run(call())
    assert "19103" in str(result)

    provider.force_flush()
    spans = exporter.get_finished_spans()
    server_calls = [
        s for s in spans
        if s.attributes.get("mcp.method.name") == "tools/call" and s.kind == trace.SpanKind.SERVER
    ]
    assert len(server_calls) == 1
    assert format(server_calls[0].context.trace_id, "032x") == caller_trace
    assert server_calls[0].attributes.get("gen_ai.tool.name") == "extract_zip_code"
    # protocol noise is filtered before export
    assert not [s for s in spans if s.attributes.get("mcp.method.name") in ("initialize", "tools/list")]
