"""Warm-up at session start and on-demand email dispatch (api.background)."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from api import background


@pytest.fixture
def calls(monkeypatch):
    """Record outgoing requests; ``gate`` holds /dispatch responses until released."""
    seen = []
    gate = asyncio.Event()

    async def handler(request):
        seen.append((request.method, str(request.url)))
        if request.url.path == "/dispatch":
            await gate.wait()
            return httpx.Response(200, json={"success": True, "processed": 1, "sent": 1})
        return httpx.Response(200, json={"status": "ok"})

    monkeypatch.setattr(background, "transport", httpx.MockTransport(handler))
    monkeypatch.setattr(background, "settings", SimpleNamespace(
        server=SimpleNamespace(warmup_enabled=True, warmup_interval_s=300)))
    background._reset_for_tests()
    yield SimpleNamespace(seen=seen, gate=gate)
    background._reset_for_tests()


async def _drain():
    while background._tasks:
        await asyncio.gather(*list(background._tasks))


def test_warmup_reaches_every_agent_once_per_interval(calls):
    async def run():
        calls.gate.set()
        assert background.warm_services(now=1000.0) is True
        assert background.warm_services(now=1010.0) is False  # second session, 10 s later
        await _drain()
        assert background.warm_services(now=1400.0) is True  # after the interval
        await _drain()

    asyncio.run(run())
    from super_agent.registry import AGENTS

    assert len(calls.seen) == 2 * len(AGENTS)
    first_round = calls.seen[: len(AGENTS)]
    dispatch = [c for c in first_round if c[1].endswith("/dispatch")]
    assert dispatch == [("POST", background.dispatch_url())]
    assert all(m == "GET" and u.endswith("/.well-known/agent-card.json")
               for m, u in first_round if not u.endswith("/dispatch"))


def test_warmup_disabled(calls, monkeypatch):
    monkeypatch.setattr(background, "settings", SimpleNamespace(
        server=SimpleNamespace(warmup_enabled=False, warmup_interval_s=300)))
    assert background.warm_services(now=1.0) is False


def test_dispatch_requests_coalesce(calls):
    async def run():
        background.request_dispatch()
        await asyncio.sleep(0.01)  # first call is in flight (held by the gate)
        background.request_dispatch()
        background.request_dispatch()
        calls.gate.set()
        await _drain()

    asyncio.run(run())
    assert calls.seen == [("POST", background.dispatch_url())] * 2


def test_dispatch_failure_is_swallowed(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(background, "transport", httpx.MockTransport(handler))
    background._reset_for_tests()

    async def run():
        background.request_dispatch()
        await _drain()

    asyncio.run(run())
    assert background._dispatch_running is False


@pytest.mark.pg
def test_turn_with_queued_notification_requests_one_dispatch(monkeypatch):
    """A tool result reporting a queued email triggers POST /dispatch during the turn."""
    from fastapi.testclient import TestClient
    from google.adk.sessions import InMemorySessionService

    from sales_common import db, migrate

    db.close_pool()
    migrate.run(seed=False)
    import runtime
    from fakes import build_fake_agents, router
    from super_agent.agent import build_gateway_app

    runtime.init_runtime(
        app=build_gateway_app(agents=build_fake_agents(), router_model=router("service_fulfillment_agent")),
        session_service=InMemorySessionService(),
        memory_service=None,
    )
    runtime.get_runner().memory_service = None
    import main
    from api import chat

    requested = []
    monkeypatch.setattr(chat, "request_dispatch", lambda: requested.append(1))
    asked = []

    async def statuses(session_id, ids):
        asked.append(list(ids))
        return {"NTF-FAKE-1": "sent"}

    monkeypatch.setattr(chat, "notification_statuses", statuses)
    try:
        with TestClient(main.app) as client:
            s = client.post("/api/session").json()
            r = client.post("/api/chat", json={"message": "Book my installation for October 2"},
                            headers={"Authorization": f"Bearer {s['token']}"})
    finally:
        runtime._runner = None
        db.close_pool()
    events = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    assert requested == [1]
    progress = [e for e in events if e["type"] == "progress"]
    assert progress[0] == {"type": "progress", "stage": "routing"}
    assert {"type": "progress", "stage": "agent", "agent": "service_fulfillment_agent"} in progress
    assert events[-1] == {"type": "done"}
    assert asked == [["NTF-FAKE-1"]]
    assert events[-2] == {"type": "activity_update", "category": "notification", "tool": "notification_status",
                          "data": {"notification_id": "NTF-FAKE-1", "status": "sent", "status_update": True}}
    queued = [e for e in events if e["type"] == "activity_update" and e["category"] == "notification"]
    assert queued[0]["data"] == {"notification_id": "NTF-FAKE-1", "triggered_by": "schedule_installation", "status": "queued"}
    assert queued[0]["tool"] == "send_installation_scheduled"


def test_notification_statuses_waits_for_the_dispatch_in_flight(monkeypatch):
    background._reset_for_tests()
    order = []

    def read(ids):
        order.append(("read", list(ids)))
        return {"N1": "sent"}

    monkeypatch.setattr(background, "_read_statuses", read)

    async def run():
        background._dispatch_running = True
        background._idle_event().clear()

        async def finish():
            await asyncio.sleep(0.05)
            order.append(("dispatched",))
            background._dispatch_running = False
            background._idle_event().set()

        asyncio.get_running_loop().create_task(finish())
        return await background.notification_statuses("s1", ["N1"], wait_s=2)

    assert asyncio.run(run()) == {"N1": "sent"}
    assert order == [("dispatched",), ("read", ["N1"])]
    background._reset_for_tests()


def test_notification_statuses_without_ids_reads_nothing(monkeypatch):
    background._reset_for_tests()
    monkeypatch.setattr(background, "_read_statuses", lambda ids: pytest.fail("no read expected"))
    assert asyncio.run(background.notification_statuses("s1", [], wait_s=0)) == {}


@pytest.mark.pg
def test_notification_statuses_carries_pending_rows_to_the_next_turn():
    from sales_common import db, migrate, notifications

    db.close_pool()
    migrate.run(seed=False)
    background._reset_for_tests()
    try:
        sent = notifications.enqueue("order_confirmation", recipient_email="a@example.com", args={"order_id": "O1"})
        pending = notifications.enqueue("payment_confirmation", recipient_email="a@example.com", args={"order_id": "O1"})
        db.execute("UPDATE notifications SET status = 'sent' WHERE notification_id = %s", (sent,))

        first = asyncio.run(background.notification_statuses("s1", [sent, pending], wait_s=0))
        assert first == {sent: "sent"}
        assert background._unresolved == {"s1": [pending]}

        db.execute("UPDATE notifications SET status = 'sent' WHERE notification_id = %s", (pending,))
        second = asyncio.run(background.notification_statuses("s1", [], wait_s=0))
        assert second == {pending: "sent"}
        assert background._unresolved == {}
    finally:
        background._reset_for_tests()
        db.close_pool()
