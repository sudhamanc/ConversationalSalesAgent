"""Span delivery (spec: agent-observability "Span delivery on Cloud Run and at shutdown")."""

import asyncio
import logging

from google.adk import Agent
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from sales_common import a2a_server, telemetry
from sales_common.telemetry import FilteringMaskingExporter, TelemetryFlushPlugin, TelemetrySettings


class _Failing(SpanExporter):
    def export(self, spans):
        return SpanExportResult.FAILURE


class _Span:
    def __init__(self):
        from opentelemetry.sdk.trace import TracerProvider

        with TracerProvider().get_tracer("t").start_as_current_span("s") as span:
            self.span = span


def test_failed_export_is_logged(caplog):
    exporter = FilteringMaskingExporter(_Failing())
    with caplog.at_level(logging.WARNING, logger="sales_common.telemetry"):
        assert exporter.export([_Span().span]) == SpanExportResult.FAILURE
    assert "1 span(s) not delivered" in caplog.text


def test_flush_timeout_is_logged(caplog, monkeypatch):
    class SlowProvider:
        def force_flush(self, timeout):
            return False

    monkeypatch.setattr(telemetry, "_provider", SlowProvider())
    with caplog.at_level(logging.WARNING, logger="sales_common.telemetry"):
        assert telemetry.flush(10) is False
    assert "did not finish within 10 ms" in caplog.text


def test_default_flush_timeout(monkeypatch):
    monkeypatch.delenv("TELEMETRY_FLUSH_TIMEOUT_MS", raising=False)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    assert TelemetrySettings.from_env().flush_timeout_ms == 5000


def test_plugin_flushes_after_run(monkeypatch):
    calls = []

    async def fake_aflush(timeout_ms=None):
        calls.append(timeout_ms)
        return True

    monkeypatch.setattr(telemetry, "aflush", fake_aflush)
    asyncio.run(TelemetryFlushPlugin().after_run_callback(invocation_context=None))
    assert calls == [None]


def _settings(flush):
    return TelemetrySettings(
        host="https://lf.example", public_key="pk", secret_key="sk", environment="test", release="",
        capture_content=True, flush_per_request=flush, flush_timeout_ms=500,
    )


def _plugins_for(monkeypatch, flush):
    monkeypatch.setenv("PUBLIC_URL", "http://localhost:8299")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u@127.0.0.1:1/unused")
    monkeypatch.delenv("SESSION_DB_URL", raising=False)
    monkeypatch.setattr(telemetry, "settings", lambda: _settings(flush))
    seen = {}
    real = a2a_server.build_app

    def capture(name, agent, plugins=None, **kw):
        seen["plugins"] = list(plugins or [])
        return real(name, agent, plugins=plugins, **kw)

    monkeypatch.setattr(a2a_server, "build_app", capture)
    a2a_server.create_a2a_app(Agent(name=f"flush_{flush}_agent", model="gemini-test", instruction="t"))
    return seen["plugins"]


def test_agent_service_adds_flush_plugin_on_cloud_run(monkeypatch):
    assert any(isinstance(p, TelemetryFlushPlugin) for p in _plugins_for(monkeypatch, True))
    assert not any(isinstance(p, TelemetryFlushPlugin) for p in _plugins_for(monkeypatch, False))
