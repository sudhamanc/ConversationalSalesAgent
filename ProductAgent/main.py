"""
ProductAgent FastAPI server entry point.

This follows the ServiceabilityAgent framework pattern with ADK Runner + InMemorySessionService.
Provides a standalone API for product information queries and comparisons.

Can be run independently or integrated as a sub-agent in the Super Agent system.
"""

import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

# Ensure the product_agent package is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from product_agent import get_agent
from product_agent.utils.logger import get_logger
from product_agent.utils.cache import get_cache_stats, cleanup_cache
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.runners import RunConfig

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# ADK Runner setup (mirrors ServiceabilityAgent/main.py pattern)
# ---------------------------------------------------------------------------
APP_NAME = os.getenv("AGENT_NAME", "product-agent")
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
    title="Product Agent API",
    description="Catalog-driven agent for product specifications and technical comparisons",
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
class QueryRequest(BaseModel):
    """Request model for product query"""
    user_id: str
    session_id: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "session_id": "session456",
                "message": "What are the speeds for Fiber 5G?"
            }
        }


class CompareRequest(BaseModel):
    """Request model for product comparison"""
    user_id: str
    session_id: str
    product_ids: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "session_id": "session456",
                "product_ids": ["FIB-1G", "FIB-5G", "FIB-10G"]
            }
        }


class QueryResponse(BaseModel):
    """Response model for queries"""
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
        "model": os.getenv("GEMINI_MODEL"),
        "catalog_mode": True,
    }


async def _ensure_adk_session(user_id: str, session_id: str):
    """Get or create an ADK session for this user."""
    existing = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id,
    )
    if existing:
        return existing

    return await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id,
    )


@app.post("/query", response_model=QueryResponse)
async def query_product(request: QueryRequest):
    """
    Query product information using natural language.
    
    The agent will determine which tools to use based on the query.
    """
    logger.info(f"Product query from user {request.user_id}: {request.message}")
    
    try:
        # Ensure session exists
        await _ensure_adk_session(request.user_id, request.session_id)
        
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
            if event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text'):
                        response_text += part.text
        
        logger.info(f"Query processed successfully for session {request.session_id}")
        
        return QueryResponse(
            response=response_text,
            agent=APP_NAME,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.post("/compare", response_model=QueryResponse)
async def compare_products(request: CompareRequest):
    """
    Compare multiple products side-by-side.
    """
    logger.info(f"Product comparison request: {request.product_ids}")
    
    try:
        # Ensure session exists
        await _ensure_adk_session(request.user_id, request.session_id)
        
        # Create comparison message
        product_list = ", ".join(request.product_ids)
        message_text = f"Compare these products: {product_list}"
        
        # Create message
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=message_text)],
        )
        
        # Run agent
        response_text = ""
        async for event in runner.run_async(
            user_id=request.user_id,
            session_id=request.session_id,
            new_message=new_message,
            run_config=RunConfig(),
        ):
            if event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text'):
                        response_text += part.text
        
        logger.info(f"Comparison processed for session {request.session_id}")
        
        return QueryResponse(
            response=response_text,
            agent=APP_NAME,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"Error processing comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@app.get("/products")
async def list_products(category: Optional[str] = None):
    """
    List all available products or filter by category.
    """
    logger.info(f"Listing products (category={category})")
    
    try:
        from product_agent.tools.product_tools import list_available_products
        result = list_available_products(category=category)
        return result
        
    except Exception as e:
        logger.error(f"Error listing products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products/{product_id}")
async def get_product(product_id: str):
    """
    Get detailed information about a specific product.
    """
    logger.info(f"Getting product: {product_id}")
    
    try:
        from product_agent.tools.product_tools import get_product_by_id
        result = get_product_by_id(product_id)
        
        if not result.get('found'):
            raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """
    Get agent statistics including cache stats.
    """
    logger.info("Getting agent statistics")
    
    try:
        return {
            "agent": APP_NAME,
            "cache": get_cache_stats(),
            "catalog_mode": True,
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/clear")
async def clear_cache():
    """
    Clear the query cache.
    """
    logger.info("Clearing cache")
    
    try:
        from product_agent.utils.cache import clear_cache as do_clear_cache
        do_clear_cache()
        return {"message": "Cache cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/cleanup")
async def cleanup_expired_cache():
    """
    Cleanup expired cache entries.
    """
    logger.info("Cleaning up expired cache entries")
    
    try:
        removed = cleanup_cache()
        return {
            "message": "Cache cleanup completed",
            "removed_entries": removed
        }
        
    except Exception as e:
        logger.error(f"Error during cache cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Startup and Shutdown Events
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    logger.info("=" * 60)
    logger.info("🚀 Product Agent Starting Up")
    logger.info("=" * 60)
    
    logger.info("✅ Catalog mode active")
    
    logger.info(f"✅ Agent: {APP_NAME}")
    logger.info(f"✅ Model: {os.getenv('GEMINI_MODEL')}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Product Agent shutting down")
    cleanup_cache()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8003"))
    
    logger.info(f"Starting Product Agent server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
