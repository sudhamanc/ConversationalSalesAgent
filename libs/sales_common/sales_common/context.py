"""Journey context forwarding across the A2A boundary.

A2A carries message parts only: the gateway's session state is not sent to a
remote agent, and a remote agent's ``state_delta`` is not returned. This module
bridges both directions:

* Gateway -> agent: :func:`build_forwarded_metadata` produces A2A request
  metadata. On the agent side, :func:`import_forwarded_context`
  (``before_agent_callback``) copies it from
  ``run_config.custom_metadata["a2a_metadata"]`` into session state.
* Agent -> gateway: :func:`export_context_delta` (``after_tool_callback``)
  appends ``_context_update`` to a tool's response whenever the tool changed a
  journey key. The gateway's ``ContextBridgePlugin`` merges it back into state
  using :func:`extract_context_updates`.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Iterable, Optional

logger = logging.getLogger("sales_common.context")

#: Session-scoped journey keys shared by every agent.
JOURNEY_KEYS: tuple[str, ...] = (
    "customer_context",
    "serviceability_context",
    "offer_context",
    "order_context",
    "payment_context",
)

CONTEXT_UPDATE_KEY = "_context_update"
METADATA_KEY = "journey"
TRANSCRIPT_STATE_KEY = "journey_transcript"
PROFILE_STATE_KEY = "user_profile"
SESSION_REF_STATE_KEY = "gateway_session_id"
#: Today's date for the agent's instruction (``{current_date?}``), set on every turn.
CURRENT_DATE_STATE_KEY = "current_date"

MAX_TRANSCRIPT_CHARS = 2000


def build_forwarded_metadata(
    state: dict[str, Any],
    *,
    session_id: str,
    transcript: str = "",
    user_profile: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Metadata attached to every A2A request sent by the gateway."""
    journey = {k: state.get(k) for k in JOURNEY_KEYS if state.get(k) is not None}
    return {
        METADATA_KEY: {
            "context": journey,
            "session_ref": session_id,
            "transcript": transcript[-MAX_TRANSCRIPT_CHARS:],
            "user_profile": user_profile or {},
        }
    }


def _forwarded(callback_context) -> dict[str, Any]:
    run_config = getattr(callback_context, "run_config", None)
    custom = getattr(run_config, "custom_metadata", None) or {}
    meta = custom.get("a2a_metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            return {}
    journey = meta.get(METADATA_KEY) if isinstance(meta, dict) else None
    return journey if isinstance(journey, dict) else {}


def current_date_text(today: Optional[date] = None) -> str:
    """ISO date plus weekday, e.g. ``2026-10-01 (Thursday)``."""
    today = today or date.today()
    return f"{today.isoformat()} ({today.strftime('%A')})"


def import_forwarded_context(callback_context) -> None:
    """``before_agent_callback``: apply forwarded journey context to session state.

    Only known journey keys are imported; values must be JSON objects. Also sets
    ``current_date`` (e.g. "2026-10-01 (Thursday)") on every turn, with or without
    forwarded metadata, so agents never guess today's date. Returns ``None`` so the
    agent always runs.
    """
    state = callback_context.state
    state[CURRENT_DATE_STATE_KEY] = current_date_text()
    journey = _forwarded(callback_context)
    if not journey:
        return None
    context = journey.get("context") or {}
    for key in JOURNEY_KEYS:
        value = context.get(key)
        if isinstance(value, dict):
            state[key] = value
    transcript = journey.get("transcript")
    if isinstance(transcript, str):
        state[TRANSCRIPT_STATE_KEY] = transcript[-MAX_TRANSCRIPT_CHARS:]
    profile = journey.get("user_profile")
    if isinstance(profile, dict):
        state[PROFILE_STATE_KEY] = profile
    session_ref = journey.get("session_ref")
    if isinstance(session_ref, str):
        state[SESSION_REF_STATE_KEY] = session_ref
    return None


def export_context_delta(tool, args, tool_context, tool_response):
    """``after_tool_callback``: surface journey-key changes in the tool response.

    Returns a new response dict containing ``_context_update`` when the tool
    wrote any journey key during this call; otherwise ``None`` (unchanged).
    """
    delta = getattr(getattr(tool_context, "actions", None), "state_delta", None) or {}
    update = {k: delta[k] for k in JOURNEY_KEYS if k in delta and delta[k] is not None}
    if not update:
        return None
    if isinstance(tool_response, dict):
        response = dict(tool_response)
    elif isinstance(tool_response, str):
        try:
            parsed = json.loads(tool_response)
            response = parsed if isinstance(parsed, dict) else {"result": tool_response}
        except ValueError:
            response = {"result": tool_response}
    else:
        response = {"result": tool_response}
    response[CONTEXT_UPDATE_KEY] = update
    return response


def extract_context_updates(responses: Iterable[Any]) -> dict[str, Any]:
    """Collect ``_context_update`` payloads from function-response dicts."""
    merged: dict[str, Any] = {}
    for response in responses:
        payload = response
        if isinstance(payload, dict) and CONTEXT_UPDATE_KEY not in payload and "result" in payload:
            payload = payload["result"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except ValueError:
                continue
        if not isinstance(payload, dict):
            continue
        update = payload.get(CONTEXT_UPDATE_KEY)
        if isinstance(update, dict):
            for key in JOURNEY_KEYS:
                if isinstance(update.get(key), dict):
                    merged[key] = update[key]
    return merged


def chain_callbacks(*callbacks):
    """Return a list of non-None callbacks (ADK runs them in order; first truthy wins)."""
    return [cb for cb in callbacks if cb is not None]
