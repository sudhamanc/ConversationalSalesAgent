"""
Browser console log forwarding.

POST /api/client-log appends a single log line to SuperAgent/logs/frontend.log
so browser-side console.log/warn/error/info show up in the same file as Vite's
own server output. Used by the lightweight remote-logging shim in
client/src/utils/remoteLog.js.
"""

import pathlib
from datetime import datetime

from fastapi import APIRouter, Request

router = APIRouter()

_LOG_PATH = pathlib.Path(__file__).resolve().parent.parent.parent / "logs" / "frontend.log"
_MAX_MSG_CHARS = 4000


@router.post("/api/client-log")
async def client_log(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid json"}

    level = str(data.get("level", "log")).upper()[:8]
    message = str(data.get("message", ""))[:_MAX_MSG_CHARS]
    ts = data.get("timestamp") or datetime.utcnow().isoformat()

    line = f"[BROWSER {level}] [{ts}] {message}\n"

    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

    return {"ok": True}
