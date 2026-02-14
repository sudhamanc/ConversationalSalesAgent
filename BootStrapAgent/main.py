
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create simple FastAPI app
app = FastAPI(title="Bootstrap Agent API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Bootstrap Agent API is running"}

@app.post("/chat")
async def chat(message: dict):
    """Simple chat endpoint - agent integration pending ADK fixes"""
    user_message = message.get("message", "")
    return {
        "response": f"Received: {user_message}. Note: Google ADK 1.20.0 has compatibility issues with Python 3.12. Agent integration pending.",
        "status": "awaiting_adk_fix"
    }

@app.get("/")
async def root():
    return {
        "message": "Bootstrap Agent API is running",
        "status": "Server operational, but Google ADK 1.20.0 has import issues",
        "endpoints": {
            "health": "/health",
            "chat": "/chat (POST with {\"message\": \"your text\"})",
        },
        "issue": "Google ADK 1.20.0 hangs on import with Python 3.12 - pydantic/genai compatibility problem"
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n{'='*60}")
    print(f"Bootstrap Agent API Server")
    print(f"{'='*60}")
    print(f"Server URL: http://localhost:{port}")
    print(f"Health Check: http://localhost:{port}/health")
    print(f"API Docs: http://localhost:{port}/docs")
    print(f"{'='*60}\n")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )