"""sales_common.telemetry: opt-in config, masking, filtering, attributes, propagation."""

from __future__ import annotations

import logging

import httpx
import pytest
from opentelemetry import context, trace
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode

from sales_common import telemetry
from sales_common.telemetry import (
    REDACTED_ACCOUNT,
    REDACTED_CARD,
    REDACTED_CVV,
    FilteringMaskingExporter,
    TelemetrySettings,
    TraceContextMiddleware,
    build_tracer_provider,
    mask_text,
)

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
TRACEPARENT = f"00-{TRACE_ID}-00f067aa0ba902b7-01"


def _settings(**overrides) -> TelemetrySettings:
    values = dict(
        host="https://lf.example",
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        environment="local",
        release="",
        capture_content=True,
        flush_per_request=False,
        flush_timeout_ms=500,
    )
    values.update(overrides)
    return TelemetrySettings(**values)


@pytest.fixture
def tracing():
    """Activate an in-memory provider for this module; yields (provider, exporter, settings)."""

    def _make(**overrides):
        settings = _settings(**overrides)
        exporter = InMemorySpanExporter()
        provider = build_tracer_provider("test-service", settings, exporter=exporter)
        telemetry.activate(provider, settings)
        return provider, exporter, settings

    yield _make
    telemetry.activate(None)


def _finished(provider, exporter):
    provider.force_flush()
    return exporter.get_finished_spans()


# --- configuration -----------------------------------------------------------


def test_disabled_without_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    assert not TelemetrySettings.from_env().enabled


def test_otel_sdk_disabled_wins(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    assert not TelemetrySettings.from_env().enabled


def test_endpoint_and_auth(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-1")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-2")
    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com/")
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    settings = TelemetrySettings.from_env()
    assert settings.enabled
    assert settings.traces_endpoint == "https://cloud.langfuse.com/api/public/otel/v1/traces"
    assert settings.auth_header == "Basic cGstbGYtMTpzay1sZi0y"  # base64("pk-lf-1:sk-lf-2")


def test_default_host_and_invalid_environment(monkeypatch):
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "langfuse-prod")
    settings = TelemetrySettings.from_env()
    assert settings.host == "https://us.cloud.langfuse.com"
    assert settings.environment == "local"


def test_init_without_keys_is_noop(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setattr(telemetry, "_initialized", False)
    telemetry.activate(None)
    assert telemetry.init_telemetry("svc") is False
    assert not telemetry.enabled()
    assert telemetry.current_trace_id() is None
    # second call: still a no-op
    assert telemetry.init_telemetry("svc") is False


# --- masking -------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "pay with 4111 1111 1111 1111 please",
        "card 4111-1111-1111-1111",
        '{"card_number": "4111111111111111"}',
        "amex 378282246310005",
    ],
)
def test_card_numbers_masked(text):
    masked = mask_text(text)
    assert REDACTED_CARD in masked
    assert "4111" not in masked and "3782" not in masked


def test_card_followed_by_cvv_digits():
    masked = mask_text("4111 1111 1111 1111 123")
    assert masked.startswith(REDACTED_CARD)
    assert "4111" not in masked


@pytest.mark.parametrize(
    "text",
    [
        "4111 1111 1111 1112",  # fails Luhn
        "order ORD-20261001-0042 on 2026-10-01",
        "call 555-123-4567",
        "1234567890123456789012345",  # long id, not a card
    ],
)
def test_non_cards_untouched(text):
    assert mask_text(text) == text


@pytest.mark.parametrize(
    "text",
    ["pay with 4111 1111 1111 1111 cvv 123", '{"cvv": "1234"}', "CVC is 987", "security code: 456"],
)
def test_cvv_masked(text):
    masked = mask_text(text)
    assert REDACTED_CVV in masked
    assert not any(code in masked for code in ("123", "1234", "987", "456"))


@pytest.mark.parametrize(
    "text",
    ['{"account_number": "000123456789"}', "routing number 021000021", "acct# 12345678", "ABA: 011000015"],
)
def test_account_numbers_masked(text):
    masked = mask_text(text)
    assert REDACTED_ACCOUNT in masked


# --- exporter --------------------------------------------------------------------


