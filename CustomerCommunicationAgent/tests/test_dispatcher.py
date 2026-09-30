"""Outbox dispatcher tests (PostgreSQL; SMTP never contacted)."""

import asyncio
import json

import psycopg
import pytest

from sales_common import notifications
from sales_common.notifications import NOTIFICATION_TYPES

from customer_communication_agent import dispatcher
from customer_communication_agent.templates import TEMPLATE_ARGS, TEMPLATES, render


# ---------------------------------------------------------------------------
# Pure rendering (no database)
# ---------------------------------------------------------------------------

def test_every_outbox_type_has_a_template():
    missing = NOTIFICATION_TYPES - set(TEMPLATES)
    assert not missing, missing
    assert set(TEMPLATE_ARGS) == set(TEMPLATES)


@pytest.mark.parametrize("ntype", sorted(NOTIFICATION_TYPES))
def test_templates_render_with_and_without_args(ntype):
    subject, message = render(ntype, {})
    assert subject and message
    args = {key: f"v-{key}" for key in TEMPLATE_ARGS[ntype]}
    args.update(total_amount=10, amount=10, monthly_total=10, total_discount=1,
                equipment_installed=["Router", "Switch"])
    subject, message = render(ntype, args)
    assert "Dear v-customer_name" in message


def test_unknown_template_uses_generic():
    subject, message = render("something_new", {"subject": "Hello", "message": "Body text",
                                                "company_name": "Acme"})
    assert subject == "Hello"
    assert "Dear Acme" in message and "Body text" in message


def test_payment_failed_variant_and_company_name_fallback():
    subject, message = render("payment_confirmation",
                              {"order_id": "ORD-9", "payment_status": "failed", "company_name": "Acme"})
    assert subject == "Payment Failed - Order ORD-9"
    assert "Dear Acme" in message


def test_payment_contract_from_payment_service():
    base = {"order_id": "ORD-P", "customer_name": "Acme", "amount": 99.5, "currency": "USD",
            "payment_method": "Visa ****4242", "transaction_id": "TXN-1"}
    subject, message = render("payment_confirmation", {**base, "payment_status": "failed",
                                                       "failure_reason": "Card declined"})
    assert subject == "Payment Failed - Order ORD-P"
    assert "Reason: Card declined" in message and "$99.50" in message
    subject, message = render("payment_confirmation", {**base, "payment_status": "success"})
    assert subject == "Payment Processed - Order ORD-P"
    assert "Transaction ID: TXN-1" in message and "Visa ****4242" in message


# ---------------------------------------------------------------------------
# Dispatcher against PostgreSQL
# ---------------------------------------------------------------------------

def _row(db, nid):
    return db.fetch_one("SELECT * FROM notifications WHERE notification_id=%s", (nid,))


@pytest.mark.pg
def test_enqueue_then_dispatch_is_simulated(clean_db):
    nid = notifications.enqueue(
        "order_confirmation", recipient_email="buyer@example.com", order_id="ORD-T1",
        customer_id="CUST-1",
        args={"order_id": "ORD-T1", "customer_name": "Acme Pizza", "service_type": "Fiber 1G",
              "total_amount": 1234.5},
    )
    counts = dispatcher.dispatch_pending()
    assert counts["processed"] == 1 and counts["simulated"] == 1
    row = _row(clean_db, nid)
    assert row["status"] == "simulated"
    assert row["attempts"] == 1
    assert row["sent_at"] and row["updated_at"]
    assert row["error"] is None
    assert row["subject"] == "Order Confirmation - ORD-T1"
    assert "Dear Acme Pizza" in row["message"] and "$1234.50" in row["message"]
    assert json.loads(row["channels_json"]) == ["email"]
    # Nothing left to do.
    assert dispatcher.dispatch_pending()["processed"] == 0


@pytest.mark.pg
def test_producer_args_from_maintenance_render(clean_db):
    nid = notifications.enqueue("abandoned_cart", recipient_email="c@example.com",
                                args={"cart_id": "CART-1", "company_name": "Acme"})
    dispatcher.dispatch_pending()
    row = _row(clean_db, nid)
    assert row["status"] == "simulated"
    assert "Cart ID: CART-1" in row["message"] and "Dear Acme" in row["message"]


@pytest.mark.pg
def test_dedup_prevents_double_send(clean_db):
    args = {"order_id": "ORD-D1", "customer_name": "Acme"}
    first = notifications.enqueue("order_confirmation", recipient_email="d@example.com",
                                  order_id="ORD-D1", args=args)
    second = notifications.enqueue("order_confirmation", recipient_email="D@example.com",
                                   order_id="ORD-D1", args=args)
    other = notifications.enqueue("order_confirmation", recipient_email="d@example.com",
                                  order_id="ORD-D2", args={"order_id": "ORD-D2"})
    counts = dispatcher.dispatch_pending()
    assert counts == {"processed": 3, "sent": 0, "simulated": 2, "deduped": 1,
                      "retrying": 0, "failed": 0}
    # created_at has second precision, so either duplicate may be processed first.
    pair = sorted([_row(clean_db, first), _row(clean_db, second)], key=lambda r: r["status"])
    assert [r["status"] for r in pair] == ["deduped", "simulated"]
    assert pair[0]["sent_at"] is None
    assert _row(clean_db, other)["status"] == "simulated"

    # A later identical request inside the window is also deduplicated.
    third = notifications.enqueue("order_confirmation", recipient_email="d@example.com",
                                  order_id="ORD-D1", args=args)
    dispatcher.dispatch_pending()
    assert _row(clean_db, third)["status"] == "deduped"


