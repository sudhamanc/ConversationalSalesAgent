"""Turn ADK session events into eval ``Invocation``s (one per user turn).

Used by ``record_golden.py`` (in-process agent runs) and ``test_journeys.py``
(gateway session loaded from PostgreSQL). For each user turn it collects:

* ``intermediate_data.tool_uses`` / ``tool_responses`` from function call and
  response parts, in event order;
* ``final_response``: the last non-partial, non-thought text produced by an
  allowed author;
* the ordered list of authors that produced text (the journey's agent trajectory).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.genai import types


@dataclass
class Turn:
    invocation: Invocation
    authors: list[str] = field(default_factory=list)


def _text(parts: Iterable[types.Part]) -> str:
    return "".join(p.text for p in parts if p.text and not p.thought)


def events_to_turns(
    events: Iterable[Any],
    allowed_authors: Optional[set[str]] = None,
    user_messages: Optional[list[str]] = None,
) -> list[Turn]:
    """``user_messages``: when given, only user events with the next of these texts open a
    turn (workflow-internal user-role events, e.g. handoff instructions, are ignored)."""
    turns: list[Turn] = []
    pending_messages = list(user_messages) if user_messages is not None else None
    current: Optional[Turn] = None
    final_text = ""

    def close() -> None:
        if current is not None:
            current.invocation.final_response = types.Content(
                role="model", parts=[types.Part(text=final_text)]
            )

    for event in events:
        content = getattr(event, "content", None)
        parts = list(content.parts or []) if content else []
        if event.author == "user":
            text = _text(parts)
            if not text:
                continue
            if pending_messages is not None:
                if not pending_messages or text.strip() != pending_messages[0].strip():
                    continue
                pending_messages.pop(0)
            close()
            final_text = ""
            current = Turn(
                Invocation(
                    invocation_id=getattr(event, "invocation_id", "") or f"e-{uuid.uuid4().hex[:8]}",
                    user_content=types.Content(role="user", parts=[types.Part(text=text)]),
                    intermediate_data=IntermediateData(),
                )
            )
            turns.append(current)
            continue
        if current is None or getattr(event, "partial", False):
            continue
        data = current.invocation.intermediate_data
        for part in parts:
            if part.function_call:
                data.tool_uses.append(
                    types.FunctionCall(name=part.function_call.name, args=dict(part.function_call.args or {}))
                )
            if part.function_response:
                data.tool_responses.append(part.function_response)
        if allowed_authors is not None and event.author not in allowed_authors:
            continue
        text = _text(parts)
        if text.strip():
            final_text = text
            if not current.authors or current.authors[-1] != event.author:
                current.authors.append(event.author)
    close()
    return turns
