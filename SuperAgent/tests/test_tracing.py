"""Gateway tracing: ``chat_turn`` span, ``done.trace_id``/``feedback_token`` and ``POST /api/feedback``.

No database (revocation check stubbed, no app lifespan) and no network
(in-memory span exporter, fake Langfuse client).
"""

from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient
from google.adk.sessions import InMemorySessionService
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from sales_common import telemetry
from sales_common.telemetry import TelemetrySettings, build_tracer_provider

CLIENT_ID = "0b7c9a4e-8f1d-4c2a-9d3e-2f6a7b8c9d0e"
MESSAGE = "We're Crane.io at 123 Main St, Philadelphia PA 19103"


@pytest.fixture
def gateway(monkeypatch):
    from middleware.auth import SessionAuthenticator

    monkeypatch.setattr(SessionAuthenticator, "is_revoked", staticmethod(lambda session_id: False))
    import runtime
    from fakes import build_fake_agents, router
    from super_agent.agent import build_gateway_app

    runtime.init_runtime(
        app=build_gateway_app(agents=build_fake_agents(), router_model=router("discovery_agent")),
        session_service=InMemorySessionService(),
        memory_service=None,
    )
    runtime.get_runner().memory_service = None
    import main

    yield TestClient(main.app)  # no lifespan: no database
    runtime._runner = None


@pytest.fixture
def tracing(monkeypatch):
    # conftest sets OTEL_SDK_DISABLED (no export from tests); the SDK provider honours it too.
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    settings = TelemetrySettings(
        host="https://lf.example", public_key="pk", secret_key="sk", environment="local", release="",
        capture_content=True, flush_per_request=False, flush_timeout_ms=500,
    )
    exporter = InMemorySpanExporter()
    provider = build_tracer_provider("gateway", settings, exporter=exporter)
    telemetry.activate(provider, settings)
    yield provider, exporter
    telemetry.activate(None)


class FakeLangfuse:
    def __init__(self):
        self.scores = []

    async def create_score(self, **kwargs):
        self.scores.append(kwargs)


@pytest.fixture
def langfuse(monkeypatch):
    import api.feedback as feedback

    fake = FakeLangfuse()
    monkeypatch.setattr(feedback.LangfuseClient, "from_env", classmethod(lambda cls: fake))
    feedback.feedback_limiter = type(feedback.feedback_limiter)()  # fresh buckets per test
    return fake


def _session(client) -> dict:
    return client.post("/api/session", json={"client_id": CLIENT_ID}).json()


def _chat(client, token: str, message: str = MESSAGE):
    response = client.post("/api/chat", json={"message": message}, headers={"Authorization": f"Bearer {token}"})
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    return response, events


def _turn_span(provider, exporter):
    provider.force_flush()
    (span,) = [s for s in exporter.get_finished_spans() if s.name == "chat_turn"]
    return span


# --- chat_turn and done ---------------------------------------------------------


def test_done_carries_trace_id_of_chat_turn(gateway, tracing):
    provider, exporter = tracing
    session = _session(gateway)
    response, events = _chat(gateway, session["token"])
    done = events[-1]
    assert done["type"] == "done"
    assert re.fullmatch(r"[0-9a-f]{32}", done["trace_id"])
    assert done["feedback_token"]

    span = _turn_span(provider, exporter)
    assert format(span.context.trace_id, "032x") == done["trace_id"]
    assert span.attributes["langfuse.session.id"] == response.headers["X-Session-Id"]
    assert span.attributes["langfuse.user.id"]
    assert span.attributes["langfuse.trace.name"] == "chat_turn"
    assert span.attributes["langfuse.observation.input"] == MESSAGE
    assert span.attributes["langfuse.observation.output"]
    tags = list(span.attributes["langfuse.trace.tags"])
    assert tags[:2] == ["discovery_agent", "serviceability_agent"] and "handoff" in tags
    assert span.attributes["langfuse.trace.metadata.handoff_hops"] == 1
    assert span.status.status_code != StatusCode.ERROR


def test_done_unchanged_when_tracing_off(gateway):
    telemetry.activate(None)
    _, events = _chat(gateway, _session(gateway)["token"])
    assert events[-1] == {"type": "done"}


