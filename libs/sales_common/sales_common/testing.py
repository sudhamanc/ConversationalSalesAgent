"""Test helpers: deterministic scripted model (no network, no API key)."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Optional

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types


class ScriptLlm(BaseLlm):
    """Replies with scripted steps.

    Each step is either ``{"call": name, "args": {...}}`` (a function call) or
    ``{"text": "..."}``. After the steps run out, the last text is repeated.
    ``json_reply`` makes every reply the given dict serialized as JSON (for
    ``output_schema`` agents).
    """

    model: str = "script-llm"
    steps: list = []
    json_reply: Optional[dict] = None
    requests: list = []

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.requests.append(llm_request)
        if self.json_reply is not None:
            yield LlmResponse(
                content=types.Content(role="model", parts=[types.Part(text=json.dumps(self.json_reply))])
            )
            return
        contents = llm_request.contents or []
        calls_made = sum(
            1 for c in contents if c.role == "model" and any(p.function_call for p in (c.parts or []))
        )
        texts_made = sum(
            1 for c in contents if c.role == "model" and any(p.text for p in (c.parts or []))
        )
        last_is_response = bool(contents) and any(
            p.function_response for p in (contents[-1].parts or [])
        )
        calls = [s for s in self.steps if "call" in s]
        texts = [s["text"] for s in self.steps if "text" in s] or ["ok"]
        if calls_made < len(calls) and (calls_made == 0 or last_is_response):
            step = calls[calls_made]
            part = types.Part(
                function_call=types.FunctionCall(name=step["call"], args=step.get("args", {}))
            )
        else:
            part = types.Part(text=texts[min(texts_made, len(texts) - 1)])
        yield LlmResponse(content=types.Content(role="model", parts=[part]))