@pytest.mark.pg
def test_smtp_failure_retries_then_fails(clean_db, monkeypatch):
    calls = []

    def fake_send(settings, to_address, subject, body):
        calls.append(to_address)
        return {"sent": False, "detail": "SMTP error: SMTPServerDisconnected: boom"}

    monkeypatch.setattr(dispatcher, "send_email", fake_send)
    monkeypatch.setenv("SMTP_ENABLED", "true")
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "not-a-real-password")

    nid = notifications.enqueue("service_activated", recipient_email="f@example.com",
                                order_id="ORD-F1", args={"order_id": "ORD-F1"})
    assert dispatcher.dispatch_pending()["retrying"] == 1
    row = _row(clean_db, nid)
    assert (row["status"], row["attempts"]) == ("pending", 1)
    assert "boom" in row["error"]

    assert dispatcher.dispatch_pending()["retrying"] == 1
    counts = dispatcher.dispatch_pending()
    assert counts["failed"] == 1
    row = _row(clean_db, nid)
    assert (row["status"], row["attempts"]) == ("failed", dispatcher.MAX_ATTEMPTS)
    assert row["sent_at"] is None
    assert calls == ["f@example.com"] * 3
    assert dispatcher.dispatch_pending()["processed"] == 0  # failed rows are not retried
    # A failed send does not poison the dedup cache.
    assert clean_db.fetch_one("SELECT count(*) AS n FROM dedup_cache")["n"] == 0


@pytest.mark.pg
def test_smtp_success_marks_sent(clean_db, monkeypatch):
    monkeypatch.setattr(dispatcher, "send_email",
                        lambda settings, to, subject, body: {"sent": True, "detail": "delivered"})
    monkeypatch.setenv("SMTP_ENABLED", "true")
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "not-a-real-password")
    nid = notifications.enqueue("quote_confirmation", recipient_email="q@example.com",
                                args={"quote_id": "Q-1", "customer_name": "Acme"})
    assert dispatcher.dispatch_pending()["sent"] == 1
    assert _row(clean_db, nid)["status"] == "sent"


@pytest.mark.pg
def test_smtp_enabled_without_credentials_is_a_delivery_error(clean_db, monkeypatch):
    monkeypatch.setenv("SMTP_ENABLED", "true")
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    nid = notifications.enqueue("order_cancelled", recipient_email="x@example.com",
                                args={"order_id": "ORD-X"})
    dispatcher.dispatch_pending()
    row = _row(clean_db, nid)
    assert row["status"] == "pending" and "SMTP_USER" in row["error"]


@pytest.mark.pg
def test_locked_rows_are_skipped(clean_db):
    from sales_common.db import database_url

    nid = notifications.enqueue("escalation", recipient_email="l@example.com",
                                args={"order_id": "ORD-L"})
    with psycopg.connect(database_url()) as other:
        other.execute("SELECT 1 FROM notifications WHERE notification_id=%s FOR UPDATE", (nid,))
        assert dispatcher.dispatch_pending()["processed"] == 0
    assert dispatcher.dispatch_pending()["simulated"] == 1


@pytest.mark.pg
def test_unknown_template_row_renders_generic(clean_db):
    clean_db.execute(
        "INSERT INTO notifications (notification_id, notification_type, recipient_email, "
        "metadata_json, status, channels_json, created_at, updated_at) "
        "VALUES ('NTF-GENERIC1', 'custom_type', 'g@example.com', %s, 'pending', '[\"email\"]', %s, %s)",
        (json.dumps({"template": "custom_type", "args": {"subject": "Hi", "message": "Custom"}}),
         "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
    )
    dispatcher.dispatch_pending()
    row = _row(clean_db, "NTF-GENERIC1")
    assert row["status"] == "simulated" and row["subject"] == "Hi"


@pytest.mark.pg
async def test_background_loop_delivers_and_stops(clean_db, monkeypatch):
    monkeypatch.setenv("NOTIFY_POLL_SECONDS", "0.05")
    async with dispatcher.dispatcher_lifespan(None):
        nid = notifications.enqueue("installation_reminder", recipient_email="b@example.com",
                                    args={"order_id": "ORD-B"})
        for _ in range(100):
            if _row(clean_db, nid)["status"] != "pending":
                break
            await asyncio.sleep(0.05)
    assert _row(clean_db, nid)["status"] == "simulated"
    assert not [t for t in asyncio.all_tasks() if t.get_name() == "notification-dispatcher"]
