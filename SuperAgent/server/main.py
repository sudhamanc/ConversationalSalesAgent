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
import uvicorn
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
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SuperAgent API",
    description="B2B Sales Super Agent with SSE streaming chat (ADK-backed)",
    version="1.0.0",
    debug=settings.server.debug,
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


@app.on_event("startup")
async def startup():
    logger.info(
        f"SuperAgent server starting — "
        f"agent={APP_NAME}, model={settings.model.model_name}, "
        f"port={settings.server.port}, "
        f"sub_agents_enabled={settings.agent.enable_sub_agents}"
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        log_level=settings.server.log_level,
        reload=settings.server.debug,
    )
