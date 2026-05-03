"""
Debug endpoints for developer-only inspection.

Only enabled when `settings.server.debug` is True to avoid accidental exposure.
"""
from fastapi import APIRouter, HTTPException

from utils.logger import get_logger
from super_agent.config import settings

import api.chat as chat_api

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/debug/session/{session_id}")
async def debug_session(session_id: str):
    """Return the ADK session state for the given session_id.

    This endpoint is intentionally minimal. It is only available when the
    server is running in debug mode (`settings.server.debug == True`).
    """
    if not settings.server.debug:
        raise HTTPException(status_code=403, detail="Debug endpoints disabled")

    svc = getattr(chat_api, "_session_service", None)
    app_name = getattr(chat_api, "_app_name", None)
    greeting_runner = getattr(chat_api, "_greeting_runner", None)
    if svc is None or app_name is None:
        raise HTTPException(status_code=500, detail="Session service not initialized")

    # Try main runner session first
    session = await svc.get_session(app_name=app_name, user_id=session_id, session_id=session_id)
    if session:
        state = getattr(session, "state", None)
        return {"session_id": session_id, "runner": "main", "state": state}

    # Greeting runner uses its own in-memory service and uses a prefixed session id
    if greeting_runner is not None:
        try_ids = [session_id, f"greet_{session_id}"]
        for sid in try_ids:
            gs = greeting_runner.session_service
            s = await gs.get_session(app_name=greeting_runner.app_name, user_id=sid, session_id=sid)
            if s:
                state = getattr(s, "state", None)
                return {"session_id": sid, "runner": "greeting", "state": state}

    raise HTTPException(status_code=404, detail="Session not found in main or greeting runner")