def test_failed_turn_marks_span_error(gateway, tracing, monkeypatch):
    import runtime

    async def broken(**kwargs):
        raise RuntimeError("agent down")
        yield  # pragma: no cover

    monkeypatch.setattr(runtime.get_runner(), "run_async", broken)
    provider, exporter = tracing
    _, events = _chat(gateway, _session(gateway)["token"])
    assert [e["type"] for e in events] == ["error", "done"]
    span = _turn_span(provider, exporter)
    assert span.status.status_code == StatusCode.ERROR
    assert "error" in span.attributes["langfuse.trace.tags"]
    assert format(span.context.trace_id, "032x") == events[-1]["trace_id"]


# --- POST /api/feedback ---------------------------------------------------------


def _feedback(client, token: str, body) -> int:
    return client.post("/api/feedback", json=body, headers={"Authorization": f"Bearer {token}"}).status_code


def _traced_turn(client):
    session = _session(client)
    _, events = _chat(client, session["token"])
    return session, events[-1]


def test_feedback_records_score_and_revote_updates_it(gateway, tracing, langfuse):
    session, done = _traced_turn(gateway)
    body = {"trace_id": done["trace_id"], "feedback_token": done["feedback_token"], "value": "down"}
    assert _feedback(gateway, session["token"], body) == 204
    assert _feedback(gateway, session["token"], {**body, "value": "up"}) == 204

    first, second = langfuse.scores
    assert first["name"] == "user_feedback" and first["data_type"] == "BOOLEAN"
    assert first["trace_id"] == done["trace_id"] and first["value"] == 0 and second["value"] == 1
    assert first["environment"] == "local"
    # same id and timestamp: Langfuse updates the score instead of adding one
    assert first["score_id"] == second["score_id"] and first["timestamp"] == second["timestamp"]


def test_feedback_rejects_bad_session(gateway, tracing, langfuse):
    assert _feedback(gateway, "nope", {}) == 401


def test_feedback_404_when_tracing_off(gateway, langfuse):
    telemetry.activate(None)
    assert _feedback(gateway, _session(gateway)["token"], {}) == 404


@pytest.mark.parametrize(
    "body",
    [
        [],
        {"trace_id": "xyz", "feedback_token": "t", "value": "up"},
        {"trace_id": "a" * 32, "feedback_token": 5, "value": "up"},
        {"trace_id": "a" * 32, "feedback_token": "t", "value": "meh"},
    ],
)
def test_feedback_rejects_malformed_body(gateway, tracing, langfuse, body):
    assert _feedback(gateway, _session(gateway)["token"], body) == 400


def test_feedback_token_from_another_session_is_forbidden(gateway, tracing, langfuse):
    _, done = _traced_turn(gateway)
    other = _session(gateway)
    body = {"trace_id": done["trace_id"], "feedback_token": done["feedback_token"], "value": "up"}
    assert _feedback(gateway, other["token"], body) == 403
    assert langfuse.scores == []


def test_feedback_token_for_another_trace_is_forbidden(gateway, tracing, langfuse):
    session, done = _traced_turn(gateway)
    body = {"trace_id": "b" * 32, "feedback_token": done["feedback_token"], "value": "up"}
    assert _feedback(gateway, session["token"], body) == 403


# --- suggestions generation span --------------------------------------------------


def test_suggestions_call_is_a_generation_span(tracing, monkeypatch):
    from types import SimpleNamespace

    from api import suggestions

    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(
                text='{"suggestions": ["Get a quote", "Check coverage", "Compare plans"]}',
                usage_metadata=SimpleNamespace(prompt_token_count=40, candidates_token_count=12, total_token_count=52),
            )

    monkeypatch.setattr("google.genai.Client", lambda *a, **k: SimpleNamespace(models=FakeModels()))
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    provider, exporter = tracing
    assert suggestions.generate_suggestions("hi", "hello there", "product_agent") == [
        "Get a quote", "Check coverage", "Compare plans"
    ]
    provider.force_flush()
    (span,) = [s for s in exporter.get_finished_spans() if s.name == "generate_suggestions"]
    assert span.attributes["openinference.span.kind"] == "LLM"
    assert span.attributes["llm.model_name"] == "gemini-test"
    assert span.attributes["llm.token_count.total"] == 52
    assert "Get a quote" in span.attributes["output.value"]
