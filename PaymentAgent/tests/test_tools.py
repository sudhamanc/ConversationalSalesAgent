"""Tool tests. DB-backed tests run against TEST_DATABASE_URL (skipped when unset)."""

import json
import os

import pytest

from payment_agent.tools.billing_tools import generate_invoice, setup_payment_plan
from payment_agent.tools.credit_tools import check_business_credit
from payment_agent.tools.payment_tools import (
    add_payment_method,
    get_payment_methods,
    process_payment,
    tokenize_payment_method,
    validate_payment_method,
)

requires_db = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")


# --------------------------------------------------------------------------- pure tools

def test_validate_credit_card():
    result = validate_payment_method(payment_type="credit_card", card_number="4532015112830366")
    assert result["valid"] is True
    assert result["card_brand"] == "visa"
    assert result["last_four"] == "0366"


def test_validate_invalid_card():
    assert validate_payment_method(payment_type="credit_card", card_number="1234567890123456")["valid"] is False


def test_validate_ach():
    result = validate_payment_method(payment_type="ach", routing_number="021000021", account_number="123456789")
    assert result["valid"] is True


def test_tokenize_card_and_ach():
    card = tokenize_payment_method("credit_card", card_number="4111 1111 1111 1111",
                                   expiry_month=12, expiry_year=2028, cvv="123")
    assert card["success"] is True and card["saved"] is False  # no customer known -> not persisted
    assert card["token"].startswith("tok_")
    assert (card["card_brand"], card["last_four"], card["expiry"]) == ("visa", "1111", "12/2028")
    ach = tokenize_payment_method("ach", routing_number="021000021", account_number="123456789",
                                  account_type="checking")
    assert ach["success"] is True and ach["token"].startswith("tok_")
    assert ach["account_last_four"] == "6789"
    assert tokenize_payment_method("credit_card", card_number="4111111111111111")["success"] is False
    assert tokenize_payment_method("credit_card", card_number="4111111111111111", expiry_month=13,
                                   expiry_year=2028, cvv="123")["success"] is False


def test_tokens_are_opaque_and_random():
    """Regression: the token used to be tok_{brand}_{last4}, derived from the card."""
    number = "4532015112830366"
    tokens = {
        tokenize_payment_method("credit_card", card_number=number, expiry_month=1, expiry_year=2030,
                                cvv="999")["token"]
        for _ in range(5)
    }
    assert len(tokens) == 5
    for token in tokens:
        assert token.startswith("tok_") and len(token) >= 24
        assert number not in token and number[:6] not in token
        assert token != "tok_visa_0366"


def test_process_payment_input_validation_needs_no_db():
    assert process_payment(amount=0, payment_method_token="tok")["success"] is False
    assert process_payment(amount=200_000, payment_method_token="tok")["success"] is False
    assert process_payment(amount=10, payment_method_token="tok", currency="XYZ")["success"] is False
    assert process_payment(amount=10, payment_method_token="")["success"] is False
    missing_order = process_payment(amount=10, payment_method_token="tok_visa_1111")
    assert missing_order["success"] is False and "order_id" in missing_order["error"]


def test_credit_and_billing_tools():
    credit = check_business_credit(business_name="ABC Corporation", ein="12-3456789",
                                   years_in_business=10, state="DE")
    assert credit["success"] is True
    assert credit["decision"] in {"approved", "conditional", "declined"}
    assert check_business_credit(business_name="X", ein="invalid", years_in_business=5,
                                 state="CA")["success"] is False
    invoice = generate_invoice(customer_name="ABC Corporation",
                               line_items_json='[{"description": "Internet", "quantity": 1, "unit_price": 500.0}]')
    assert invoice["success"] is True and invoice["total"] == pytest.approx(540.0)
    plan = setup_payment_plan(total_amount=1200.00, num_installments=12)
    assert plan["success"] is True and plan["installment_amount"] == 100.00


def test_payment_plan_never_starts_in_the_past():
    from datetime import date

    past = setup_payment_plan(total_amount=1200.0, num_installments=4, start_date="2025-05-20")
    assert past["success"] is False and "in the past" in past["error"]
    plan = setup_payment_plan(total_amount=1200.0, num_installments=4)
    first_due = date.fromisoformat(plan["installments"][0]["due_date"][:10])
    assert first_due > date.today()


