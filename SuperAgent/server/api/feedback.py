"""POST /api/feedback – thumbs up/down on an assistant reply, recorded as a Langfuse score.

When tracing is on, each turn's SSE ``done`` event carries the turn's
``trace_id`` and a ``feedback_token``: an itsdangerous signature (keyed by
``SESSION_SECRET_KEY``) over ``[session_id, trace_id, turn timestamp]``. The
token proves the trace belongs to the caller's session without server-side
state, so any gateway instance can verify it.

The vote becomes the boolean score ``user_feedback`` (1 = up, 0 = down) on the
trace. Its id is derived from the trace id and its timestamp is the turn's, so
a changed vote updates the same score (Langfuse updates a score sent again with
the same id and timestamp).

Responses: 204 recorded · 400 malformed body · 401 bad session · 403 token not
issued for this session/trace · 404 tracing disabled · 429 rate limited ·
502 Langfuse rejected the score.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, URLSafeSerializer

from middleware.auth import get_authenticator
from middleware.rate_limiter import RateLimiter
from sales_common import telemetry
from sales_common.config import require_env
from sales_common.langfuse_api import LangfuseApiError, LangfuseClient
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

SCORE_NAME = "user_feedback"
_SALT = "csa-feedback"
_TRACE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_VALUES = {"up": 1, "down": 0}

# Same RATE_LIMIT_* settings as /api/client-log, separate per-session buckets.
feedback_limiter = RateLimiter()


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(require_env("SESSION_SECRET_KEY"), salt=_SALT)


def issue_feedback_token(session_id: str, trace_id: str, issued_at: Optional[datetime] = None) -> str:
    """Token binding ``trace_id`` to ``session_id`` (and the turn time used as the score timestamp)."""
    when = (issued_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    return _serializer().dumps([session_id, trace_id, when])


def verify_feedback_token(token: str, session_id: str, trace_id: str) -> Optional[datetime]:
    """Turn timestamp when ``token`` was issued for this session and trace, else ``None``."""
    try:
        sid, tid, when = _serializer().loads(token)
        if sid != session_id or tid != trace_id:
            return None
        return datetime.fromisoformat(when)
    except (BadSignature, ValueError, TypeError):
        return None


def score_id(trace_id: str) -> str:
    return hashlib.sha256(f"{SCORE_NAME}:{trace_id}".encode()).hexdigest()[:32]


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status)


@router.post("/api/feedback")
async def feedback(request: Request, authorization: str = Header(default="")):
    session = get_authenticator().validate_token(authorization.removeprefix("Bearer ").strip())
    if not session:
        return _error("invalid session", 401)
    client = LangfuseClient.from_env()
    if not telemetry.enabled() or client is None:
        return _error("feedback is not enabled", 404)
    if not feedback_limiter.allow(session.session_id):
        return _error("rate limited", 429)

    try:
        body = await request.json()
    except ValueError:
        return _error("invalid json", 400)
    if not isinstance(body, dict):
        return _error("invalid body", 400)
    trace_id = str(body.get("trace_id") or "")
    token = body.get("feedback_token")
    value = body.get("value")
    if not _TRACE_ID_RE.match(trace_id) or not isinstance(token, str) or value not in _VALUES:
        return _error("expected trace_id (32 hex), feedback_token and value 'up' or 'down'", 400)

    turn_time = verify_feedback_token(token, session.session_id, trace_id)
    if turn_time is None:
        return _error("feedback token does not match this session", 403)

    settings = telemetry.settings()
    try:
        await client.create_score(
            name=SCORE_NAME,
            value=_VALUES[value],
            trace_id=trace_id,
            score_id=score_id(trace_id),
            data_type="BOOLEAN",
            environment=settings.environment if settings else None,
            timestamp=turn_time,
        )
    except (LangfuseApiError, httpx.HTTPError) as exc:
        logger.warning("Feedback score not recorded: %s", exc)
        return _error("feedback not recorded", 502)
    logger.info("Feedback %s recorded for trace %s", value, trace_id)
    return Response(status_code=204)
