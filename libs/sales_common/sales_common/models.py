"""Gemini model wrapper for agents: retry once on an empty response.

Gemini 3 occasionally returns a response with no text and no function call
(seen intermittently in golden evals for the faq, payment and product agents),
which ADK turns into an empty agent reply. ``ResilientGemini`` repeats such a
non-streaming call once. Streaming calls pass through unchanged.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from google.adk.models.google_llm import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from .config import model_name

logger = logging.getLogger("sales_common.models")


def is_empty_response(response: LlmResponse) -> bool:
    """No text, no function call, no error: nothing the agent can use."""
    if response.error_code:
        return False
    parts = response.content.parts if response.content and response.content.parts else []
    return not any((p.text and not p.thought) or p.function_call for p in parts)


class ResilientGemini(Gemini):
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if stream:
            async for response in super().generate_content_async(llm_request, stream=True):
                yield response
            return
        responses = [r async for r in super().generate_content_async(llm_request, stream=False)]
        if responses and is_empty_response(responses[-1]):
            logger.warning("Empty model response (finish=%s); retrying once", responses[-1].finish_reason)
            responses = [r async for r in super().generate_content_async(llm_request, stream=False)]
        for response in responses:
            yield response


def agent_model() -> ResilientGemini:
    """The model every agent uses by default (``GEMINI_MODEL``)."""
    return ResilientGemini(model=model_name())
