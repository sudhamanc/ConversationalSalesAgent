"""Expose an ADK agent as an A2A service with durable sessions and tasks.

Every agent service's ``server.py`` is::

    from sales_common.a2a_server import create_a2a_app
    from .agent import root_agent
    app = create_a2a_app(root_agent, app_name="order_agent")

Run with ``uvicorn order_agent.server:app --host 0.0.0.0 --port $PORT``.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Callable, Optional, Sequence
from urllib.parse import urlsplit

from google.adk import Runner
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.sessions import DatabaseSessionService
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import db
from .adk_app import build_app
from .config import require_env
from .logging import mask_url, setup_logging

logger = logging.getLogger("sales_common.a2a_server")


def _public_endpoint() -> tuple[str, int, str]:
    """Parse ``PUBLIC_URL`` into (host, port, protocol) for the agent card."""
    url = require_env("PUBLIC_URL")
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError(f"PUBLIC_URL must be an absolute http(s) URL, got {url!r}")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return parts.hostname, port, parts.scheme


_TASK_TABLE = "a2a_tasks"
# a2a-sdk maps the task table on its global declarative ``Base.metadata``; mapping
# the same table name twice raises ``InvalidRequestError``. Keep one ORM model per
# table name per process and share it between task stores (each app still gets
# its own engine and store).
_task_models: dict[str, type] = {}


def _task_store(engine, table_name: str = _TASK_TABLE):
    """``DatabaseTaskStore`` on ``engine`` that is safe to build repeatedly."""
    from a2a.server.tasks import DatabaseTaskStore

    model = _task_models.get(table_name)
    if model is None:
        store = DatabaseTaskStore(engine=engine, table_name=table_name)
        _task_models[table_name] = store.task_model
        return store
    # The default table name reuses the SDK's pre-mapped TaskModel (no new
    # mapping); then point the store at the cached model for ``table_name``.
    store = DatabaseTaskStore(engine=engine)
    store.task_model = model
    return store


def create_a2a_app(
    agent,
    *,
    app_name: Optional[str] = None,
    plugins: Optional[Sequence[BasePlugin]] = None,
    uses_database: bool = True,
    extra_lifespan: Optional[Callable] = None,
):
    """Build the Starlette A2A app for ``agent``.

    * ADK ``App`` with compaction + context caching (``sales_common.adk_app``)
    * ``DatabaseSessionService`` on PostgreSQL (sessions keyed by A2A context id)
    * a2a-sdk ``DatabaseTaskStore`` on the same database (table ``a2a_tasks``)
    * ``GET /healthz`` (503 when the database is unreachable)

    Safe to call more than once per process (tests, several apps in one
    process): the task-table ORM model is shared, engines are per app.
    """
    name = app_name or agent.name
    setup_logging(name)
    host, port, protocol = _public_endpoint()

    from sqlalchemy.ext.asyncio import create_async_engine

    session_url = db.session_db_url()
    logger.info("A2A service %s sessions/tasks at %s", name, mask_url(session_url))
    session_service = DatabaseSessionService(db_url=session_url)
    task_engine = create_async_engine(session_url, pool_pre_ping=True)
    task_store = _task_store(task_engine)

    adk_app = build_app(name, agent, plugins=plugins)
    runner = Runner(app=adk_app, session_service=session_service, auto_create_session=True)

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        if extra_lifespan is not None:
            async with extra_lifespan(_app):
                yield
        else:
            yield
        await task_engine.dispose()
        db.close_pool()

    app = to_a2a(
        agent,
        host=host,
        port=port,
        protocol=protocol,
        runner=runner,
        task_store=task_store,
        lifespan=lifespan,
    )

    async def healthz(_request: Request) -> JSONResponse:
        healthy = db.ping() if uses_database else True
        return JSONResponse(
            {"status": "ok" if healthy else "degraded", "agent": agent.name},
            status_code=200 if healthy else 503,
        )

    app.router.routes.append(Route("/healthz", healthz, methods=["GET"]))
    return app