@requires_db
def test_payment_history_reads_payments_table(migrated_db):
    from payment_agent.tools.billing_tools import get_payment_history

    # Seed: CUST-20260427-152 has exactly one payment (ORD-20260427-518, 495.97, completed).
    history = get_payment_history("CUST-20260427-152")
    assert history["success"] is True and history["count"] == 1
    (txn,) = history["transactions"]
    assert txn["order_id"] == "ORD-20260427-518" and txn["amount"] == 495.97
    assert txn["status"] == "completed" and history["total_amount"] == 495.97
    assert txn["payment_method"] == "ACH bank transfer (token ending 7890)"
    # Seed payment PAY-20260426213336-4854 has no customer_id; it belongs via its order.
    via_order = get_payment_history("CUST-20260427-151")
    assert [t["order_id"] for t in via_order["transactions"]] == ["ORD-20260426-370"]
    assert get_payment_history("CUST-NOPE")["count"] == 0
    assert get_payment_history("CUST-20260427-152", start_date="2030-01-01")["count"] == 0


def test_describe_method_never_exposes_token():
    from payment_agent.tools.billing_tools import _describe_method

    assert _describe_method("tok_SECRETabcd", "credit_card", "visa", "1111") == "Visa card ending 1111"
    assert _describe_method("tok_SECRETabcd", "ach", None, "6789") == "ACH bank transfer ending 6789"
    assert "SECRET" not in _describe_method("tok_SECRETabcd")


# --------------------------------------------------------------------------- PostgreSQL

@requires_db
def test_process_payment_persists_everything(make_order):
    from sales_common import db

    order = make_order(total=249.0)
    result = process_payment(
        amount=249.0,
        payment_method_token="tok_visa_1111",
        order_id=order["order_id"],
        customer_name="Test Corp",
        customer_email="buyer@example.com",
        description="Payment for Fiber",
    )
    assert result["success"] is True
    assert result["status"] == "completed"
    assert result["transaction_id"].startswith("TXN-")
    assert result["order_status"] == "paid"
    assert result["email_confirmation_queued"] is True

    pay = db.fetch_one("SELECT * FROM payments WHERE payment_id=%s", (result["payment_id"],))
    assert pay["status"] == "completed"
    assert pay["order_id"] == order["order_id"]
    assert pay["customer_id"] == order["customer_id"]
    assert pay["transaction_id"] == result["transaction_id"]
    assert pay["expires_at"]

    events = db.fetch_all(
        "SELECT from_status, to_status FROM payment_events WHERE payment_id=%s ORDER BY created_at, to_status",
        (result["payment_id"],),
    )
    assert {(e["from_status"], e["to_status"]) for e in events} == {
        (None, "initiated"), ("initiated", "processing"), ("processing", "completed"),
    }
    assert db.fetch_one("SELECT status FROM orders WHERE order_id=%s", (order["order_id"],))["status"] == "paid"
    rl = db.fetch_one("SELECT SUM(attempt_count) AS n FROM payment_rate_limit WHERE customer_id=%s",
                      (order["customer_id"],))
    assert rl["n"] == 1

    notif = db.fetch_one(
        "SELECT * FROM notifications WHERE order_id=%s AND notification_type='payment_confirmation'",
        (order["order_id"],),
    )
    assert notif["status"] == "pending"
    assert notif["recipient_email"] == "buyer@example.com"
    meta = json.loads(notif["metadata_json"])
    assert meta["template"] == "payment_confirmation"
    assert meta["args"]["transaction_id"] == result["transaction_id"]
    assert meta["args"]["payment_status"] == "success"
    assert meta["args"]["amount"] == 249.0


