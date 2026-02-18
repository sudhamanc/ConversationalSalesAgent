
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the root agent
from bootstrap_agent.agent import root_agent

# Create FastAPI app
app = FastAPI(title="Discovery Agent API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    agent: str
    status: str

@app.get("/")
async def root():
    return {
        "message": "Discovery Agent API is running",
        "status": "operational",
        "version": "1.0.0",
        "agents": {
            "discovery_agent": "Customer discovery, intent, company details, contact personas",
            "lead_gen_agent": "Lead qualification, BANT scoring, sales readiness",
            "test_agent": "Simple test agent"
        },
        "endpoints": {
            "health": "GET /health - Health check",
            "chat": "POST /chat - Send message to agent",
            "agents": "GET /agents - List available agents"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Discovery Agent API is running",
        "agents_loaded": True,
        "agent_count": len(root_agent.sub_agents)
    }

@app.get("/agents")
async def list_agents():
    """List all available sub-agents and their capabilities"""
    return {
        "root_agent": {
            "name": root_agent.name,
            "sub_agents": [
                {
                    "name": agent.name,
                    "description": agent.description,
                    "tool_count": len(agent.tools) if hasattr(agent, 'tools') else 0
                }
                for agent in root_agent.sub_agents
            ]
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Chat with the Discovery Agent system.
    The root agent will automatically route to the appropriate sub-agent.
    """
    try:
        user_message = message.message
        
        if not user_message or not user_message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Use the root agent to process the message
        response = root_agent.send_message(user_message)
        
        # Extract response text
        response_text = str(response)
        
        return ChatResponse(
            response=response_text,
            agent=root_agent.name,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )

@app.get("/")
async def root():
    return {
        "message": "Bootstrap Agent API is running",
        "status": "Server operational - ADK agents integrated!",
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