"""Gateway runtime singletons: session service, memory service, runner."""

from __future__ import annotations

from typing import Optional

from google.adk import Runner
from google.adk.sessions import DatabaseSessionService

from sales_common.db import session_db_url
from sales_common.memory import PostgresMemoryService
from super_agent import build_gateway_app
from super_agent.config import settings

_runner: Optional[Runner] = None


def init_runtime(app=None, session_service=None, memory_service=None) -> Runner:
    """Create the Runner (tests may inject an app and services)."""
    global _runner
    url = session_db_url()
    _runner = Runner(
        app=app or build_gateway_app(),
        session_service=session_service or DatabaseSessionService(db_url=url),
        memory_service=memory_service or PostgresMemoryService(url),
    )
    return _runner


def get_runner() -> Runner:
    if _runner is None:
        raise RuntimeError("Runtime not initialised")
    return _runner


def app_name() -> str:
    return settings.agent.app_name


async def ensure_adk_session(user_id: str, session_id: str):
    runner = get_runner()
    svc = runner.session_service
    existing = await svc.get_session(app_name=app_name(), user_id=user_id, session_id=session_id)
    if existing:
        return existing
    return await svc.create_session(app_name=app_name(), user_id=user_id, session_id=session_id)
