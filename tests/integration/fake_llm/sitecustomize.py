"""Integration-test only: registers a scripted ``fake-*`` model with ADK.

Put this directory on PYTHONPATH and set ``GEMINI_MODEL=fake-sales`` to run the
real services (A2A, MCP, PostgreSQL) without calling Gemini. Never used in
production images.
"""

import json
import re
import uuid
from typing import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models.registry import LLMRegistry
from google.genai import types

_ADDR = re.compile(r"(?P<street>\d+[^,]+),\s*(?P<city>[A-Za-z .]+?),?\s+(?P<state>[A-Z]{2})\s+(?P<zip>\d{5})")


def _text(content) -> str:
    return " ".join(p.text for p in (content.parts or []) if getattr(p, "text", None)) if content else ""


def _route(message: str) -> str:
    m = message.lower()
    for words, target in (
        (("quote", "price", "pricing", "cost"), "offer_management_agent"),
        (("we're", "we are", "our company", "register"), "discovery_agent"),
        (("product", "catalog", "fiber plans"), "product_agent"),
        (("schedule", "install"), "service_fulfillment_agent"),
        (("pay", "card"), "payment_agent"),
        (("order", "cart"), "order_agent"),
    ):
        if any(w in m for w in words):
            return target
    return "faq_agent"


class FakeSalesLlm(BaseLlm):
    model: str = "fake-sales"

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"fake-.*"]

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        contents = llm_request.contents or []
        last = contents[-1] if contents else None
        cfg = llm_request.config
        if cfg is not None and getattr(cfg, "response_schema", None) is not None:
            payload = _text(last)
            try:
                message = json.loads(payload).get("message", payload)
            except ValueError:
                message = payload
            yield self._reply(json.dumps({"target": _route(message), "reason": "fake"}))
            return
        model_turns = [c for c in contents if c.role == "model"]
        called = bool(model_turns) and any(p.function_call for p in (model_turns[-1].parts or []))
        responses = [p.function_response for c in contents for p in (c.parts or []) if p.function_response]
        if called and responses:
            # ADK 2.x may append the dynamic instruction after the tool result,
            # so "our last model turn was a function call" marks post-tool state.
            fr = responses[-1]
            resp = {k: v for k, v in (fr.response or {}).items() if k != "_context_update"}
            yield self._reply(f"[{fr.name}] {json.dumps(resp, default=str)[:600]}")
            return
        tools = set(llm_request.tools_dict or {})
        user_text = " ".join(_text(c) for c in contents if c.role == "user")
        call = self._pick_call(tools, user_text)
        if call:
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name=call[0], args=call[1]))]))
        else:
            yield self._reply(f"ack: {user_text[-120:]}")

    @staticmethod
    def _pick_call(tools: set, text: str):
        if "check_service_availability" in tools:
            m = re.search(r"address: (\{[^{}]*\})", text)
            if m:
                a = json.loads(m.group(1))
                return "check_service_availability", {k: a[k] for k in ("street", "city", "state", "zip_code")}
        if "add_new_company" in tools:
            m = _ADDR.search(text)
            name = re.search(r"(?:We're|We are)\s+([^,]+?)\s+at\b", text)
            if m and name:
                return "add_new_company", {
                    "company_name": f"{name.group(1)} {uuid.uuid4().hex[:6]}", "industry": "Technology",
                    "region": "Northeast", "street": m["street"].strip(), "city": m["city"].strip(),
                    "state": m["state"], "zip_code": m["zip"],
                }
        if "list_available_products" in tools:
            return "list_available_products", {"category": "internet"}
        if "generate_offer_quote" in tools:
            return None
        return None

    @staticmethod
    def _reply(text: str) -> LlmResponse:
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


LLMRegistry.register(FakeSalesLlm)
