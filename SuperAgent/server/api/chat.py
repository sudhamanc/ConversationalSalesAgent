"""POST /api/chat – SSE streaming chat endpoint.

Flow:
1. Verify the signed Bearer session token (any gateway instance can verify it).
2. Apply the per-instance rate limit.
3. Run one turn of the ``sales_journey`` workflow (router -> remote A2A agent ->
   deterministic handoffs) with durable PostgreSQL sessions.
4. Map workflow events to SSE payloads (``api/sse.py``).
5. After the stream completes, add the session to long-term memory.

With tracing on (``sales_common.telemetry``), each turn is one Langfuse trace
rooted at the ``chat_turn`` span, and ``done`` carries ``trace_id`` and
``feedback_token`` (``api/feedback.py``).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from google.genai import types
from opentelemetry import context as otel_context
from opentelemetry.trace import Status, StatusCode

from api.feedback import issue_feedback_token
from api.sse import EventMapper
from api.suggestions import generate_suggestions
from middleware.auth import Session, get_authenticator
from middleware.rate_limiter import rate_limiter
from runtime import app_name, ensure_adk_session, get_runner
from sales_common import telemetry
from super_agent.config import settings
from super_agent.registry import display_name
from utils.logger import get_logger, session_id_var

logger = get_logger(__name__)
router = APIRouter()

_MAX_RETRIES = 3
_RETRY_DELAYS = [2, 5, 10]
_FALLBACK_TEXT = "I'm ready to assist you! How can I help with your business telecommunications needs today?"
_ACTIVATION_SUGGESTIONS = ["Simulate install day", "Show order details", "Send installation confirmation"]
_background_tasks: set[asyncio.Task] = set()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


def _is_retryable(error: str) -> bool:
    return any(code in error for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))


def _unavailable_message(target: str | None) -> str:
    service = display_name(target) if target else "assistant"
    return f"The {service} service is temporarily unavailable. Please try again in a moment."


async def _save_to_memory(user_id: str, session_id: str) -> None:
    runner = get_runner()
    if runner.memory_service is None:
        return
    try:
        session = await runner.session_service.get_session(
            app_name=app_name(), user_id=user_id, session_id=session_id
        )
        if session:
            await runner.memory_service.add_session_to_memory(session)
    except Exception as exc:  # memory is best effort and must not affect the chat
        logger.warning("Saving session to memory failed: %s", type(exc).__name__)


def _schedule_memory_save(user_id: str, session_id: str) -> None:
    task = asyncio.create_task(_save_to_memory(user_id, session_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@dataclass
class _TurnRecord:
    """What happened in a turn, for the ``chat_turn`` trace span."""

    mapper: Optional[EventMapper] = None
    attempts: int = 0
    error: Optional[str] = None


def _trace_user(adk_session, session: Session) -> str:
    """Langfuse user: the customer id once known, otherwise the browser user id."""
    state = getattr(adk_session, "state", None) or {}
    return str(state.get("user:customer_id") or session.user_id)


def _annotate_turn(span, user_message: str, record: _TurnRecord) -> None:
    mapper = record.mapper
    agents = list(mapper.agents) if mapper else []
    tags = agents + (["handoff"] if len(agents) > 1 else []) + (["error"] if record.error else [])
    span.set_attribute("langfuse.observation.output", "".join(mapper.response_parts) if mapper else "")
    span.set_attribute("langfuse.trace.tags", tags)
    span.set_attribute("langfuse.trace.metadata.answering_agents", ",".join(agents))
    span.set_attribute("langfuse.trace.metadata.route_target", (mapper.current_target if mapper else None) or "")
    span.set_attribute("langfuse.trace.metadata.handoff_hops", max(len(agents) - 1, 0))
    span.set_attribute("langfuse.trace.metadata.attempts", record.attempts)
    if record.error:
        span.set_status(Status(StatusCode.ERROR, record.error[:300]))


async def stream_turn(session: Session, user_message: str) -> AsyncIterator[str]:
    """Run one workflow turn and yield SSE lines.

    With tracing on (``sales_common.telemetry``) the turn is the root span
    ``chat_turn``: the conversation's session and user ride along as baggage to
    every agent and tool service, and ``done`` carries the turn's ``trace_id``
    and a ``feedback_token`` for ``POST /api/feedback``.
    """
    adk_session = await ensure_adk_session(session.user_id, session.session_id)
    if not telemetry.enabled():
        async for line in _run_turn(session, user_message, _TurnRecord(), {"type": "done"}):
            yield line
        return

    record = _TurnRecord()
    token = otel_context.attach(
        telemetry.turn_baggage_context(session.session_id, _trace_user(adk_session, session))
    )
    try:
        with telemetry.get_tracer("gateway").start_as_current_span("chat_turn") as span:
            trace_id = telemetry.trace_id_hex(span)
            span.set_attribute("langfuse.trace.name", "chat_turn")
            span.set_attribute("langfuse.observation.input", user_message)
            done = {"type": "done"}
            if trace_id:
                done.update(trace_id=trace_id, feedback_token=issue_feedback_token(session.session_id, trace_id))
            async for line in _run_turn(session, user_message, record, done):
                yield line
            _annotate_turn(span, user_message, record)
    finally:
        try:
            otel_context.detach(token)
        except Exception:  # generator closed from another context (client disconnect)
            pass


async def _run_turn(session: Session, user_message: str, record: _TurnRecord, done: dict) -> AsyncIterator[str]:
    """The workflow turn with retries; ``record`` collects the outcome, ``done`` is the final event."""
    runner = get_runner()
    new_message = types.Content(role="user", parts=[types.Part(text=user_message)])

    for attempt in range(_MAX_RETRIES):
        mapper = EventMapper()
        record.mapper = mapper
        record.attempts = attempt + 1
        try:
            async for event in runner.run_async(
                user_id=session.user_id, session_id=session.session_id, new_message=new_message
            ):
                if event.error_message:
                    if mapper.sent_text and "Unknown error" in event.error_message:
                        continue
                    if not mapper.domain_events_seen and _is_retryable(event.error_message) and attempt < _MAX_RETRIES - 1:
                        raise _Retry(event.error_message)
                    logger.error("Agent error from %s: %s", event.author, event.error_message)
                    record.error = f"{event.author}: {event.error_message}"
                    yield _sse({"type": "error", "content": _unavailable_message(mapper.current_target)})
                    yield _sse(done)
                    return
                for payload in mapper.consume(event):
                    yield _sse(payload)
        except _Retry as retry:
            delay = _RETRY_DELAYS[attempt]
            logger.warning("Retryable error (attempt %d/%d), retrying in %ds: %s", attempt + 1, _MAX_RETRIES, delay, str(retry)[:120])
            await asyncio.sleep(delay)
            continue
        except Exception as exc:
            error = str(exc)
            if not mapper.domain_events_seen and _is_retryable(error) and attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_DELAYS[attempt])
                continue
            logger.error("Turn failed (target=%s): %s: %s", mapper.current_target, type(exc).__name__, error[:300])
            record.error = f"{type(exc).__name__}: {error}"
            if not mapper.sent_text:
                yield _sse({"type": "error", "content": _unavailable_message(mapper.current_target)})
            yield _sse(done)
            return

        # --- turn completed ---
        if not mapper.sent_text:
            logger.warning("Empty response from workflow; sending fallback text")
            yield _sse({"type": "token", "content": _FALLBACK_TEXT, "author": "agent"})
        elif settings.server.suggestions_enabled:
            if mapper.provisioning_done:
                suggestions = _ACTIVATION_SUGGESTIONS
            else:
                suggestions = await asyncio.to_thread(
                    generate_suggestions, user_message, "".join(mapper.response_parts), mapper.last_text_author
                )
            if suggestions:
                yield _sse({"type": "suggestions", "author": mapper.last_text_author or "agent", "data": suggestions})
        yield _sse(done)
        _schedule_memory_save(session.user_id, session.session_id)
        return


class _Retry(Exception):
    pass


def _error_response(message: str, status: int) -> StreamingResponse:
    return StreamingResponse(iter([_sse({"type": "error", "content": message})]), media_type="text/event-stream", status_code=status)


@router.post("/api/chat")
async def chat(request: Request, authorization: str = Header(default="")):
    """SSE chat. Body ``{"message": "..."}``; header ``Authorization: Bearer <token>``."""
    session = get_authenticator().validate_token(authorization.removeprefix("Bearer ").strip())
    if not session:
        return _error_response("Invalid or expired session. Please refresh.", 401)
    session_id_var.set(session.session_id)

    if not rate_limiter.allow(session.session_id):
        return _error_response("Rate limit exceeded. Please wait a moment.", 429)

    try:
        body = await request.json()
    except ValueError:
        return _error_response("Invalid JSON body.", 400)
    user_message = str(body.get("message", "") if isinstance(body, dict) else "").strip()
    if not user_message:
        return _error_response("Message cannot be empty.", 400)
    if len(user_message) > 4000:
        return _error_response("Message is too long (max 4000 characters).", 400)

    logger.info("Chat turn received (%d chars)", len(user_message))
    return StreamingResponse(
        stream_turn(session, user_message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Session-Id": session.session_id},
    )
