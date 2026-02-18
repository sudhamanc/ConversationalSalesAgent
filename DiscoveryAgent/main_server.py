
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
            "agents": "GET /agents - List available agents",
            "docs": "GET /docs - Interactive API documentation"
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
    Chat with the Prospect Intelligence system using Gemini.
    Ask questions about companies, leads, BANT scores, buying signals, etc.
    """
    try:
        user_message = message.message
        
        if not user_message or not user_message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Use the prospect chat agent with Gemini API
        from prospect_chat import send_chat_message
        response_text = send_chat_message(user_message)
        
        return ChatResponse(
            response=response_text,
            agent="prospect_chat",
            status="success"
        )
        
    except ValueError as e:
        # Handle missing API key configuration
        raise HTTPException(
            status_code=401,
            detail=f"Configuration error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n{'='*60}")
    print(f"Discovery Agent API Server")
    print(f"{'='*60}")
    print(f"Server URL: http://localhost:{port}")
    print(f"Health Check: http://localhost:{port}/health")
    print(f"API Docs: http://localhost:{port}/docs")
    print(f"Agents Endpoint: http://localhost:{port}/agents")
    print(f"{'='*60}")
    print(f"\nAvailable Agents:")
    for agent in root_agent.sub_agents:
        print(f"  - {agent.name}: {agent.description}")
    print(f"{'='*60}\n")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
