"""PostgreSQL integration tests (set TEST_DATABASE_URL to an empty scratch database)."""

import asyncio
import json

import psycopg
import pytest
from google.adk.events import Event
from google.adk.sessions import Session
from google.genai import types

pytestmark = pytest.mark.pg


def test_migrations_idempotent(pg_url):
    from sales_common import migrate

    migrate.run(seed=False)
    second = migrate.run(seed=False)
    assert second["migrations"] == []


def test_notification_enqueue_in_transaction(pg_url):
    from sales_common import db, migrate, notifications

    migrate.run(seed=False)
    with db.transaction() as conn:
        nid = notifications.enqueue(
            "order_confirmation", recipient_email="buyer@example.com", order_id="ORD-T1",
            args={"order_id": "ORD-T1"}, conn=conn,
        )
    row = db.fetch_one("SELECT status, metadata_json FROM notifications WHERE notification_id=%s", (nid,))
    assert row["status"] == "pending"
    assert json.loads(row["metadata_json"])["template"] == "order_confirmation"
    assert notifications.enqueue("order_confirmation", recipient_email="not-an-email") is None


def test_notification_rolls_back_with_business_change(pg_url):
    from sales_common import db, migrate, notifications

    migrate.run(seed=False)
    with pytest.raises(RuntimeError):
        with db.transaction() as conn:
            nid = notifications.enqueue("order_confirmation", recipient_email="a@b.co", conn=conn)
            raise RuntimeError("business failure")
    assert db.fetch_one("SELECT 1 FROM notifications WHERE notification_id=%s", (nid,)) is None


def test_memory_add_search_isolation(pg_url):
    from sales_common import migrate
    from sales_common.memory import PostgresMemoryService

    migrate.run(seed=False)
    url = "postgresql+asyncpg://" + pg_url.split("://", 1)[1]

    async def scenario():
        svc = PostgresMemoryService(url)
        def ev(i, text):
            return Event(id=f"ev-{i}", author="user", invocation_id="i",
                         content=types.Content(role="user", parts=[types.Part(text=text)]))
        s1 = Session(id="s1", app_name="gw", user_id="web:u1", events=[ev(1, "We want SD-WAN security for 12 branches")])
        s2 = Session(id="s2", app_name="gw", user_id="web:u2", events=[ev(2, "Fiber internet for our warehouse")])
        await svc.add_session_to_memory(s1)
        await svc.add_session_to_memory(s1)  # idempotent
        await svc.add_session_to_memory(s2)
        r1 = await svc.search_memory(app_name="gw", user_id="web:u1", query="security product")
        r2 = await svc.search_memory(app_name="gw", user_id="web:u2", query="SD-WAN security")
        await svc.close()
        return r1, r2

    r1, r2 = asyncio.run(scenario())
    assert len(r1.memories) == 1 and "SD-WAN" in r1.memories[0].content.parts[0].text
    assert r2.memories == []
