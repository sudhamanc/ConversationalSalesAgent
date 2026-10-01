"""HTTP/SSE client for the gateway chat API (shared by e2e_test.py and evals/test_journeys.py).

``post_json`` for ``POST /api/session``, ``stream_sse`` + ``run_turn`` for a streamed
``POST /api/chat`` turn. Uses httpx when installed, otherwise only the standard library.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Iterator, Optional

try:  # optional dependency
    import httpx
except ImportError:  # pragma: no cover - depends on the environment
    httpx = None  # type: ignore[assignment]

import urllib.error
import urllib.request


class GatewayUnreachable(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# HTTP (httpx if available, else urllib)
# ---------------------------------------------------------------------------


def post_json(url: str, body: dict, headers: dict, timeout: float) -> dict:
    data = json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json", **headers}
    try:
        if httpx is not None:
            resp = httpx.post(url, content=data, headers=hdrs, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as exc:  # connection refused, HTTP error, bad JSON
        raise GatewayUnreachable(f"POST {url} failed: {type(exc).__name__}: {exc}") from exc


def stream_sse(url: str, body: dict, headers: dict, timeout: float) -> Iterator[dict]:
    """Yield parsed ``data:`` payloads from an SSE POST response."""
    data = json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json", "Accept": "text/event-stream", **headers}

    def parse(line: str) -> Optional[dict]:
        line = line.strip()
        if not line.startswith("data:"):
            return None
        raw = line[5:].strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    if httpx is not None:
        try:
            with httpx.stream("POST", url, content=data, headers=hdrs, timeout=timeout) as resp:
                if resp.status_code != 200:
                    resp.read()
                    yield {"type": "error", "content": f"HTTP {resp.status_code}: {resp.text[:300]}"}
                    return
                for line in resp.iter_lines():
                    payload = parse(line)
                    if payload is not None:
                        yield payload
        except httpx.HTTPError as exc:
            yield {"type": "error", "content": f"{type(exc).__name__}: {exc}"}
        return

    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw_line in resp:
                payload = parse(raw_line.decode("utf-8", errors="replace"))
                if payload is not None:
                    yield payload
    except urllib.error.HTTPError as exc:
        yield {"type": "error", "content": f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        yield {"type": "error", "content": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------
# Turn result + assertions
# ---------------------------------------------------------------------------


@dataclass
class Turn:
    events: list[dict] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)  # token authors, first-seen order
    text: str = ""
    errors: list[str] = field(default_factory=list)
    done: bool = False
    seconds: float = 0.0

    def of_type(self, kind: str) -> list[dict]:
        return [e for e in self.events if e.get("type") == kind]


def run_turn(base_url: str, token: str, message: str, timeout: float) -> Turn:
    turn = Turn()
    start = time.monotonic()
    parts: list[str] = []
    for event in stream_sse(f"{base_url}/api/chat", {"message": message}, {"Authorization": f"Bearer {token}"}, timeout):
        turn.events.append(event)
        kind = event.get("type")
        if kind == "token":
            author = event.get("author")
            content = event.get("content") or ""
            if author and content.strip() and author not in turn.authors:
                turn.authors.append(author)
            parts.append(content)
        elif kind == "error":
            turn.errors.append(str(event.get("content", "unknown error")))
        elif kind == "done":
            turn.done = True
    turn.text = "".join(parts)
    turn.seconds = time.monotonic() - start
    return turn
