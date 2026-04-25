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
import logging

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from google.genai import types

from super_agent.config import settings
from middleware.auth import authenticator
from middleware.rate_limiter import rate_limiter
from utils.logger import get_logger, session_id_var

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)  # Enable debug logging for chat endpoint
router = APIRouter()

# These are set at startup by main.py — avoids circular imports.
_runner = None
_session_service = None
_app_name = None


def _parse_suggestion_payload(raw_text: str) -> list[str]:
    """Parse JSON suggestions payload into a cleaned list."""
    if not raw_text:
        return []

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return []

    candidates = []
    if isinstance(parsed, list):
        candidates = parsed
    elif isinstance(parsed, dict):
        suggestions = parsed.get("suggestions")
        if isinstance(suggestions, list):
            candidates = suggestions

    cleaned: list[str] = []
    for item in candidates:
        text = str(item).strip()
        if not text:
            continue
        # Keep suggestions editable and generic; avoid over-specific hard values.
        text = text.replace("\n", " ").strip()
        if text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= 3:
            break

    return cleaned


def _generate_dynamic_suggestions(user_message: str, assistant_message: str, author: str | None) -> list[str]:
    """Generate generic editable next-step suggestions using LLM; return empty list on failure."""
    if not assistant_message.strip():
        return []

    try:
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client()
        prompt = (
            "You generate next-step suggestions for a B2B telecom sales chat.\n"
            "Return ONLY JSON.\n"
            "Output format: {\"suggestions\": [\"...\", \"...\", \"...\"]}\n"
            "Rules:\n"
            "- Exactly 3 suggestions\n"
            "- Suggestions must be generic and editable templates\n"
            "- Do NOT include specific addresses, IDs, account numbers, emails, phone numbers, or names\n"
            "- Keep each suggestion under 80 characters\n"
            "- Keep suggestions actionable and relevant to the assistant response\n"
            f"Agent author: {author or 'agent'}\n"
            f"User message: {user_message}\n"
            f"Assistant response: {assistant_message}\n"
        )

        response = client.models.generate_content(
            model=settings.model.model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=180,
                response_mime_type="application/json",
            ),
        )

        response_text = getattr(response, "text", "") or ""
        return _parse_suggestion_payload(response_text)
    except Exception as error:
        logger.warning("Dynamic suggestion generation failed: %s", error)
        return []


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
    """
    Stream ADK agent responses via SSE.
    
    Natural two-step workflow:
    1. User provides company info → DiscoveryAgent responds and asks about serviceability
    2. User says "yes" → SuperAgent routes to ServiceabilityAgent
    
    Each user message is one turn. No automatic recursive routing.
    """
    from google.adk.runners import RunConfig
    
    try:
        await _ensure_adk_session(user_id, session_id)
        
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        )
        
        run_config = RunConfig()
        
        logger.info(f"Processing user message: {user_message[:80]}")
        logger.debug(f"Full user message: {user_message}")
        logger.debug(f"Session ID: {session_id}, User ID: {user_id}")
        logger.debug(f"Model: {_runner.agent.model}")
        
        sent_content = False
        response_parts: list[str] = []
        last_text_author: str | None = None
        async for event in _runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
            run_config=run_config,
        ):
            if event.error_message:
                # If we already streamed text content to the client and the error
                # is "Unknown error." (caused by Gemini returning an empty
                # response after a mixed text+function_call turn), treat the
                # already-streamed text as the valid response instead of failing.
                if sent_content and "Unknown error" in (event.error_message or ""):
                    logger.warning(
                        "Suppressing '%s' — text was already streamed (%d chars). "
                        "Completing turn normally.",
                        event.error_message,
                        sum(len(p) for p in response_parts),
                    )
                    # Don't return — let the loop continue to hit turn_complete
                    continue
                logger.error(f"Agent error: {event.error_message}")
                yield f"data: {json.dumps({'type': 'error', 'content': event.error_message})}\n\n"
                return
            
            if event.content and hasattr(event.content, 'parts') and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        logger.debug(f"Streaming token from {event.author}: {part.text[:50]}...")
                        response_parts.append(part.text)
                        last_text_author = event.author or last_text_author
                        payload = json.dumps({
                            "type": "token",
                            "content": part.text,
                            "author": event.author or "agent",
                        })
                        yield f"data: {payload}\n\n"
                        sent_content = True

                    # Emit cart_update events for cart/order tool responses
                    if hasattr(part, 'function_response') and part.function_response:
                        fn_name = getattr(part.function_response, 'name', '')
                        fn_response = getattr(part.function_response, 'response', None)
                        cart_tools = {'create_cart', 'add_to_cart', 'remove_from_cart', 'get_cart', 'clear_cart'}
                        order_tools = {'create_order', 'modify_order', 'get_order'}
                        if isinstance(fn_response, dict) and fn_response.get('success'):
                            cart_data = None
                            if fn_name in cart_tools:
                                cart_data = fn_response.get('cart', fn_response)
                            elif fn_name in order_tools:
                                order_payload = fn_response.get('order') if isinstance(fn_response.get('order'), dict) else None
                                items = []
                                total_amount = fn_response.get('total_amount', 0)
                                cart_id = fn_response.get('order_id', '')

                                if order_payload:
                                    if isinstance(order_payload.get('items'), list):
                                        items = order_payload.get('items', [])
                                    total_amount = order_payload.get('total_amount', total_amount)
                                    cart_id = order_payload.get('order_id', cart_id)
                                elif isinstance(fn_response.get('items'), list):
                                    items = fn_response.get('items', [])

                                if items:
                                    cart_data = {
                                        'cart_id': cart_id,
                                        'items': items,
                                        'total_amount': total_amount,
                                    }
                                else:
                                    logger.debug("Skipping cart_update for %s: no structured items in response", fn_name)
                            if cart_data:
                                cart_payload = json.dumps({
                                    "type": "cart_update",
                                    "tool": fn_name,
                                    "data": cart_data,
                                    "author": event.author or "order_agent",
                                })
                                logger.debug(f"Emitting cart_update from {fn_name}")
                                yield f"data: {cart_payload}\n\n"
            
            if event.turn_complete:
                logger.info(f"Turn complete from {event.author}")
                # If no content was sent, send a fallback message
                if not sent_content:
                    logger.warning(f"Empty response from agent, sending fallback")
                    fallback_payload = json.dumps({
                        "type": "token",
                        "content": "I'm ready to assist you! How can I help with your business telecommunications needs today?",
                        "author": "agent",
                    })
                    yield f"data: {fallback_payload}\n\n"
                else:
                    full_response = "".join(response_parts).strip()
                    suggestion_items = _generate_dynamic_suggestions(
                        user_message=user_message,
                        assistant_message=full_response,
                        author=last_text_author or event.author,
                    )
                    if suggestion_items:
                        suggestion_payload = json.dumps({
                            "type": "suggestions",
                            "author": last_text_author or event.author or "agent",
                            "data": suggestion_items,
                        })
                        yield f"data: {suggestion_payload}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

    except Exception as e:
        error_str = str(e)
        # If text was already streamed and the exception is the "Unknown error"
        # from Gemini returning an empty response after a mixed text+function_call,
        # treat the already-streamed text as the complete response.
        if sent_content and "Unknown error" in error_str:
            logger.warning(
                "Suppressing exception '%s' — text was already streamed (%d chars). "
                "Completing turn with already-sent content.",
                error_str,
                sum(len(p) for p in response_parts),
            )
            full_response = "".join(response_parts).strip()
            suggestion_items = _generate_dynamic_suggestions(
                user_message=user_message,
                assistant_message=full_response,
                author=last_text_author or "agent",
            )
            if suggestion_items:
                suggestion_payload = json.dumps({
                    "type": "suggestions",
                    "author": last_text_author or "agent",
                    "data": suggestion_items,
                })
                yield f"data: {suggestion_payload}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
        logger.error(f"Exception in _stream_agent: {type(e).__name__}: {error_str}", exc_info=True)
        error_msg = f"Agent error: {error_str}"
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"


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
