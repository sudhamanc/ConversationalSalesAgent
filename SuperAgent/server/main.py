"""
SuperAgent FastAPI server entry point.

Initializes the ADK Runner + InMemorySessionService following the
bootstrap agent framework pattern, then registers custom API routes
for SSE streaming chat.

The ADK agent (with sub-agents and tools) is the single LLM entry
point — all chat requests flow through it.
"""

import os
import sys
# Monkey-patch to fix google-adk 1.25.1 bug: passes unknown kwargs to Logger._log()
import logging as _logging
_orig_log = _logging.Logger._log
_known_log_kwargs = {"exc_info", "stack_info", "stacklevel", "extra"}
def _patched_log(self, level, msg, args, **kwargs):
    for key in list(kwargs):
        if key not in _known_log_kwargs:
            kwargs.pop(key)
    _orig_log(self, level, msg, args, **kwargs)
_logging.Logger._log = _patched_log
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the server package and project root are on sys.path for imports
_server_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.dirname(_server_dir)
sys.path.insert(0, _server_dir)
sys.path.insert(0, _project_dir)

from super_agent.config import settings
from super_agent import get_agent
from api.chat import router as chat_router, init_runner
from api.session import router as session_router
from utils.logger import get_logger

# Keep application-level logging at INFO; suppress verbose ADK/GenAI debug output
logging.basicConfig(level=logging.INFO)
genai_logger = logging.getLogger("google.genai")
genai_logger.setLevel(logging.WARNING)
adk_logger = logging.getLogger("google.adk")
adk_logger.setLevel(logging.WARNING)
logging.getLogger("google_adk").setLevel(logging.WARNING)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# ADK Runner setup (mirrors BootStrapAgent/main.py's get_fast_api_app usage
# but gives us control over the HTTP layer for custom SSE streaming).
# ---------------------------------------------------------------------------
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

APP_NAME = settings.agent.agent_name
session_service = InMemorySessionService()
runner = Runner(
    agent=get_agent(),
    app_name=APP_NAME,
    session_service=session_service,
)

# Inject the runner into the chat module so it can invoke the agent.
init_runner(runner, session_service, APP_NAME)

# ---------------------------------------------------------------------------
# FastAPI application with lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(
        f"SuperAgent server starting — "
        f"agent={APP_NAME}, model={settings.model.model_name}, "
        f"port={settings.server.port}, "
        f"sub_agents_enabled={settings.agent.enable_sub_agents}"
    )
    yield
    # Shutdown
    logger.info("SuperAgent server shutting down")

app = FastAPI(
    title="SuperAgent API",
    description="B2B Sales Super Agent with SSE streaming chat (ADK-backed)",
    version="1.0.0",
    debug=settings.server.debug,
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(chat_router, tags=["Chat"])
app.include_router(session_router, tags=["Session"])


@app.get("/health")
async def health():
    return {"status": "ok", "agent": settings.agent.agent_name, "model": settings.model.model_name}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        log_level=settings.server.log_level,
        reload=settings.server.debug,
    )
