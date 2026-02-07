"""
Lightweight session-based authentication.

In production, swap this for OAuth 2.0 / JWT verification against
an identity provider.  For development, sessions are created on
first contact and tracked via a Bearer token.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass, field

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Session:
    session_id: str
    token: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


class SessionAuthenticator:
    """In-memory session store with token-based auth."""

    def __init__(self, expiry_minutes: int = settings.session.token_expiry_minutes):
        self._sessions: dict[str, Session] = {}
        self._token_index: dict[str, str] = {}  # token -> session_id
        self._expiry_seconds = expiry_minutes * 60

    def create_session(self) -> Session:
        """Create a new session and return it."""
        session_id = hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:24]
        token = secrets.token_urlsafe(48)
        session = Session(session_id=session_id, token=token)
        self._sessions[session_id] = session
        self._token_index[token] = session_id
        logger.info(f"Session created: {session_id}")
        return session

    def validate_token(self, token: str) -> Session | None:
        """Validate a Bearer token and return the session if valid."""
        session_id = self._token_index.get(token)
        if not session_id:
            return None

        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check expiry
        if time.time() - session.created_at > self._expiry_seconds:
            logger.info(f"Session expired: {session_id}")
            self.revoke_session(session_id)
            return None

        session.last_active = time.time()
        return session

    def revoke_session(self, session_id: str) -> None:
        """Remove a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            self._token_index.pop(session.token, None)

    def cleanup_expired(self) -> None:
        """Purge all expired sessions."""
        now = time.time()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if now - s.created_at > self._expiry_seconds
        ]
        for sid in expired:
            self.revoke_session(sid)


# Module-level singleton
authenticator = SessionAuthenticator()