@requires_db
def test_process_payment_idempotency_and_duplicate_guard(make_order):
    from sales_common import db

    order = make_order()
    first = process_payment(amount=249.0, payment_method_token="tok_visa_1111", customer_email="a@example.com",
                            order_id=order["order_id"], idempotency_key="idem-" + order["order_id"])
    replay = process_payment(amount=249.0, payment_method_token="tok_visa_1111", customer_email="a@example.com",
                             order_id=order["order_id"], idempotency_key="idem-" + order["order_id"])
    assert replay["idempotent"] is True
    assert replay["payment_id"] == first["payment_id"]
    assert replay["transaction_id"] == first["transaction_id"]

    duplicate = process_payment(amount=249.0, payment_method_token="tok_visa_1111", customer_email="a@example.com",
                                order_id=order["order_id"])
    assert duplicate["success"] is True and duplicate["idempotent"] is True
    assert duplicate["payment_id"] == first["payment_id"]

    count = db.fetch_one("SELECT COUNT(*) AS n FROM payments WHERE order_id=%s", (order["order_id"],))
    assert count["n"] == 1
    notifs = db.fetch_one("SELECT COUNT(*) AS n FROM notifications WHERE order_id=%s", (order["order_id"],))
    assert notifs["n"] == 1


@requires_db
def test_process_payment_unknown_order(migrated_db):
    result = process_payment(amount=10.0, payment_method_token="tok_visa_1111", order_id="ORD-DOES-NOT-EXIST")
    assert result == {"success": False, "error": "Order ORD-DOES-NOT-EXIST not found"}


@requires_db
def test_process_payment_rate_limit(make_order):
    from sales_common import db
    from payment_agent.tools import payment_tools

    order = make_order()
    db.execute(
        "INSERT INTO payment_rate_limit (customer_id, window_start, attempt_count) VALUES (%s, %s, %s)",
        (order["customer_id"], payment_tools._rate_limit_window(), payment_tools._MAX_ATTEMPTS_PER_HOUR),
    )
    result = process_payment(amount=10.0, payment_method_token="tok_visa_1111", order_id=order["order_id"])
    assert result["success"] is False and "Too many payment attempts" in result["error"]
    assert db.fetch_one("SELECT COUNT(*) AS n FROM payments WHERE order_id=%s", (order["order_id"],))["n"] == 0


def test_mock_credit_score_is_stable_across_processes():
    """Regression: the score used salted ``hash()`` and changed per process/replica."""
    import subprocess
    import sys

    code = (
        "from payment_agent.tools.credit_tools import _calculate_mock_credit_score as f;"
        "print(f(3, 'Crane.io'))"
    )
    runs = {
        subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                       env={**os.environ, "PYTHONHASHSEED": seed}).stdout.strip()
        for seed in ("1", "2", "3")
    }
    assert len(runs) == 1


def test_invoice_and_plan_ids_unique():
    a = generate_invoice(customer_name="Same Co", line_items_json=json.dumps([{"description": "x", "amount": 10.0}]))
    b = generate_invoice(customer_name="Same Co", line_items_json=json.dumps([{"description": "x", "amount": 10.0}]))
    ia, ib = json.loads(a) if isinstance(a, str) else a, json.loads(b) if isinstance(b, str) else b
    assert ia["invoice_id"] != ib["invoice_id"]


# --------------------------------------------------------------------------- saved methods

@requires_db
def test_tokenize_persists_masked_method_and_lists_it(migrated_db):
    import uuid
    from types import SimpleNamespace

    from sales_common import db

    cid = f"CUST-PM-{uuid.uuid4().hex[:8]}"
    number = "4532015112830366"
    ctx = SimpleNamespace(state={"customer_context": {"customer_id": cid}})
    tok = tokenize_payment_method("credit_card", card_number=number, expiry_month=7, expiry_year=29,
                                  cvv="321", tool_context=ctx)
    assert tok["success"] and tok["saved"] is True and tok["customer_id"] == cid

    row = db.fetch_one("SELECT * FROM customer_payment_methods WHERE token=%s", (tok["token"],))
    assert row["customer_id"] == cid and row["status"] == "active"
    assert (row["payment_type"], row["card_brand"], row["last_four"], row["token_expiry"]) == (
        "credit_card", "visa", "0366", "07/2029")
    assert number not in " ".join(str(v) for v in row.values())

    # order_context fallback + ACH
    ctx2 = SimpleNamespace(state={"order_context": {"customer_id": cid}})
    ach = tokenize_payment_method("ach", routing_number="021000021", account_number="987654321",
                                  account_type="savings", tool_context=ctx2)
    assert ach["saved"] is True

    added = add_payment_method(cid, "credit_card", tok["token"], is_default=True, nickname="Ops Visa")
    assert added["success"] is True
    assert added["payment_method"]["method_id"] == tok["method_id"]  # same row, updated
    assert added["payment_method"]["is_default"] is True

    listed = get_payment_methods(cid)
    assert listed["success"] is True and listed["count"] == 2
    first = listed["payment_methods"][0]
    assert first["token"] == tok["token"] and first["nickname"] == "Ops Visa" and first["last_four"] == "0366"
    assert {m["payment_type"] for m in listed["payment_methods"]} == {"credit_card", "ach"}
    assert {m["type"] for m in listed["supported_methods"]} == {"credit_card", "ach"}
    assert number not in str(listed) and "987654321" not in str(listed)

    assert get_payment_methods(f"CUST-NONE-{uuid.uuid4().hex[:6]}")["count"] == 0


