"""
Browser console log forwarding (development aid).

POST /api/client-log appends a single log line to ``<repo>/logs/frontend.log``
(``LOG_DIR`` overrides the directory, matching ``scripts/lib.sh``) so
browser-side console.log/warn/error/info show up next to the other service
logs. Used by the remote-logging shim in ``client/src/utils/remoteLog.js``.

Hardening:
- requires a valid Bearer session token (401 otherwise);
- per-session token-bucket rate limit (429), separate from the chat limiter so
  console noise never consumes chat quota;
- control characters (including CR/LF) are replaced with spaces so a message
  cannot forge extra log lines; messages are capped at 4000 characters.
"""

from __future__ import annotations

import os
import pathlib
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from middleware.auth import get_authenticator
from middleware.rate_limiter import RateLimiter

router = APIRouter()

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_MAX_MSG_CHARS = 4000
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f  ]")
_LEVELS = {"LOG", "INFO", "WARN", "ERROR", "DEBUG"}

client_log_limiter = RateLimiter()


def log_path() -> pathlib.Path:
    """``$LOG_DIR/frontend.log``, defaulting to ``<repo>/logs/frontend.log``."""
    return pathlib.Path(os.getenv("LOG_DIR") or (_REPO_ROOT / "logs")) / "frontend.log"


def sanitize(value: object, limit: int) -> str:
    """Strip control characters (log injection) and cap the length."""
    return _CONTROL_CHARS.sub(" ", str(value)[:limit])


@router.post("/api/client-log")
async def client_log(request: Request, authorization: str = Header(default="")):
    session = get_authenticator().validate_token(authorization.removeprefix("Bearer ").strip())
    if not session:
        return JSONResponse({"ok": False, "error": "invalid session"}, status_code=401)
    if not client_log_limiter.allow(session.session_id):
        return JSONResponse({"ok": False, "error": "rate limited"}, status_code=429)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({"ok": False, "error": "invalid body"}, status_code=400)

    level = sanitize(data.get("level", "log"), 8).upper()
    if level not in _LEVELS:
        level = "LOG"
    message = sanitize(data.get("message", ""), _MAX_MSG_CHARS)
    ts = sanitize(data.get("timestamp") or datetime.now(timezone.utc).isoformat(), 40)

    line = f"[BROWSER {level}] [{ts}] [{session.session_id}] {message}\n"
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
    return {"ok": True}
