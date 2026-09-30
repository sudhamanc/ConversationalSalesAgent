"""Stateless session tokens (any gateway instance can verify them).

Token = ``itsdangerous.URLSafeTimedSerializer(SESSION_SECRET_KEY)`` over
``{"sid": <session id>, "uid": <ADK user id>}`` with max age
``SESSION_TOKEN_EXPIRY_MIN``. Revocation is recorded in the ``revoked_sessions``
table (migration 003).
"""

from __future__ import annotations

import re
import secrets
import uuid
from dataclasses import dataclass
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from sales_common import db
from sales_common.config import require_env
from super_agent.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_SALT = "csa-session-v1"
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


@dataclass(frozen=True)
class Session:
    session_id: str
    user_id: str
    token: str = ""


def normalize_client_uid(raw: Optional[str]) -> str:
    """Map a browser-supplied anonymous id to an ADK user id (``web:<uuid4>``)."""
    try:
        return f"web:{uuid.UUID(str(raw), version=4)}"
    except (ValueError, TypeError, AttributeError):
        return f"web:{uuid.uuid4()}"


class SessionAuthenticator:
    def __init__(self, secret_key: Optional[str] = None, expiry_minutes: Optional[int] = None):
        self._serializer = URLSafeTimedSerializer(secret_key or require_env("SESSION_SECRET_KEY"), salt=_SALT)
        self._max_age = 60 * (expiry_minutes or settings.session.token_expiry_minutes)

    def create_session(self, client_uid: Optional[str] = None) -> Session:
        session_id = secrets.token_urlsafe(18)
        user_id = normalize_client_uid(client_uid)
        token = self._serializer.dumps({"sid": session_id, "uid": user_id})
        logger.info("Session created: %s", session_id)
        return Session(session_id=session_id, user_id=user_id, token=token)

    def validate_token(self, token: str) -> Optional[Session]:
        if not token:
            return None
        try:
            payload = self._serializer.loads(token, max_age=self._max_age)
        except SignatureExpired:
            logger.info("Expired session token")
            return None
        except BadSignature:
            logger.warning("Rejected tampered or invalid session token")
            return None
        sid, uid = payload.get("sid"), payload.get("uid")
        if not (isinstance(sid, str) and _SID_RE.match(sid) and isinstance(uid, str) and uid.startswith("web:")):
            return None
        if self.is_revoked(sid):
            return None
        return Session(session_id=sid, user_id=uid, token=token)

    @staticmethod
    def is_revoked(session_id: str) -> bool:
        return db.fetch_one("SELECT 1 AS r FROM revoked_sessions WHERE session_id = %s", (session_id,)) is not None

    @staticmethod
    def revoke_session(session_id: str) -> None:
        db.execute(
            "INSERT INTO revoked_sessions (session_id) VALUES (%s) ON CONFLICT DO NOTHING", (session_id,)
        )


_authenticator: Optional[SessionAuthenticator] = None


def get_authenticator() -> SessionAuthenticator:
    global _authenticator
    if _authenticator is None:
        _authenticator = SessionAuthenticator()
    return _authenticator
