"""Agent-facing tool tests (enqueue + immediate dispatch; PostgreSQL)."""

import pytest

from customer_communication_agent import dispatcher
from customer_communication_agent.tools import (
    get_notification_history,
    send_abandoned_cart_reminder,
    send_order_confirmation,
    send_payment_notification,
    send_quote_confirmation,
)

pytestmark = pytest.mark.pg


def test_send_order_confirmation_reports_real_status(clean_db):
    result = send_order_confirmation(
        order_id="ORD-100", customer_name="Acme", customer_email="ops@acme.example",
        customer_phone="215-555-1234", service_type="Fiber", total_amount=99.0,
    )
    assert result["success"] is True
    assert result["status"] == "simulated"
    assert result["channels"] == ["email", "sms"]
    assert result["email_delivery"] == "simulated"
    assert result["notification_id"].startswith("NTF-")
    row = clean_db.fetch_one("SELECT * FROM notifications WHERE notification_id=%s",
                             (result["notification_id"],))
    assert row["order_id"] == "ORD-100" and row["status"] == "simulated"

    again = send_order_confirmation(order_id="ORD-100", customer_name="Acme",
                                    customer_email="ops@acme.example")
    assert again["success"] is True and again["status"] == "deduped"


def test_missing_contact_info(clean_db):
    result = send_quote_confirmation(quote_id="Q-1", customer_name="Acme")
    assert result["success"] is False
    assert "contact" in result["error"].lower()
    assert clean_db.fetch_one("SELECT count(*) AS n FROM notifications")["n"] == 0


def test_abandoned_cart_is_email_only(clean_db):
    result = send_abandoned_cart_reminder(cart_id="CART-1", customer_name="Acme",
                                          customer_email="c@acme.example",
                                          customer_phone="215-555-0000")
    assert result["success"] is True and result["channels"] == ["email"]
    assert send_abandoned_cart_reminder(cart_id="CART-2", customer_name="Acme",
                                        customer_phone="215-555-0000")["success"] is False


def test_tool_reports_failure_with_retry(clean_db, monkeypatch):
    monkeypatch.setattr(dispatcher, "send_email",
                        lambda settings, to, subject, body: {"sent": False, "detail": "SMTP error: down"})
    monkeypatch.setenv("SMTP_ENABLED", "true")
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "not-a-real-password")
    result = send_payment_notification(order_id="ORD-7", customer_name="Acme",
                                       customer_email="p@acme.example", amount=10)
    assert result["success"] is False
    assert result["status"] == "pending" and result["attempts"] == 1
    assert "down" in result["error"]


def test_get_notification_history_returns_rows(clean_db):
    send_order_confirmation(order_id="ORD-H1", customer_name="Acme", customer_email="h@acme.example")
    send_payment_notification(order_id="ORD-H1", customer_name="Acme",
                              customer_email="h@acme.example", payment_status="success")
    send_order_confirmation(order_id="ORD-H9", customer_name="Other", customer_email="z@other.example")

    history = get_notification_history(customer_email="H@acme.example")
    assert history["success"] is True and history["count"] == 2
    types = {n["notification_type"] for n in history["notifications"]}
    assert types == {"order_confirmation", "payment_confirmation"}
    first = history["notifications"][0]
    assert first["status"] == "simulated" and first["subject"] and first["metadata"]["order_id"] == "ORD-H1"

    # Legacy type names are accepted as filters.
    legacy = get_notification_history(customer_email="h@acme.example", notification_type="payment_success")
    assert legacy["count"] == 1
    assert get_notification_history()["success"] is False
