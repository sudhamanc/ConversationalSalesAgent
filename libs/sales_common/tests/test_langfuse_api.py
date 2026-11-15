"""sales_common.langfuse_api: score payloads, auth and error handling (no network)."""

from __future__ import annotations

import base64
import json
from datetime import datetime

import httpx
import pytest

from sales_common.langfuse_api import LangfuseApiError, LangfuseClient


def _client(handler) -> LangfuseClient:
    return LangfuseClient("https://lf.example", "pk-lf-1", "sk-lf-2", transport=httpx.MockTransport(handler))


async def test_create_score_posts_array_with_basic_auth():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(202, json={"message": "Accepted"})

    await _client(handler).create_score(
        name="user_feedback",
        value=True,
        trace_id="a" * 32,
        score_id="b" * 32,
        data_type="BOOLEAN",
        environment="local",
        timestamp=datetime(2026, 11, 14, 12, 0, 0),
    )
    assert seen["url"] == "https://lf.example/api/public/scores"
    assert seen["auth"] == "Basic " + base64.b64encode(b"pk-lf-1:sk-lf-2").decode()
    assert seen["body"] == [
        {
            "id": "b" * 32,
            "traceId": "a" * 32,
            "name": "user_feedback",
            "value": 1.0,
            "dataType": "BOOLEAN",
            "environment": "local",
            "timestamp": "2026-11-14T12:00:00+00:00",
        }
    ]


@pytest.mark.parametrize("status", [207, 400, 401, 500])
async def test_rejections_raise(status):
    client = _client(lambda request: httpx.Response(status, json={"errors": ["bad"]}))
    with pytest.raises(LangfuseApiError):
        await client.create_score(name="x", value=1, trace_id="a" * 32)


def test_from_env_requires_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    assert LangfuseClient.from_env() is None
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com/")
    client = LangfuseClient.from_env()
    assert client is not None and client.host == "https://cloud.langfuse.com"
