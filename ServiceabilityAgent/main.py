"""
ServiceabilityAgent FastAPI server entry point.

This follows the BootStrap Agent framework pattern with ADK Runner + InMemorySessionService.
Provides a standalone API for address validation and serviceability checking.

Can be run independently or integrated as a sub-agent in the Super Agent system.
"""

import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Ensure the serviceability_agent package is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from serviceability_agent import get_agent
from serviceability_agent.utils.logger import get_logger
from serviceability_agent.utils.cache import get_cache_stats, cleanup_cache
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.runners import RunConfig

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# ADK Runner setup (mirrors BootStrapAgent/main.py pattern)
# ---------------------------------------------------------------------------
APP_NAME = os.getenv("AGENT_NAME", "serviceability-agent")
session_service = InMemorySessionService()
runner = Runner(
    agent=get_agent(),
    app_name=APP_NAME,
    session_service=session_service,
)

logger.info(f"ADK Runner initialized for {APP_NAME}")

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Serviceability Agent API",
    description="PRE-SALE address validation & coverage verification agent",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------
class CheckRequest(BaseModel):
    """Request model for serviceability check"""
    user_id: str
    session_id: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "session_id": "session456",
                "message": "Check serviceability for 123 Market Street, Philadelphia, PA 19107"
            }
        }


class CheckResponse(BaseModel):
    """Response model for serviceability check"""
    response: str
    agent: str
    session_id: str


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "agent": APP_NAME,
        "model": os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
        "version": "1.0.0"
    }


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    stats = get_cache_stats()
    return {
        "cache": stats,
        "agent": APP_NAME
    }


@app.post("/cache/cleanup")
async def cache_cleanup():
    """Clean up expired cache entries"""
    cleanup_cache()
    return {
        "status": "ok",
        "message": "Expired cache entries removed"
    }


@app.post("/api/check", response_model=CheckResponse)
async def check_serviceability(request: CheckRequest):
    """
    Check serviceability for a given address message.
    
    This endpoint accepts a user message containing an address and returns
    the agent's response with serviceability information.
    
    Args:
        request: CheckRequest with user_id, session_id, and message
        
    Returns:
        CheckResponse with agent's response
        
    Example:
        POST /api/check
        {
            "user_id": "user123",
            "session_id": "session456",
            "message": "Check 123 Market St, Philadelphia, PA 19107"
        }
    """
    logger.info(f"Serviceability check request: user={request.user_id}, session={request.session_id}")
    
    try:
        # Create message
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=request.message)],
        )
        
        # Run agent with streaming disabled for HTTP response
        response_text = ""
        async for event in runner.run_async(
            user_id=request.user_id,
            session_id=request.session_id,
            new_message=new_message,
            run_config=RunConfig(),
        ):
            # Extract text from event
            if event.content and hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text += part.text
        
        logger.info(f"Serviceability check complete for session {request.session_id}")
        
        return CheckResponse(
            response=response_text,
            agent=APP_NAME,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"Error processing serviceability check: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str, user_id: str):
    """
    Delete a session to clear conversation history.
    
    Args:
        session_id: Session identifier
        user_id: User identifier
        
    Returns:
        Success message
    """
    try:
        await session_service.delete_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
        logger.info(f"Session deleted: {session_id}")
        return {"status": "ok", "message": f"Session {session_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Serviceability Agent API",
        "version": "1.0.0",
        "description": "PRE-SALE address validation & coverage verification",
        "endpoints": {
            "health": "GET /health",
            "check": "POST /api/check",
            "cache_stats": "GET /cache/stats",
            "cache_cleanup": "POST /cache/cleanup",
            "delete_session": "DELETE /api/session/{session_id}",
            "docs": "GET /docs"
        }
    }


# ---------------------------------------------------------------------------
# Startup/Shutdown Events
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    """Startup event handler"""
    logger.info(
        f"Serviceability Agent server starting — "
        f"agent={APP_NAME}, "
        f"model={os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview')}, "
        f"port={os.getenv('PORT', '8002')}"
    )


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event handler"""
    logger.info("Serviceability Agent server shutting down")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        reload=debug,
    )
