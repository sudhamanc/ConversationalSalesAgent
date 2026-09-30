"""create_a2a_app can be built more than once per process (shared a2a_tasks model)."""

import asyncio

import pytest
from google.adk import Agent


def _agent(name: str) -> Agent:
    return Agent(name=name, model="gemini-test", instruction="test")


@pytest.fixture
def a2a_env(monkeypatch):
    monkeypatch.setenv("PUBLIC_URL", "http://localhost:8299")
    monkeypatch.delenv("SESSION_DB_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u@127.0.0.1:1/unused")


def test_two_apps_in_one_process(a2a_env):
    from sales_common import a2a_server

    first = a2a_server.create_a2a_app(_agent("first_agent"))
    second = a2a_server.create_a2a_app(_agent("second_agent"))
    third = a2a_server._task_store(None)
    assert first is not second
    assert third.task_model is a2a_server._task_models["a2a_tasks"]
    assert third.task_model.__table__.name == "a2a_tasks"


@pytest.mark.pg
def test_two_task_stores_initialize(pg_url, monkeypatch):
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from starlette.testclient import TestClient

    from sales_common import a2a_server, db

    monkeypatch.setenv("PUBLIC_URL", "http://localhost:8299")
    monkeypatch.delenv("SESSION_DB_URL", raising=False)
    for name in ("one_agent", "two_agent"):
        with TestClient(a2a_server.create_a2a_app(_agent(name))) as client:
            assert client.get("/healthz").json() == {"status": "ok", "agent": name}

    async def init_twice():
        engines = [create_async_engine(db.session_db_url()) for _ in range(2)]
        try:
            for engine in engines:
                await a2a_server._task_store(engine).initialize()
            async with engines[0].connect() as conn:
                return (await conn.execute(text("SELECT to_regclass('a2a_tasks') IS NOT NULL"))).scalar()
        finally:
            for engine in engines:
                await engine.dispose()

    assert asyncio.run(init_twice()) is True
