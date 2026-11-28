"""POST /dispatch: on-demand outbox delivery (Cloud Run scales the service to zero)."""

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from sales_common import notifications

from customer_communication_agent import dispatcher, rest


@pytest.fixture
def client():
    return TestClient(Starlette(routes=rest.ROUTES))


def test_dispatch_returns_counts(client, monkeypatch):
    monkeypatch.setattr(dispatcher, "dispatch_pending", lambda: {"processed": 1, "sent": 1, "simulated": 0,
                                                                 "deduped": 0, "retrying": 0, "failed": 0})
    r = client.post("/dispatch")
    assert r.status_code == 200
    assert r.json() == {"success": True, "processed": 1, "sent": 1, "simulated": 0, "deduped": 0,
                        "retrying": 0, "failed": 0}


def test_dispatch_failure_is_503(client, monkeypatch):
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(dispatcher, "dispatch_pending", boom)
    r = client.post("/dispatch")
    assert r.status_code == 503 and r.json()["success"] is False


def test_get_is_not_allowed(client):
    assert client.get("/dispatch").status_code == 405


@pytest.mark.pg
def test_dispatch_delivers_pending_rows(clean_db, client):
    ids = [
        notifications.enqueue("quote_confirmation", recipient_email="a@example.com",
                              args={"offer_id": "OFF-1", "company_name": "Acme"}),
        notifications.enqueue("order_confirmation", recipient_email="b@example.com", order_id="ORD-1",
                              args={"order_id": "ORD-1", "customer_name": "Acme"}),
    ]
    r = client.post("/dispatch")
    assert r.status_code == 200
    assert r.json()["processed"] == 2
    statuses = {clean_db.fetch_one("SELECT status FROM notifications WHERE notification_id=%s", (i,))["status"]
                for i in ids}
    assert "pending" not in statuses
