"""Distributed tracing to Langfuse (OpenTelemetry, OTLP over HTTP).

Every service calls :func:`init_telemetry` once at startup (``create_a2a_app``,
the tool-service apps and the gateway do this). Tracing is **off** unless both
``LANGFUSE_PUBLIC_KEY`` and ``LANGFUSE_SECRET_KEY`` are set (and
``OTEL_SDK_DISABLED`` is not true); then spans are exported to
``{LANGFUSE_BASE_URL or LANGFUSE_HOST}/api/public/otel/v1/traces``.

Span sources:

* ADK agents, model calls, tool calls and workflow nodes, via
  ``openinference.instrumentation.google_adk.GoogleADKInstrumentor`` (input,
  output, model, token usage; it suppresses ADK's duplicate native spans)
* MCP ``tools/call`` spans from the ``mcp`` SDK (client and server; trace
  context travels in the JSON-RPC ``_meta`` field)
* the gateway's ``chat_turn`` root span and suggestion generation

Propagation: the gateway's A2A httpx client injects ``traceparent`` and
``baggage`` (:func:`inject_trace_headers`); services extract them in
:class:`TraceContextMiddleware`. The baggage carries only the conversation's
``langfuse.session.id`` and ``langfuse.user.id``; :class:`LangfuseAttributesProcessor`
stamps them, the environment and the release on every span.

:class:`FilteringMaskingExporter` masks payment data, optionally drops all
content (``LANGFUSE_CAPTURE_CONTENT=false``) and drops MCP protocol spans (all but ``tools/call``, ``resources/read``, ``prompts/get``)
before export. Export failures are logged, never raised.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from google.adk.plugins.base_plugin import BasePlugin
from opentelemetry import baggage, context, propagate, trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, ReadableSpan, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Status

from .config import env_bool, env_int, env_str

logger = logging.getLogger("sales_common.telemetry")

DEFAULT_HOST = "https://us.cloud.langfuse.com"
OTLP_TRACES_PATH = "/api/public/otel/v1/traces"
SESSION_KEY = "langfuse.session.id"
USER_KEY = "langfuse.user.id"
BAGGAGE_KEYS = (SESSION_KEY, USER_KEY)
_ENVIRONMENT_RE = re.compile(r"^(?!langfuse)[a-z0-9_-]{1,40}$")


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #


def langfuse_host() -> str:
    """``LANGFUSE_BASE_URL`` (Langfuse's current name) or ``LANGFUSE_HOST``; default US cloud."""
    return (env_str("LANGFUSE_BASE_URL", "") or env_str("LANGFUSE_HOST", DEFAULT_HOST)).rstrip("/")


@dataclass(frozen=True)
class TelemetrySettings:
    host: str
    public_key: str
    secret_key: str
    environment: str
    release: str
    capture_content: bool
    flush_per_request: bool
    flush_timeout_ms: int
    disabled: bool = False

    @property
    def enabled(self) -> bool:
        return bool(self.public_key and self.secret_key) and not self.disabled

    @property
    def traces_endpoint(self) -> str:
        return self.host.rstrip("/") + OTLP_TRACES_PATH

    @property
    def auth_header(self) -> str:
        token = base64.b64encode(f"{self.public_key}:{self.secret_key}".encode()).decode()
        return f"Basic {token}"

    @classmethod
    def from_env(cls) -> "TelemetrySettings":
        environment = env_str("LANGFUSE_TRACING_ENVIRONMENT", "local").lower()
        if not _ENVIRONMENT_RE.match(environment):
            logger.warning("LANGFUSE_TRACING_ENVIRONMENT=%r is not a valid Langfuse environment; using 'local'", environment)
            environment = "local"
        return cls(
            host=langfuse_host(),
            public_key=env_str("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=env_str("LANGFUSE_SECRET_KEY", ""),
            environment=environment,
            release=env_str("LANGFUSE_RELEASE", ""),
            capture_content=env_bool("LANGFUSE_CAPTURE_CONTENT", True),
            flush_per_request=env_bool("TELEMETRY_FLUSH_PER_REQUEST", False),
            flush_timeout_ms=env_int("TELEMETRY_FLUSH_TIMEOUT_MS", 5000),
            disabled=env_bool("OTEL_SDK_DISABLED", False),
        )


# --------------------------------------------------------------------------- #
# Masking and filtering
# --------------------------------------------------------------------------- #

REDACTED_CARD = "[REDACTED_CARD]"
REDACTED_CVV = "[REDACTED_CVV]"
REDACTED_ACCOUNT = "[REDACTED_ACCOUNT]"

# A run of digits with single space/dash separators; candidates are checked in code.
_DIGIT_RUN_RE = re.compile(r"(?<![\d-])\d(?:[ -]?\d){12,}(?!\d)")
_SEP_RE = re.compile(r"([ -])")
_CVV_RE = re.compile(
    r"(?i)\b(cvv2?|cvc2?|security[\s_-]*code)\b([\s\"':=]*(?:is\s+)?[\s\"':=]*)(\d{3,4})(?!\d)"
)
_ACCOUNT_RE = re.compile(
    r"(?i)\b(account[\s_-]*(?:number|num|no\.?|#)|routing[\s_-]*(?:number|num|no\.?|#)|acct\.?|aba)"
    r"([\s\"':=#]*(?:is\s+)?[\s\"':=#]*)(\d{6,17})(?!\d)"
)


def _luhn_valid(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _mask_digit_run(match: re.Match) -> str:
    """Replace the longest Luhn-valid 13-19 digit group sequences in a digit run."""
    parts = _SEP_RE.split(match.group(0))
    groups, seps = parts[0::2], parts[1::2]
    out: list[str] = []
    i = 0
    while i < len(groups):
        hit = None
        for j in range(len(groups) - 1, i - 1, -1):
            digits = "".join(groups[i : j + 1])
            if 13 <= len(digits) <= 19 and _luhn_valid(digits):
                hit = j
                break
        end = i if hit is None else hit
        out.append(groups[i] if hit is None else REDACTED_CARD)
        if end < len(seps):
            out.append(seps[end])
        i = end + 1
    return "".join(out)


def mask_text(text: str) -> str:
    """Mask card numbers (Luhn-checked), card security codes and account/routing numbers."""
    if not text or not any(ch.isdigit() for ch in text):
        return text
    text = _DIGIT_RUN_RE.sub(_mask_digit_run, text)
    text = _CVV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED_CVV}", text)
    return _ACCOUNT_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED_ACCOUNT}", text)


CONTENT_KEYS = frozenset(
    {
        "input.value",
        "output.value",
        "gcp.vertex.agent.llm_request",
        "gcp.vertex.agent.llm_response",
        "gcp.vertex.agent.tool_call_args",
        "gcp.vertex.agent.tool_response",
        "gcp.vertex.agent.data",
        "langfuse.observation.input",
        "langfuse.observation.output",
        "langfuse.trace.input",
        "langfuse.trace.output",
        "gen_ai.prompt",
        "gen_ai.completion",
        "gen_ai.input.messages",
        "gen_ai.output.messages",
        "gen_ai.system_instructions",
    }
)
CONTENT_PREFIXES = ("llm.input_messages.", "llm.output_messages.", "llm.prompts.", "gen_ai.prompt.", "gen_ai.completion.")
# MCP spans worth exporting: requests that do work. Every other MCP method (initialize,
# server/discover, tools/list, ping, notifications/*, ...) is protocol noise.
WORK_MCP_METHODS = frozenset({"tools/call", "resources/read", "prompts/get"})


def is_content_key(key: str) -> bool:
    return key in CONTENT_KEYS or key.startswith(CONTENT_PREFIXES)


# Tracers whose spans are SDK plumbing, not agent behaviour: a2a-sdk traces every
# event-queue/task-manager method (~60 spans per turn), which buries the agent tree.
NOISE_SCOPES = frozenset({"a2a-python-sdk"})


def is_noise_span(span: ReadableSpan) -> bool:
    scope = getattr(span, "instrumentation_scope", None)
    if scope is not None and scope.name in NOISE_SCOPES:
        return True
    method = (span.attributes or {}).get("mcp.method.name")
    return isinstance(method, str) and method not in WORK_MCP_METHODS


def _clean_value(value: Any) -> Any:
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, (list, tuple)) and value and all(isinstance(v, str) for v in value):
        return tuple(mask_text(v) for v in value)
    return value


