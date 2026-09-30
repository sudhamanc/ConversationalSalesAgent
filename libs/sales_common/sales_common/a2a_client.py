"""``RemoteA2aAgent`` factory used by the gateway orchestration workflow."""

from __future__ import annotations

from typing import Any, Callable, Optional

import httpx
from google.adk.a2a.agent import A2aRemoteAgentConfig, RemoteA2aAgent
from google.genai import types as genai_types

from .auth import ServiceAuth

AGENT_CARD_PATH = "/.well-known/agent-card.json"

#: Session-state key holding the exact text to send to the next remote agent.
#: ``RemoteA2aAgent`` ignores a workflow node's input and by default replays the
#: caller's session history (other agents' turns included); the orchestrator
#: instead writes the directed message here and :func:`outbound_message_builder`
#: sends only that. Cross-agent context travels as forwarded journey metadata.
OUTBOUND_MESSAGE_KEY = "a2a_outbound_message"

MetaProvider = Callable[[Any, Any], dict[str, Any]]


def card_url(base_url: str) -> str:
    return base_url.rstrip("/") + AGENT_CARD_PATH


def outbound_message_builder(ctx, _agent_name: str, part_converter):
    """``context_builder`` for ``RemoteA2aAgent``: send only the directed message.

    Returns ``(parts, None)``; ``None`` lets ``forward_session_id_as_context_id``
    use the gateway session id as the stable remote context id.
    """
    text = str(ctx.session.state.get(OUTBOUND_MESSAGE_KEY) or "")
    if not text and ctx.user_content and ctx.user_content.parts:
        text = " ".join(p.text for p in ctx.user_content.parts if p.text)
    part = part_converter(genai_types.Part(text=text)) if text else None
    return ([part] if part is not None else []), None


def remote_agent(
    name: str,
    base_url: str,
    *,
    description: str = "",
    meta_provider: Optional[MetaProvider] = None,
    timeout: float = 120.0,
) -> RemoteA2aAgent:
    """Build a ``RemoteA2aAgent`` for an agent service at ``base_url``.

    * the remote A2A context id is the gateway session id, so each gateway
      session maps to one stable remote session per agent
    * requests (card fetch + JSON-RPC) carry service auth (``SERVICE_AUTH``)
    * ``meta_provider(ctx, message)`` attaches forwarded journey context
    """
    client = httpx.AsyncClient(timeout=httpx.Timeout(timeout), auth=ServiceAuth())
    return RemoteA2aAgent(
        name=name,
        agent_card=card_url(base_url),
        description=description,
        httpx_client=client,
        timeout=timeout,
        a2a_request_meta_provider=meta_provider,
        context_builder=outbound_message_builder,
        config=A2aRemoteAgentConfig(forward_session_id_as_context_id=True),
    )
