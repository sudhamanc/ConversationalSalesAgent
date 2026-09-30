import pytest

from middleware import auth as auth_mod
from middleware.auth import SessionAuthenticator, normalize_client_uid


@pytest.fixture(autouse=True)
def no_db_revocation(monkeypatch):
    monkeypatch.setattr(SessionAuthenticator, "is_revoked", staticmethod(lambda sid: sid == "revoked-session-id-123"))


def test_token_verifiable_by_another_instance():
    a = SessionAuthenticator(secret_key="k1", expiry_minutes=60)
    b = SessionAuthenticator(secret_key="k1", expiry_minutes=60)
    s = a.create_session("0b7c9a4e-8f1d-4c2a-9d3e-2f6a7b8c9d0e")
    got = b.validate_token(s.token)
    assert got.session_id == s.session_id and got.user_id == "web:0b7c9a4e-8f1d-4c2a-9d3e-2f6a7b8c9d0e"


def test_tampered_and_foreign_tokens_rejected():
    a = SessionAuthenticator(secret_key="k1")
    s = a.create_session()
    assert a.validate_token(s.token[:-2] + "xx") is None
    assert SessionAuthenticator(secret_key="other").validate_token(s.token) is None
    assert a.validate_token("") is None


def test_expired_token_rejected(monkeypatch):
    a = SessionAuthenticator(secret_key="k1", expiry_minutes=1)
    s = a.create_session()
    a._max_age = -1
    assert a.validate_token(s.token) is None


def test_revoked_rejected():
    a = SessionAuthenticator(secret_key="k1")
    token = a._serializer.dumps({"sid": "revoked-session-id-123", "uid": "web:x"})
    assert a.validate_token(token) is None


def test_client_uid_normalization():
    assert normalize_client_uid("not-a-uuid").startswith("web:")
    assert normalize_client_uid("'; DROP TABLE x;--").startswith("web:")
    assert len(normalize_client_uid(None)) == len("web:") + 36