@requires_db
def test_add_payment_method_persists_legacy_and_rejects_bad_input(migrated_db):
    import uuid

    cid = f"CUST-PM-{uuid.uuid4().hex[:8]}"
    legacy = f"tok_visa_{uuid.uuid4().int % 10000:04d}"
    added = add_payment_method(cid, "credit_card", legacy)
    assert added["success"] is True
    assert added["payment_method"]["last_four"] == legacy[-4:]
    assert added["payment_method"]["card_brand"] == "visa"
    assert get_payment_methods(cid)["payment_methods"][0]["token"] == legacy
    # a token already saved for another customer is not re-assigned
    assert add_payment_method("CUST-OTHER", "credit_card", legacy)["success"] is False
    assert add_payment_method(cid, "wire", "tok_x")["success"] is False
    assert add_payment_method(cid, "credit_card", "4111111111111111")["success"] is False


@requires_db
def test_process_payment_accepts_new_opaque_token(make_order):
    order = make_order()
    tok = tokenize_payment_method("credit_card", card_number="4111111111111111", expiry_month=12,
                                  expiry_year=2030, cvv="123", customer_id=order["customer_id"])
    result = process_payment(amount=249.0, payment_method_token=tok["token"], order_id=order["order_id"])
    assert result["success"] is True and result["payment_method_token"] == tok["token"]


# --------------------------------------------------------------------------- order status guard

def _set_status(order_id: str, status: str) -> None:
    from sales_common import db

    db.execute("UPDATE orders SET status=%s WHERE order_id=%s", (status, order_id))


def _assert_refused(order: dict, status: str) -> None:
    from sales_common import db

    result = process_payment(amount=249.0, payment_method_token="tok_visa_1111",
                             customer_email="a@example.com", order_id=order["order_id"])
    assert result["success"] is False
    assert result["error"] == f"Order {order['order_id']} cannot be paid in status {status}"
    assert "transaction_id" not in result
    oid = order["order_id"]
    assert db.fetch_one("SELECT COUNT(*) AS n FROM payments WHERE order_id=%s", (oid,))["n"] == 0
    assert db.fetch_one("SELECT COUNT(*) AS n FROM notifications WHERE order_id=%s", (oid,))["n"] == 0
    assert db.fetch_one("SELECT status FROM orders WHERE order_id=%s", (oid,))["status"] == status
    rl = db.fetch_one("SELECT COUNT(*) AS n FROM payment_rate_limit WHERE customer_id=%s",
                      (order["customer_id"],))
    assert rl["n"] == 0


@requires_db
def test_process_payment_refuses_cancelled_order(make_order):
    order = make_order()
    _set_status(order["order_id"], "cancelled")
    _assert_refused(order, "cancelled")


@requires_db
def test_process_payment_refuses_paid_order(make_order):
    order = make_order()
    _set_status(order["order_id"], "paid")  # paid without a completed payment row here
    _assert_refused(order, "paid")


@requires_db
def test_process_payment_allows_draft_and_keeps_idempotent_replay(make_order):
    order = make_order()
    _set_status(order["order_id"], "draft")
    key = "idem-draft-" + order["order_id"]
    first = process_payment(amount=249.0, payment_method_token="tok_visa_1111", order_id=order["order_id"],
                            idempotency_key=key)
    assert first["success"] is True
    # The order is now 'paid'; replaying the same key still returns the original result.
    replay = process_payment(amount=249.0, payment_method_token="tok_visa_1111", order_id=order["order_id"],
                             idempotency_key=key)
    assert replay["success"] is True and replay["idempotent"] is True
    assert replay["transaction_id"] == first["transaction_id"]
