import asyncio

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from sales_common import models


def _resp(text=None, call=None):
    parts = []
    if text is not None:
        parts.append(types.Part(text=text))
    if call:
        parts.append(types.Part(function_call=types.FunctionCall(name=call, args={})))
    return LlmResponse(content=types.Content(role="model", parts=parts))


def test_is_empty_response():
    assert models.is_empty_response(_resp())
    assert models.is_empty_response(_resp(text=""))
    assert not models.is_empty_response(_resp(text="hi"))
    assert not models.is_empty_response(_resp(call="get_order"))
    assert not models.is_empty_response(LlmResponse(error_code="X"))


def test_retries_once_on_empty(monkeypatch):
    calls = []

    async def fake(self, req, stream=False):
        calls.append(stream)
        yield _resp() if len(calls) == 1 else _resp(text="answer")

    monkeypatch.setattr(models.Gemini, "generate_content_async", fake)
    model = models.ResilientGemini(model="gemini-test")

    async def run():
        return [r async for r in model.generate_content_async(LlmRequest(), stream=False)]

    out = asyncio.run(run())
    assert len(calls) == 2 and out[-1].content.parts[0].text == "answer"
