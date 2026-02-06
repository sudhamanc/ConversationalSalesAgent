"""
POST /api/chat – SSE streaming chat endpoint.

Flow:
1. Authenticate the user session via Bearer token.
2. Apply rate limits.
3. Inject the system message into the conversation.
4. Forward the request to the Gemini LLM via Google GenAI SDK (server-side).
5. Stream response tokens back as Server-Sent Events.
"""

import json
import uuid

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from google import genai

from config import settings
from middleware.auth import authenticator
from middleware.rate_limiter import rate_limiter
from utils.logger import get_logger, session_id_var

logger = get_logger(__name__)
router = APIRouter()


def _build_contents(
    history: list[dict], user_message: str
) -> list[dict]:
    """Build the Gemini-compatible contents array with system context."""
    contents: list[dict] = []

    # Replay conversation history
    for msg in history:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    # Append the new user message
    contents.append({"role": "user", "parts": [{"text": user_message}]})
    return contents


async def _stream_gemini(contents: list[dict]):
    """Call the Gemini API with streaming and yield SSE-formatted chunks."""
    client = genai.Client()

    response = client.models.generate_content_stream(
        model=settings.model.model_name,
        contents=contents,
        config=genai.types.GenerateContentConfig(
            system_instruction=settings.agent.system_message,
            temperature=settings.model.temperature,
            top_p=settings.model.top_p,
            top_k=settings.model.top_k,
            max_output_tokens=settings.model.max_output_tokens,
        ),
    )

    for chunk in response:
        if chunk.text:
            payload = json.dumps({"type": "token", "content": chunk.text})
            yield f"data: {payload}\n\n"

    # Signal completion
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/api/chat")
async def chat(request: Request, authorization: str = Header(default="")):
    """
    SSE streaming chat endpoint.

    Request body:
        {
            "message": "user message text",
            "history": [{"role": "user"|"assistant", "content": "..."}]
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
    history = body.get("history", [])

    if not user_message:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'content': 'Message cannot be empty.'})}\n\n"]),
            media_type="text/event-stream",
            status_code=400,
        )

    # Trim history to max configured length
    max_history = settings.session.max_history_length
    if len(history) > max_history:
        history = history[-max_history:]

    # --- 4 & 5. Build contents, call Gemini, stream SSE ---
    contents = _build_contents(history, user_message)
    logger.info(f"Streaming response for message: {user_message[:80]}...")

    return StreamingResponse(
        _stream_gemini(contents),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session.session_id,
        },
    )
