#!/usr/bin/env python3
"""End-to-end check of the sales journey through the gateway's SSE chat API.

Usage::

    python scripts/e2e_test.py [--base-url http://127.0.0.1:8000] [--timeout 180] [--verbose]

Creates a chat session (``POST /api/session``), then runs a scripted conversation
(``POST /api/chat``) and asserts, per step, which agent(s) answered and key fields:

  1. greeting       -> greeting_agent
  2. discovery      -> discovery_agent AND serviceability_agent tokens in the same turn
                       (company registration with an address triggers the handoff)
  3. product        -> product_agent
  4. quote          -> offer_management_agent + a ``structured_card`` of card_type "quote"
                       carrying an ``offer_id``
  5. order          -> order_agent + a ``cart_update`` event

Exits 1 on the first failed assertion, 2 when the gateway cannot be reached, 0 when
every step passes. Uses httpx when installed, otherwise only the standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional

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


Check = Callable[[Turn], Optional[str]]  # returns a failure message, or None when OK


def expect_authors(*names: str) -> Check:
    def check(turn: Turn) -> Optional[str]:
        missing = [n for n in names if n not in turn.authors]
        if missing:
            return f"expected tokens from {', '.join(missing)}; got authors {turn.authors or '[]'}"
        return None

    return check


def expect_quote_card(turn: Turn) -> Optional[str]:
    cards = [e for e in turn.of_type("structured_card") if e.get("card_type") == "quote"]
    if not cards:
        return "expected a structured_card with card_type 'quote'"
    data = cards[-1].get("data") or {}
    if not data.get("offer_id"):
        return "quote card has no offer_id"
    return None


def expect_cart_update(turn: Turn) -> Optional[str]:
    if not turn.of_type("cart_update"):
        return "expected a cart_update event"
    return None


@dataclass
class Step:
    name: str
    message: str
    expected: str  # human-readable expectation for the table
    checks: list[Check]


STEPS: list[Step] = [
    Step(
        "greeting",
        "Hello!",
        "greeting_agent",
        [expect_authors("greeting_agent")],
    ),
    Step(
        "discovery",
        "Hi, we are Apex Digital Inc at 1601 Market St, Philadelphia, PA 19103. We are a technology "
        "company with 50 employees and need business fiber internet within a month; budget is approved "
        "and I am the CEO, Sam Rivera (sam@apexdigital.com, 215-555-0400). Please register us.",
        "discovery_agent + serviceability_agent",
        [expect_authors("discovery_agent", "serviceability_agent")],
    ),
    Step(
        "product",
        "Show me the details of Business Fiber 5 Gbps.",
        "product_agent",
        [expect_authors("product_agent")],
    ),
    Step(
        "quote",
        "Give me a quote for Business Fiber 5 Gbps with a 24-month contract.",
        "offer_management_agent + quote card",
        [expect_authors("offer_management_agent"), expect_quote_card],
    ),
    Step(
        "order",
        "I want to order Business Fiber 5 Gbps from that quote. Please add it to my cart.",
        "order_agent + cart_update",
        [expect_authors("order_agent"), expect_cart_update],
    ),
]


def print_table(rows: list[tuple[str, str, str, str, str]]) -> None:
    headers = ("STEP", "EXPECTED", "AUTHORS", "SECS", "RESULT")
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    fmt = "  ".join("{:<%d}" % w for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for row in rows:
        print(fmt.format(*row))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scripted end-to-end conversation with assertions")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="gateway base URL")
    parser.add_argument("--timeout", type=float, default=180.0, help="seconds per chat turn")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds to wait between turns")
    parser.add_argument("--verbose", "-v", action="store_true", help="print each agent response")
    args = parser.parse_args(argv)
    base_url = args.base_url.rstrip("/")

    print(f"E2E against {base_url} (http client: {'httpx' if httpx is not None else 'urllib'})")
    try:
        session = post_json(f"{base_url}/api/session", {"client_id": str(uuid.uuid4())}, {}, 30.0)
        token = session["token"]
    except (GatewayUnreachable, KeyError) as exc:
        print(f"ERROR: could not create a session: {exc}", file=sys.stderr)
        return 2
    print(f"session {session.get('session_id')}\n")

    rows: list[tuple[str, str, str, str, str]] = []
    failure: Optional[str] = None
    for index, step in enumerate(STEPS):
        if index:
            time.sleep(args.delay)
        turn = run_turn(base_url, token, step.message, args.timeout)
        problems = list(turn.errors)
        if not turn.errors and not turn.done:
            problems.append("stream ended without a 'done' event")
        if not problems:
            problems = [msg for msg in (check(turn) for check in step.checks) if msg]
        result = "PASS" if not problems else "FAIL"
        rows.append((step.name, step.expected, ",".join(turn.authors) or "-", f"{turn.seconds:.1f}", result))
        if args.verbose or problems:
            preview = turn.text.strip().replace("\n", " ")
            print(f"[{step.name}] {preview[:500]}{'...' if len(preview) > 500 else ''}\n")
        if problems:
            failure = f"step '{step.name}': " + "; ".join(problems)
            break

    print_table(rows)
    if failure:
        print(f"\nFAILED {failure}", file=sys.stderr)
        return 1
    print(f"\nALL {len(STEPS)} STEPS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
