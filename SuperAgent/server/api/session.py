"""
Session management endpoints.

POST /api/session       – Create a new session (returns token).
DELETE /api/session      – Revoke current session.
GET  /api/session/health – Health check.
"""

from fastapi import APIRouter, Header

from middleware.auth import authenticator
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/api/session")
async def create_session():
    """Create a new authenticated session."""
    session = authenticator.create_session()
    return {
        "session_id": session.session_id,
        "token": session.token,
    }


@router.delete("/api/session")
async def revoke_session(authorization: str = Header(default="")):
    """Revoke the current session."""
    token = authorization.removeprefix("Bearer ").strip()
    session = authenticator.validate_token(token)
    if session:
        authenticator.revoke_session(session.session_id)
        return {"status": "revoked"}
    return {"status": "not_found"}


@router.get("/api/session/health")
async def session_health():
    """Quick health probe."""
    return {"status": "ok"}
