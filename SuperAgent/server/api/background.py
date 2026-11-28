"""Fire-and-forget calls from the gateway to agent services.

* :func:`warm_services` (``POST /api/session``): one request to every agent
  service so Cloud Run starts scaled-to-zero instances while the customer reads
  the greeting (spec: conversation-orchestration, services warmed at session
  start): ``GET /.well-known/agent-card.json`` (not ``/healthz``: Cloud Run's
  front end answers ``/healthz`` itself with 404, so the request never reaches the
  container). Customer communication gets ``POST /dispatch``, which also delivers
  notifications left pending. At most once per ``WARMUP_INTERVAL_S`` per process.
* :func:`notification_statuses` (end of a turn): the delivery status of the
  notifications the turn queued, after waiting briefly for the dispatch request
  (spec: conversation-orchestration, notification delivery status reported to
  the UI). Rows still pending are kept per session and reported by a later turn.
* :func:`request_dispatch` (a turn whose tool result queued a notification): the
  customer communication service delivers pending notifications inside the
  request (spec: conversation-orchestration, email dispatch triggered by queued
  notifications). At most one call in flight; triggers that arrive meanwhile
  cause exactly one more call after it.

Calls carry service authentication (``sales_common.auth.service_headers``: a
Google ID token on Cloud Run, nothing locally). Failures are logged, never raised.
The target service does its work inside its own request, so it has CPU even when
the gateway's request has already finished.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx

from sales_common import db
from sales_common.auth import service_headers
from super_agent.config import settings
from super_agent.registry import AGENTS, spec
from utils.logger import get_logger

logger = get_logger(__name__)

COMMUNICATION_AGENT = "customer_communication_agent"
#: Served by every A2A agent service. ``/healthz`` cannot be used from outside on Cloud Run.
WARMUP_PATH = "/.well-known/agent-card.json"
_TIMEOUT_S = 90.0  # a cold start can take a minute

_tasks: set[asyncio.Task] = set()
_last_warmup: Optional[float] = None
_dispatch_running = False
_dispatch_again = False
_dispatch_idle: Optional[asyncio.Event] = None  # set while no dispatch request is in flight
_unresolved: dict[str, list[str]] = {}  # session id -> notification ids still pending
_MAX_UNRESOLVED_SESSIONS = 1000
#: Test hook: an ``httpx`` transport for the outgoing calls.
transport: Optional[httpx.AsyncBaseTransport] = None


def _spawn(coro) -> asyncio.Task:
    task = asyncio.get_running_loop().create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return task


def dispatch_url() -> str:
    return spec(COMMUNICATION_AGENT).base_url().rstrip("/") + "/dispatch"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=_TIMEOUT_S, transport=transport)


# --- warm-up -----------------------------------------------------------------


def warm_services(now: Optional[float] = None) -> bool:
    """Start the warm-up round unless disabled or done recently. Returns True when started."""
    global _last_warmup
    if not settings.server.warmup_enabled:
        return False
    now = time.monotonic() if now is None else now
    if _last_warmup is not None and now - _last_warmup < settings.server.warmup_interval_s:
        return False
    _last_warmup = now
    _spawn(_warm_all())
    return True


async def _warm_all() -> None:
    async with _client() as client:
        await asyncio.gather(*(_warm_one(client, agent.name) for agent in AGENTS))


async def _warm_one(client: httpx.AsyncClient, name: str) -> None:
    base = spec(name).base_url().rstrip("/")
    started = time.monotonic()
    try:
        if name == COMMUNICATION_AGENT:
            url = base + "/dispatch"
            response = await client.post(url, headers=service_headers(url))
        else:
            url = base + WARMUP_PATH
            response = await client.get(url, headers=service_headers(url))
        logger.info("Warmed %s: %s in %.1fs", name, response.status_code, time.monotonic() - started)
    except Exception as exc:  # best effort
        logger.info("Warm-up of %s failed: %s", name, type(exc).__name__)


# --- notification dispatch ---------------------------------------------------


def request_dispatch() -> None:
    """Ask the customer communication service to deliver pending notifications now."""
    global _dispatch_running, _dispatch_again
    if _dispatch_running:
        _dispatch_again = True
        return
    _dispatch_running = True
    _idle_event().clear()
    _spawn(_dispatch_loop())


def _idle_event() -> asyncio.Event:
    global _dispatch_idle
    if _dispatch_idle is None:
        _dispatch_idle = asyncio.Event()
        _dispatch_idle.set()
    return _dispatch_idle


async def _dispatch_loop() -> None:
    global _dispatch_running, _dispatch_again
    try:
        while True:
            _dispatch_again = False
            await _dispatch_once()
            if not _dispatch_again:
                return
    finally:
        _dispatch_running = False
        _idle_event().set()


async def _dispatch_once() -> None:
    url = dispatch_url()
    try:
        async with _client() as client:
            response = await client.post(url, headers=service_headers(url))
        try:
            counts = response.json()
        except ValueError:
            counts = {}
        logger.info("Notification dispatch: %s %s", response.status_code,
                    {k: counts.get(k) for k in ("processed", "sent", "simulated", "failed") if k in counts})
    except Exception as exc:  # rows stay pending; the next trigger or the service's loop delivers them
        logger.warning("Notification dispatch request failed: %s", type(exc).__name__)


# --- delivery status -----------------------------------------------------------


def _read_statuses(ids: list[str]) -> dict[str, str]:
    rows = db.fetch_all(
        "SELECT notification_id, status FROM notifications WHERE notification_id = ANY(%s)", (ids,)
    )
    return {row["notification_id"]: row["status"] for row in rows}


async def notification_statuses(session_id: str, ids: list[str], wait_s: Optional[float] = None) -> dict[str, str]:
    """Status of the session's queued notifications that are no longer ``pending``.

    Waits up to ``wait_s`` (``NOTIFY_STATUS_WAIT_S``) for an in-flight dispatch
    request, then reads the rows. Ids still pending (or unknown) are kept for the
    session's next call; delivered ones are returned once.
    """
    wanted = list(dict.fromkeys(_unresolved.pop(session_id, []) + list(ids)))
    if not wanted:
        return {}
    wait_s = settings.server.notify_status_wait_s if wait_s is None else wait_s
    if _dispatch_running and wait_s > 0:
        try:
            await asyncio.wait_for(_idle_event().wait(), timeout=wait_s)
        except asyncio.TimeoutError:
            pass
    try:
        statuses = await asyncio.to_thread(_read_statuses, wanted)
    except Exception as exc:  # best effort: report next turn
        logger.warning("Could not read notification status: %s", type(exc).__name__)
        statuses = {}
    done = {nid: status for nid, status in statuses.items() if status != "pending"}
    pending = [nid for nid in wanted if nid in statuses and nid not in done]
    if pending:
        if len(_unresolved) >= _MAX_UNRESOLVED_SESSIONS:
            _unresolved.pop(next(iter(_unresolved)))
        _unresolved[session_id] = pending
    return done


def _reset_for_tests() -> None:
    global _last_warmup, _dispatch_running, _dispatch_again, _dispatch_idle
    _last_warmup = None
    _dispatch_running = False
    _dispatch_again = False
    _dispatch_idle = None
    _unresolved.clear()
