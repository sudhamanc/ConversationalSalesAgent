"""
SuperAgent FastAPI server entry point.

Registers:
  - CORS middleware
  - /api/chat   (SSE streaming chat)
  - /api/session (session management)
  - /health     (health check)
  - ADK agent   (optional, for ADK web UI)
"""

import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the server package is on sys.path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from api.chat import router as chat_router
from api.session import router as session_router
from utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="SuperAgent API",
    description="B2B Sales Super Agent with SSE streaming chat",
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
    return {"status": "ok", "agent": settings.agent.agent_name}


@app.on_event("startup")
async def startup():
    logger.info(
        f"SuperAgent server starting — model={settings.model.model_name}, "
        f"port={settings.server.port}"
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        log_level=settings.server.log_level,
        reload=settings.server.debug,
    )
