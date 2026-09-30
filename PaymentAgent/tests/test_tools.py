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
    assert card == {
        "success": True, "token": "tok_visa_1111", "payment_type": "credit_card", "card_brand": "visa",
        "last_four": "1111", "expiry": "12/2028", "message": "Payment method tokenized successfully",
    }
    ach = tokenize_payment_method("ach", routing_number="021000021", account_number="123456789",
                                  account_type="checking")
    assert ach["success"] is True and ach["token"] == "tok_ach_6789"
    assert tokenize_payment_method("credit_card", card_number="4111111111111111")["success"] is False


def test_get_and_add_payment_methods_simulated():
    methods = get_payment_methods("CUST-1")
    assert methods["success"] is True and methods["count"] == 2
    added = json.loads(add_payment_method("CUST-1", "credit_card", "tok_visa_1111", is_default=True))
    assert added["success"] is True
    assert added["payment_method"]["last_four"] == "1111"
    assert json.loads(add_payment_method("CUST-1", "wire", "tok_x"))["success"] is False


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
