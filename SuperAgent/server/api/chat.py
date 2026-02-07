"""
POST /api/chat – SSE streaming chat endpoint.

Flow:
1. Authenticate the user session via Bearer token.
2. Apply rate limits.
3. Inject the system message (baked into the ADK agent instruction).
4. Forward the request through the ADK Runner (sub-agents + tools active).
5. Stream response tokens back as Server-Sent Events.
"""

import json

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from google.genai import types

from config import settings
from middleware.auth import authenticator
from middleware.rate_limiter import rate_limiter
from utils.logger import get_logger, session_id_var

logger = get_logger(__name__)
router = APIRouter()

# These are set at startup by main.py — avoids circular imports.
_runner = None
_session_service = None
_app_name = None


def init_runner(runner, session_service, app_name: str):
    """Called once from main.py at startup to inject the ADK runner."""
    global _runner, _session_service, _app_name
    _runner = runner
    _session_service = session_service
    _app_name = app_name


async def _ensure_adk_session(user_id: str, session_id: str):
    """Get or create an ADK session for this user."""
    existing = await _session_service.get_session(
        app_name=_app_name, user_id=user_id, session_id=session_id,
    )
    if existing:
        return existing

    return await _session_service.create_session(
        app_name=_app_name, user_id=user_id, session_id=session_id,
    )


async def _stream_agent(user_id: str, session_id: str, user_message: str):
    """Run the ADK agent with SSE streaming and yield formatted events."""
    from google.adk.runners import RunConfig

    await _ensure_adk_session(user_id, session_id)

    new_message = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )

    run_config = RunConfig(streaming_mode="sse")

    async for event in _runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message,
        run_config=run_config,
    ):
        # Emit text content from the agent (or sub-agents)
        if event.content and event.content.parts:
            for part in event.content.parts:
                text = part.text if hasattr(part, "text") else None
                if text:
                    payload = json.dumps({
                        "type": "token",
                        "content": text,
                        "author": event.author,
                        "partial": bool(event.partial),
                    })
                    yield f"data: {payload}\n\n"

        # Check for errors
        if event.error_message:
            payload = json.dumps({"type": "error", "content": event.error_message})
            yield f"data: {payload}\n\n"

        # Turn complete = done
        if event.turn_complete:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

    # Safety: always signal done
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/api/chat")
async def chat(request: Request, authorization: str = Header(default="")):
    """
    SSE streaming chat endpoint.

    Request body:
        {
            "message": "user message text",
            "history": []  (history is managed by ADK sessions, not the client)
        }

    Headers:
        Authorization: Bearer <session_token>

    Response: text/event-stream with JSON payloads.
    """
    # --- 1. Authenticate ---
    token = authorization.removeprefix("Bearer ").strip()
    session = authenticator.validate_token(token)
    if not session:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'content': 'Invalid or expired session. Please refresh.'})}\n\n"]),
            media_type="text/event-stream",
            status_code=401,
        )

    session_id_var.set(session.session_id)
    logger.info("Chat request received")

    # --- 2. Rate limit ---
    if not rate_limiter.allow(session.session_id):
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'content': 'Rate limit exceeded. Please wait a moment.'})}\n\n"]),
            media_type="text/event-stream",
            status_code=429,
        )

    # --- 3. Parse request body ---
    body = await request.json()
    user_message = body.get("message", "").strip()

    if not user_message:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'content': 'Message cannot be empty.'})}\n\n"]),
            media_type="text/event-stream",
            status_code=400,
        )

    # --- 4 & 5. Run ADK agent and stream SSE ---
    # Use the auth session_id as both ADK user_id and session_id.
    # ADK sessions handle conversation history internally.
    logger.info(f"Streaming ADK agent response for: {user_message[:80]}...")

    return StreamingResponse(
        _stream_agent(
            user_id=session.session_id,
            session_id=session.session_id,
            user_message=user_message,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session.session_id,
        },
    )
