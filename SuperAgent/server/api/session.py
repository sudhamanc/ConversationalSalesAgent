"""Session endpoints.

POST   /api/session          – create a session; body ``{"client_id": "<uuid4>"}`` (optional)
DELETE /api/session          – revoke the current session
GET    /api/session/health   – liveness
"""

from fastapi import APIRouter, Header, Request

from middleware.auth import get_authenticator
from runtime import ensure_adk_session
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/api/session")
async def create_session(request: Request):
    client_id = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            client_id = body.get("client_id")
    except ValueError:
        pass
    session = get_authenticator().create_session(client_id)
    await ensure_adk_session(session.user_id, session.session_id)
    return {"session_id": session.session_id, "token": session.token}


@router.delete("/api/session")
async def revoke_session(authorization: str = Header(default="")):
    auth = get_authenticator()
    session = auth.validate_token(authorization.removeprefix("Bearer ").strip())
    if session:
        auth.revoke_session(session.session_id)
        return {"status": "revoked"}
    return {"status": "not_found"}


@router.get("/api/session/health")
async def session_health():
    return {"status": "ok"}