def test_exported_attributes_events_and_status_are_masked(tracing):
    provider, exporter, _ = tracing()
    tracer = provider.get_tracer("t")
    with tracer.start_as_current_span("llm") as span:
        span.set_attribute("input.value", "pay with 4111 1111 1111 1111 cvv 123")
        span.set_attribute("tags", ["4111111111111111", "ok"])
        span.add_event("exception", {"exception.message": "card 4111111111111111 declined"})
        span.set_status(Status(StatusCode.ERROR, "declined 4111111111111111"))
    (exported,) = _finished(provider, exporter)
    assert exported.attributes["input.value"] == f"pay with {REDACTED_CARD} cvv {REDACTED_CVV}"
    assert exported.attributes["tags"] == (REDACTED_CARD, "ok")
    assert REDACTED_CARD in exported.events[0].attributes["exception.message"]
    assert exported.status.description == f"declined {REDACTED_CARD}"


def test_capture_content_false_drops_content(tracing):
    provider, exporter, _ = tracing(capture_content=False)
    with provider.get_tracer("t").start_as_current_span("llm") as span:
        span.set_attribute("input.value", "hello")
        span.set_attribute("output.value", "hi")
        span.set_attribute("llm.input_messages.0.message.content", "hello")
        span.set_attribute("gcp.vertex.agent.tool_call_args", "{}")
        span.set_attribute("llm.model_name", "gemini-3-flash-preview")
        span.set_attribute("llm.token_count.total", 42)
    (exported,) = _finished(provider, exporter)
    assert "input.value" not in exported.attributes
    assert "output.value" not in exported.attributes
    assert "llm.input_messages.0.message.content" not in exported.attributes
    assert "gcp.vertex.agent.tool_call_args" not in exported.attributes
    assert exported.attributes["llm.model_name"] == "gemini-3-flash-preview"
    assert exported.attributes["llm.token_count.total"] == 42


def test_mcp_protocol_noise_dropped(tracing):
    provider, exporter, _ = tracing()
    tracer = provider.get_tracer("mcp-python-sdk")
    for method in ("initialize", "server/discover", "tools/list", "ping", "notifications/initialized", "tools/call"):
        with tracer.start_as_current_span(f"MCP send {method}", attributes={"mcp.method.name": method}):
            pass
    names = [s.name for s in _finished(provider, exporter)]
    assert names == ["MCP send tools/call"]


def test_export_failure_is_logged_not_raised(caplog):
    class Boom(SpanExporter):
        def export(self, spans):
            raise RuntimeError("network down")

        def shutdown(self):
            pass

    exporter = FilteringMaskingExporter(Boom())
    provider = build_tracer_provider("svc", _settings(), exporter=InMemorySpanExporter())
    with provider.get_tracer("t").start_as_current_span("x") as span:
        readable = span
    with caplog.at_level(logging.WARNING, logger="sales_common.telemetry"):
        assert exporter.export([readable]) == SpanExportResult.FAILURE
    assert "network down" in caplog.text


# --- attributes on every span -----------------------------------------------------


def test_session_user_environment_release_stamped(tracing):
    provider, exporter, _ = tracing(environment="gcp", release="abc123")
    tracer = provider.get_tracer("t")
    token = context.attach(telemetry.turn_baggage_context("sess-1", "CUST-1"))
    try:
        with tracer.start_as_current_span("root"):
            with tracer.start_as_current_span("child"):
                pass
    finally:
        context.detach(token)
    spans = _finished(provider, exporter)
    assert len(spans) == 2
    for span in spans:
        assert span.attributes["langfuse.session.id"] == "sess-1"
        assert span.attributes["langfuse.user.id"] == "CUST-1"
        assert span.attributes["langfuse.environment"] == "gcp"
        assert span.attributes["langfuse.release"] == "abc123"
        assert span.resource.attributes["service.name"] == "test-service"


# --- propagation -------------------------------------------------------------------


async def test_httpx_hook_injects_traceparent_and_baggage(tracing):
    provider, _, _ = tracing()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), event_hooks={"request": [telemetry.ainject_trace_headers]}
    )
    token = context.attach(telemetry.turn_baggage_context("sess-9"))
    try:
        with provider.get_tracer("t").start_as_current_span("chat_turn") as span:
            await client.get("http://agent.local/")
            expected_trace = telemetry.trace_id_hex(span)
    finally:
        context.detach(token)
        await client.aclose()
    assert seen["traceparent"].split("-")[1] == expected_trace
    assert "langfuse.session.id=sess-9" in seen["baggage"]


