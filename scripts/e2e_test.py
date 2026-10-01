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
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Optional

from e2e_client import GatewayUnreachable, Turn, httpx, post_json, run_turn


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------


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
