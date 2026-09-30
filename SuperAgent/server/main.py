"""SuperAgent gateway: FastAPI + React UI + ADK 2.x ``sales_journey`` workflow.

Domain agents run as separate A2A services; this process hosts only the
router, the orchestration workflow, sessions (PostgreSQL), memory, and the SSE
chat API.
"""

import asyncio
import os
import pathlib
import sys
from contextlib import asynccontextmanager

_server_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _server_dir)
sys.path.insert(0, os.path.dirname(_server_dir))

import logging  # noqa: E402

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from super_agent.config import settings  # noqa: E402  (loads .env for local dev)
from sales_common import db, migrate  # noqa: E402
from sales_common.maintenance import cleanup_stale_records  # noqa: E402
from sales_common.config import model_name  # noqa: E402

import runtime  # noqa: E402
from api.chat import router as chat_router  # noqa: E402
from api.client_log import router as client_log_router  # noqa: E402
from api.debug import router as debug_router  # noqa: E402
from api.session import router as session_router  # noqa: E402
from middleware.auth import get_authenticator  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
for noisy in ("google.genai", "google.adk", "google_adk", "httpx"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = get_logger(__name__)


async def _hourly_cleanup() -> None:
    while True:
        await asyncio.sleep(3600)
        try:
            await asyncio.to_thread(cleanup_stale_records)
        except Exception as exc:
            logger.warning("Hourly cleanup failed (non-fatal): %s", type(exc).__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    model_name()  # fail fast when GEMINI_MODEL is missing
    get_authenticator()  # fail fast when SESSION_SECRET_KEY is missing
    if settings.server.run_migrations:
        await asyncio.to_thread(migrate.run, True)
    if runtime._runner is None:
        runtime.init_runtime()
    try:
        await asyncio.to_thread(cleanup_stale_records)
    except Exception as exc:
        logger.warning("Startup cleanup failed (non-fatal): %s", type(exc).__name__)
    task = asyncio.create_task(_hourly_cleanup())
    logger.info("Gateway started: app=%s model=%s", settings.agent.app_name, os.getenv("GEMINI_MODEL"))
    yield
    task.cancel()
    db.close_pool()
    logger.info("Gateway shutting down")


app = FastAPI(
    title="SuperAgent Gateway",
    description="B2B Sales gateway: SSE chat over an ADK 2.x workflow of A2A agents",
    version="2.0.0",
    debug=settings.server.debug,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(chat_router, tags=["Chat"])
app.include_router(debug_router, tags=["Debug"])
app.include_router(session_router, tags=["Session"])
app.include_router(client_log_router, tags=["ClientLog"])


@app.get("/health")
async def health():
    healthy = await asyncio.to_thread(db.ping)
    return JSONResponse(
        {"status": "ok" if healthy else "degraded", "agent": settings.agent.app_name, "model": os.getenv("GEMINI_MODEL")},
        status_code=200 if healthy else 503,
    )


@app.get("/healthz")
async def healthz():
    return await health()


_dist_path = pathlib.Path(__file__).parent.parent / "client" / "dist"
if _dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist_path / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(str(_dist_path / "index.html"))


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.server.host, port=settings.server.port, log_level=settings.server.log_level)
