"""Smoke-run a few chat scenarios against a running gateway.

Usage (gateway on :8000, agents running)::

    python SuperAgent/server/run_scenarios.py            # GATEWAY_URL overrides the base URL

Flow: ``POST /api/session`` with ``{"client_id": <uuid4>}`` -> Bearer token ->
``POST /api/chat`` per message, parsing the SSE ``data: {...}`` lines
(``token`` / ``error`` / ``done`` and the other event types).
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Optional

import httpx

BASE_URL = os.getenv("GATEWAY_URL", "http://localhost:8000").rstrip("/")

SCENARIOS = [
    "Hello",
    "I need internet for 123 Market St, Philadelphia, PA 19107",
    "What is the speed of Fiber 5G?",
    "I'd like to get a quote for Fiber 5G at that address.",
]


def parse_sse_line(line: str) -> Optional[dict]:
    """Return the JSON payload of one ``data: {...}`` SSE line, else None."""
    if not line.startswith("data: "):
        return None
    try:
        payload = json.loads(line[6:])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


async def get_session(client: httpx.AsyncClient, client_id: Optional[str] = None) -> Optional[dict]:
    """Create a gateway session; returns ``{"session_id", "token"}`` or None."""
    try:
        response = await client.post("/api/session", json={"client_id": client_id or str(uuid.uuid4())})
    except httpx.HTTPError as exc:
        print(f"Connection error: {exc}")
        return None
    if response.status_code != 200:
        print(f"Error creating session: {response.status_code} {response.text}")
        return None
    return response.json()


async def run_chat(client: httpx.AsyncClient, token: str, message: str) -> list[dict]:
    """Send one message, print the streamed reply, and return all SSE payloads."""
    print(f"\n--- Sending: {message!r} ---")
    events: list[dict] = []
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with client.stream("POST", "/api/chat", json={"message": message}, headers=headers) as response:
            async for line in response.aiter_lines():
                payload = parse_sse_line(line)
                if payload is None:
                    continue
                events.append(payload)
                kind = payload.get("type")
                if kind == "token":
                    print(payload.get("content", ""), end="", flush=True)
                elif kind == "error":
                    print(f"\n[ERROR {response.status_code}] {payload.get('content')}")
                elif kind == "done":
                    print("\n[DONE]")
                    break
                elif kind in ("activity_update", "structured_card", "cart_update", "suggestions"):
                    print(f"\n[{kind}]", flush=True)
    except httpx.HTTPError as exc:
        print(f"Error during chat: {exc}")
    return events


async def run_scenarios(base_url: str = BASE_URL, scenarios: list[str] = SCENARIOS) -> None:
    timeout = httpx.Timeout(10.0, read=180.0)
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        print("Authenticating...")
        session = await get_session(client)
        if not session:
            print("Failed to authenticate. Is the server running?")
            return
        print(f"Authenticated. Session ID: {session['session_id']}")
        for scenario in scenarios:
            await run_chat(client, session["token"], scenario)
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(run_scenarios())
    except KeyboardInterrupt:
        print("\nStopped.")
