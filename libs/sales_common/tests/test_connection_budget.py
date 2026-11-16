"""Connection budget (spec: sales-data-store "Database connection budget")."""

import asyncio

import pytest
from google.adk import Agent
from sqlalchemy.pool import NullPool, QueuePool

from sales_common import a2a_server, db

URL = "postgresql+asyncpg://u@127.0.0.1:1/unused"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("DB_ASYNC_POOL_SIZE", "DB_ASYNC_MAX_OVERFLOW", "DB_POOL_MIN", "DB_POOL_MAX", "DB_POOL_MAX_IDLE_S"):
        monkeypatch.delenv(name, raising=False)


def _dispose(engine):
    asyncio.run(engine.dispose())


def test_default_engine_holds_no_idle_connections():
    engine = db.create_session_engine(URL)
    try:
        assert isinstance(engine.pool, NullPool)
    finally:
        _dispose(engine)


def test_pooling_opt_in(monkeypatch):
    monkeypatch.setenv("DB_ASYNC_POOL_SIZE", "3")
    monkeypatch.setenv("DB_ASYNC_MAX_OVERFLOW", "1")
    engine = db.create_session_engine(URL)
    try:
        assert isinstance(engine.pool, QueuePool)
        assert engine.pool.size() == 3
        assert engine.pool._max_overflow == 1
    finally:
        _dispose(engine)


def test_tool_pool_defaults(monkeypatch):
    captured = {}

    class FakePool:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def close(self):
            pass

    monkeypatch.setenv("DATABASE_URL", "postgresql://u@127.0.0.1:1/unused")
    monkeypatch.setattr(db, "ConnectionPool", FakePool)
    db.close_pool()
    try:
        db.get_pool()
    finally:
        db.close_pool()
    assert (captured["min_size"], captured["max_size"], captured["max_idle"]) == (0, 2, 60.0)


def test_agent_service_shares_one_engine(monkeypatch):
    monkeypatch.setenv("PUBLIC_URL", "http://localhost:8299")
    monkeypatch.delenv("SESSION_DB_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u@127.0.0.1:1/unused")
    seen = {}
    real_service, real_store = a2a_server.DatabaseSessionService, a2a_server._task_store

    def session_service(**kwargs):
        seen["session"] = kwargs
        return real_service(**kwargs)

    def task_store(engine):
        seen["task"] = engine
        return real_store(engine)

    monkeypatch.setattr(a2a_server, "DatabaseSessionService", session_service)
    monkeypatch.setattr(a2a_server, "_task_store", task_store)
    a2a_server.create_a2a_app(Agent(name="budget_agent", model="gemini-test", instruction="t"))
    assert set(seen["session"]) == {"db_engine"}
    assert seen["session"]["db_engine"] is seen["task"]
    assert isinstance(seen["task"].pool, NullPool)
