"""Developer-only session inspection (enabled only when DEBUG=true).

GET /api/debug/session – returns the ADK session state for the caller's own
session (Bearer token required).
"""

from fastapi import APIRouter, Header, HTTPException

from middleware.auth import get_authenticator
from runtime import app_name, get_runner
from super_agent.config import settings

router = APIRouter()


@router.get("/api/debug/session")
async def debug_session(authorization: str = Header(default="")):
    if not settings.server.debug:
        raise HTTPException(status_code=403, detail="Debug endpoints disabled")
    session = get_authenticator().validate_token(authorization.removeprefix("Bearer ").strip())
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    adk_session = await get_runner().session_service.get_session(
        app_name=app_name(), user_id=session.user_id, session_id=session.session_id
    )
    if not adk_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session.session_id, "user_id": session.user_id, "state": adk_session.state}