async def test_httpx_hook_noop_when_disabled():
    telemetry.activate(None)
    request = httpx.Request("GET", "http://agent.local/")
    await telemetry.ainject_trace_headers(request)
    assert "traceparent" not in request.headers


def _asgi_app(tracer, seen):
    async def app(scope, receive, send):
        with tracer.start_as_current_span("agent_run") as span:
            seen["trace_id"] = telemetry.trace_id_hex(span)
            seen["session"] = (getattr(span, "attributes", None) or {}).get("langfuse.session.id")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    return app


async def _call(app, headers):
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {"type": "http", "method": "POST", "path": "/", "headers": headers}
    await app(scope, receive, send)
    return messages


async def test_middleware_extracts_incoming_context(tracing):
    provider, _, _ = tracing()
    seen = {}
    app = TraceContextMiddleware(_asgi_app(provider.get_tracer("t"), seen))
    await _call(app, [(b"traceparent", TRACEPARENT.encode()), (b"baggage", b"langfuse.session.id=sess-7")])
    assert seen == {"trace_id": TRACE_ID, "session": "sess-7"}


async def test_middleware_ignores_invalid_traceparent(tracing):
    provider, _, _ = tracing()
    seen = {}
    app = TraceContextMiddleware(_asgi_app(provider.get_tracer("t"), seen))
    messages = await _call(app, [(b"traceparent", b"garbage")])
    assert seen["trace_id"] and seen["trace_id"] != TRACE_ID
    assert messages[-1]["body"] == b"ok"


async def test_middleware_flushes_before_final_chunk(tracing, monkeypatch):
    provider, _, _ = tracing(flush_per_request=True)
    order = []

    async def fake_aflush(timeout_ms=None):
        order.append("flush")
        return True

    monkeypatch.setattr(telemetry, "aflush", fake_aflush)
    inner = _asgi_app(provider.get_tracer("t"), {})

    async def recording_app(scope, receive, send):
        async def rec_send(message):
            await send(message)

        await inner(scope, receive, rec_send)

    app = TraceContextMiddleware(recording_app)
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        order.append(message["type"])
        messages.append(message)

    await app({"type": "http", "headers": []}, receive, send)
    assert order == ["http.response.start", "flush", "http.response.body"]


async def test_middleware_passthrough_when_disabled():
    telemetry.activate(None)
    seen = {}
    app = TraceContextMiddleware(_asgi_app(trace.NoOpTracer(), seen))
    messages = await _call(app, [(b"traceparent", TRACEPARENT.encode())])
    assert messages[-1]["body"] == b"ok"
    assert seen["trace_id"] is None


def test_export_timeout_bounded_by_flush_budget_on_cloud_run():
    # force_flush does not cut a retrying export short, so the exporter itself must
    # give up within the per-request flush budget (Langfuse outage on Cloud Run).
    assert telemetry.export_timeout_seconds(_settings(flush_per_request=True, flush_timeout_ms=1500)) == 1.5
    assert telemetry.export_timeout_seconds(_settings(flush_per_request=True, flush_timeout_ms=100)) == 0.5
    assert telemetry.export_timeout_seconds(_settings(flush_per_request=False)) == 10.0


def test_base_url_preferred_over_host(monkeypatch):
    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com/")
    assert TelemetrySettings.from_env().host == "https://us.cloud.langfuse.com"
    monkeypatch.delenv("LANGFUSE_BASE_URL")
    assert TelemetrySettings.from_env().host == "https://cloud.langfuse.com"


def test_a2a_sdk_internal_spans_dropped(tracing):
    provider, exporter, _ = tracing()
    with provider.get_tracer("a2a-python-sdk").start_as_current_span("a2a.server.events.event_queue_v2.EventQueueSource.dequeue_event"):
        pass
    with provider.get_tracer("openinference.instrumentation.google_adk").start_as_current_span("agent_run [order_agent]"):
        pass
    assert [s.name for s in _finished(provider, exporter)] == ["agent_run [order_agent]"]