def clean_attributes(attributes: Optional[Mapping[str, Any]], capture_content: bool) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in (attributes or {}).items():
        if not capture_content and is_content_key(key):
            continue
        cleaned[key] = _clean_value(value)
    return cleaned


class FilteringMaskingExporter(SpanExporter):
    """Wraps an exporter: drops MCP protocol noise, masks payment data, optionally drops content."""

    def __init__(self, inner: SpanExporter, *, capture_content: bool = True):
        self._inner = inner
        self._capture_content = capture_content

    def _clean(self, span: ReadableSpan) -> ReadableSpan:
        status = span.status
        if status is not None and status.description:
            status = Status(status.status_code, mask_text(status.description))
        events = [
            Event(e.name, clean_attributes(e.attributes, self._capture_content), e.timestamp)
            for e in span.events
        ]
        return ReadableSpan(
            name=span.name,
            context=span.context,
            parent=span.parent,
            resource=span.resource,
            attributes=clean_attributes(span.attributes, self._capture_content),
            events=events,
            links=span.links,
            kind=span.kind,
            status=status,
            start_time=span.start_time,
            end_time=span.end_time,
            instrumentation_scope=span.instrumentation_scope,
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            cleaned = [self._clean(s) for s in spans if not is_noise_span(s)]
            if not cleaned:
                return SpanExportResult.SUCCESS
            result = self._inner.export(cleaned)
            if result != SpanExportResult.SUCCESS:
                logger.warning("Span export failed: %d span(s) not delivered (%s)", len(cleaned), result.name)
            return result
        except Exception as exc:  # never let telemetry break the service
            logger.warning("Span export failed: %s: %s", type(exc).__name__, exc)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        try:
            self._inner.shutdown()
        except Exception as exc:
            logger.warning("Span exporter shutdown failed: %s", exc)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        flush = getattr(self._inner, "force_flush", None)
        return flush(timeout_millis) if flush else True


# --------------------------------------------------------------------------- #
# Attributes on every span
# --------------------------------------------------------------------------- #


class LangfuseAttributesProcessor(SpanProcessor):
    """Stamps environment, release and the baggage session/user ids on every span."""

    def __init__(self, environment: str, release: str = ""):
        self._environment = environment
        self._release = release

    def on_start(self, span, parent_context=None) -> None:
        span.set_attribute("langfuse.environment", self._environment)
        if self._release:
            span.set_attribute("langfuse.release", self._release)
        for key in BAGGAGE_KEYS:
            value = baggage.get_baggage(key, parent_context)
            if value:
                span.set_attribute(key, str(value))

    def on_end(self, span) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


# --------------------------------------------------------------------------- #
# Provider lifecycle
# --------------------------------------------------------------------------- #

_lock = threading.Lock()
_initialized = False
_provider: Optional[TracerProvider] = None
_settings: Optional[TelemetrySettings] = None


def export_timeout_seconds(settings: TelemetrySettings) -> float:
    """Exporter time budget, retries included.

    ``force_flush(timeout)`` does not cut short an export that is retrying, so
    with per-request flushing the exporter itself must give up within the flush
    budget; otherwise a Langfuse outage would delay every response by ~10 s.
    """
    if settings.flush_per_request:
        return max(0.5, settings.flush_timeout_ms / 1000)
    return 10.0


def build_tracer_provider(
    service_name: str, settings: TelemetrySettings, exporter: Optional[SpanExporter] = None
) -> TracerProvider:
    """Tracer provider with the Langfuse attribute processor and the masking exporter.

    ``exporter`` defaults to OTLP/HTTP to Langfuse; tests pass an in-memory exporter.
    """
    if exporter is None:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(
            endpoint=settings.traces_endpoint,
            headers={"Authorization": settings.auth_header, "x-langfuse-ingestion-version": "4"},
            timeout=export_timeout_seconds(settings),
        )
    resource = Resource.create({"service.name": service_name, "service.version": settings.release or "dev"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(LangfuseAttributesProcessor(settings.environment, settings.release))
    provider.add_span_processor(
        BatchSpanProcessor(FilteringMaskingExporter(exporter, capture_content=settings.capture_content))
    )
    return provider


def activate(provider: Optional[TracerProvider], settings: Optional[TelemetrySettings] = None) -> None:
    """Make ``provider`` this module's active provider (``None`` deactivates).

    :func:`init_telemetry` calls this after installing the global provider. Tests
    use it to enable tracing with an in-memory exporter without touching the
    process-wide OpenTelemetry provider.
    """
    global _provider, _settings
    _provider = provider
    _settings = settings if provider is not None else None


def _instrument_adk(provider: TracerProvider) -> None:
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        instrumentor = GoogleADKInstrumentor()
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument(tracer_provider=provider)
    except Exception as exc:  # degrade to ADK-native spans rather than fail startup
        logger.warning("ADK instrumentation unavailable (%s: %s); using ADK native spans", type(exc).__name__, exc)


def init_telemetry(service_name: str) -> bool:
    """Install tracing for this process once. Returns whether tracing is enabled."""
    global _initialized
    with _lock:
        if _initialized:
            return enabled()
        _initialized = True
        settings = TelemetrySettings.from_env()
        if not settings.enabled:
            logger.info("Tracing disabled for %s (Langfuse keys not set or OTEL_SDK_DISABLED)", service_name)
            return False
        provider = build_tracer_provider(service_name, settings)
        trace.set_tracer_provider(provider)
        activate(provider, settings)
        _instrument_adk(provider)
        logger.info(
            "Tracing %s to %s (environment=%s, capture_content=%s)",
            service_name,
            settings.host,
            settings.environment,
            settings.capture_content,
        )
        return True


def enabled() -> bool:
    return _provider is not None


def settings() -> Optional[TelemetrySettings]:
    return _settings


def get_tracer(name: str = "sales_common") -> trace.Tracer:
    """Tracer on the active provider, or a no-op tracer when tracing is off."""
    if _provider is None:
        return trace.NoOpTracer()
    return _provider.get_tracer(name)


def flush(timeout_ms: Optional[int] = None) -> bool:
    """Export pending spans now (bounded). Never raises."""
    provider = _provider
    if provider is None:
        return True
    timeout = timeout_ms if timeout_ms is not None else (_settings.flush_timeout_ms if _settings else 5000)
    try:
        done = provider.force_flush(timeout)
        if not done:
            logger.warning("Span flush did not finish within %d ms; spans may be delayed or lost", timeout)
        return done
    except Exception as exc:
        logger.warning("Span flush failed: %s", exc)
        return False


async def aflush(timeout_ms: Optional[int] = None) -> bool:
    if _provider is None:
        return True
    return await asyncio.to_thread(flush, timeout_ms)


class TelemetryFlushPlugin(BasePlugin):
    """ADK plugin: flush spans when an agent run ends, while the A2A request is still open.

    The per-request flush in :class:`TraceContextMiddleware` runs on the final
    response chunk, which can come after (or without) the run's spans being
    exported; on Cloud Run the CPU is throttled once the response ends, so spans
    left in the batch queue are lost. Flushing here delivers the run's agent,
    model and tool spans first (spec: agent-observability).
    """

    def __init__(self) -> None:
        super().__init__(name="telemetry_flush")

    async def after_run_callback(self, *, invocation_context) -> None:
        await aflush()
        return None


def shutdown_telemetry() -> None:
    """Flush and shut down the provider (application shutdown)."""
    provider = _provider
    if provider is None:
        return
    try:
        provider.shutdown()
    except Exception as exc:
        logger.warning("Tracer provider shutdown failed: %s", exc)


# --------------------------------------------------------------------------- #
# Context helpers
# --------------------------------------------------------------------------- #


def trace_id_hex(span: Optional[trace.Span] = None) -> Optional[str]:
    """32-hex trace id of ``span`` (default: the current span), or ``None``."""
    span_context = (span or trace.get_current_span()).get_span_context()
    if not span_context.is_valid:
        return None
    return format(span_context.trace_id, "032x")


def current_trace_id() -> Optional[str]:
    return trace_id_hex()


def turn_baggage_context(
    session_id: str, user_id: Optional[str] = None, ctx: Optional[context.Context] = None
) -> context.Context:
    """Context carrying the conversation's session and user ids as baggage."""
    ctx = baggage.set_baggage(SESSION_KEY, str(session_id), ctx)
    if user_id:
        ctx = baggage.set_baggage(USER_KEY, str(user_id), ctx)
    return ctx


def inject_trace_headers(request) -> None:
    """httpx request event hook: add ``traceparent``/``baggage`` for our own services."""
    if _provider is None:
        return
    try:
        propagate.inject(request.headers)
    except Exception as exc:
        logger.warning("Trace header injection failed: %s", exc)


async def ainject_trace_headers(request) -> None:
    """Async variant of :func:`inject_trace_headers` for ``httpx.AsyncClient``."""
    inject_trace_headers(request)


class TraceContextMiddleware:
    """ASGI middleware: extract incoming trace context; optionally flush per request.

    With ``TELEMETRY_FLUSH_PER_REQUEST=true`` pending spans are exported before
    the final response chunk is sent, so they are delivered even when Cloud Run
    throttles CPU after the response.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or _provider is None:
            await self.app(scope, receive, send)
            return
        carrier: dict[str, str] = {}
        for raw_key, raw_value in scope.get("headers") or []:
            key = raw_key.decode("latin-1").lower()
            if key in ("traceparent", "tracestate", "baggage"):
                carrier[key] = raw_value.decode("latin-1")
        try:
            ctx = propagate.extract(carrier) if carrier else context.get_current()
        except Exception as exc:
            logger.warning("Ignoring invalid trace headers: %s", exc)
            ctx = context.get_current()

        downstream_send = send
        if _settings is not None and _settings.flush_per_request:

            async def flushing_send(message):
                if message.get("type") == "http.response.body" and not message.get("more_body", False):
                    await aflush()
                await send(message)

            downstream_send = flushing_send

        token = context.attach(ctx)
        try:
            await self.app(scope, receive, downstream_send)
        finally:
            try:
                context.detach(token)
            except Exception:  # detached from another context (client disconnect)
                pass
