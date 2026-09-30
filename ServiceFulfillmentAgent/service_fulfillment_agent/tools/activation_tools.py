"""Service activation tools: activation (lifecycle capstone), tests and service details.

``activate_service`` is the only point where a prospect becomes a customer. In
one PostgreSQL transaction it:

1. marks the order's ``fulfillments`` row ``activated`` (activation/circuit/account ids)
2. upserts ``customer_master``
3. sets ``accounts."Existing Customer" = 'Y'`` and merges ``accounts."Current Products"``
4. sets ``orders.status = 'fulfilled'``
5. enqueues a ``service_activated`` notification
"""

from __future__ import annotations

import json
import logging
from random import uniform
from typing import Any, List, Optional

import psycopg
from google.adk.tools.tool_context import ToolContext

from sales_common import db, notifications

from ._common import find_fulfillment, get_order, stable_number, state_dict, state_order_id, update_order_context

logger = logging.getLogger(__name__)


def activate_service(
    order_id: Optional[str] = None,
    service_type: Optional[str] = None,
    circuit_id: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Activates service for a completed installation and converts the prospect to a customer.

    order_id and service_type default to the journey order_context when not passed.

    Args:
        order_id: Order identifier
        service_type: Type of service to activate
        circuit_id: Circuit identifier (auto-generated if not provided)

    Returns:
        Service activation details
    """
    order_ctx = state_dict(tool_context, "order_context")
    order_id = (order_id or "").strip() or state_order_id(tool_context)
    service_type = service_type or order_ctx.get("service_type")
    if not order_id:
        return {"success": False, "error": "order_id is required to activate service"}

    now = db.now_iso()
    try:
        with db.transaction() as conn:
            order = get_order(conn, order_id)
            if order is None:
                return {"success": False, "error": f"Order {order_id} not found"}
            items = conn.execute(
                "SELECT service_type FROM order_items WHERE order_id = %s ORDER BY id", (order_id,)
            ).fetchall()
            products = [r["service_type"] for r in items]
            if not service_type:
                service_type = products[0] if products else "Business Internet"
            if not products:
                products = [service_type]

            fulfillment = find_fulfillment(conn, order_id=order_id, for_update=True)
            if fulfillment and fulfillment["status"] == "activated":
                # Idempotent: return the existing activation without re-notifying.
                activation_id = fulfillment["activation_id"]
                circuit_id = fulfillment["circuit_id"]
                account_id = fulfillment["account_id"]
                already_active = True
            else:
                already_active = False
                activation_id = f"ACT-{order_id.removeprefix('ORD-')}"
                circuit_id = circuit_id or f"CKT-{now[:7].replace('-', '')}-{stable_number(order_id, 100000):05d}"
                account_id = f"ACCT-{stable_number('acct:' + order_id, 1000000):06d}"
                if fulfillment:
                    conn.execute(
                        "UPDATE fulfillments SET activation_id = %s, circuit_id = %s, account_id = %s, "
                        "status = 'activated', updated_at = %s WHERE fulfillment_id = %s",
                        (activation_id, circuit_id, account_id, now, fulfillment["fulfillment_id"]),
                    )
                else:
                    # Activation without a booked appointment (e.g. simulated install day):
                    # record the fulfillment so the lifecycle stays queryable and idempotent.
                    conn.execute(
                        "INSERT INTO fulfillments (fulfillment_id, order_id, customer_id, activation_id, "
                        "circuit_id, account_id, status, created_at, updated_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, 'activated', %s, %s)",
                        (f"FUL-{activation_id}", order_id, order["customer_id"], activation_id,
                         circuit_id, account_id, now, now),
                    )

            customer_id = order["customer_id"]
            customer_master_created = False
            notification_id = None
            if not already_active:
                account = conn.execute(
                    'SELECT "Company Name", "Street", "City", "State", zip_code, "Current Products" '
                    "FROM accounts WHERE customer_id = %s LIMIT 1",
                    (customer_id,),
                ).fetchone()
                if account:
                    conn.execute(
                        "INSERT INTO customer_master (customer_id, company_name, street, city, state, "
                        "zip_code, contact_name, contact_email, contact_phone, first_order_id, circuit_id, "
                        "account_id, contracted_products, monthly_revenue, activated_at, created_at, "
                        "updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                        "ON CONFLICT (customer_id) DO UPDATE SET "
                        "contact_name = EXCLUDED.contact_name, contact_email = EXCLUDED.contact_email, "
                        "contact_phone = EXCLUDED.contact_phone, circuit_id = EXCLUDED.circuit_id, "
                        "account_id = EXCLUDED.account_id, contracted_products = EXCLUDED.contracted_products, "
                        "monthly_revenue = EXCLUDED.monthly_revenue, updated_at = EXCLUDED.updated_at",
                        (
                            customer_id,
                            account["Company Name"],
                            account["Street"] or "",
                            account["City"] or "",
                            account["State"] or "",
                            account["zip_code"],
                            order["customer_name"],
                            order["contact_email"],
                            order["contact_phone"],
                            order_id,
                            circuit_id,
                            account_id,
                            json.dumps(products),
                            order["total_amount"],
                            now,
                            now,
                            now,
                        ),
                    )
                    current = [p.strip() for p in (account["Current Products"] or "").split(",") if p.strip()]
                    merged = current + [p for p in products if p not in current]
                    conn.execute(
                        'UPDATE accounts SET "Existing Customer" = %s, "Current Products" = %s, '
                        "updated_at = %s WHERE customer_id = %s",
                        ("Y", ", ".join(merged), now, customer_id),
                    )
                    customer_master_created = True
                else:
                    logger.warning("No accounts row for customer %s; customer_master not written", customer_id)

                conn.execute(
                    "UPDATE orders SET status = 'fulfilled', updated_at = %s WHERE order_id = %s",
                    (now, order_id),
                )
                notification_id = notifications.enqueue(
                    "service_activated",
                    recipient_email=order["contact_email"],
                    customer_id=customer_id,
                    order_id=order_id,
                    args={
                        "order_id": order_id,
                        "customer_name": order["customer_name"],
                        "service_type": service_type,
                        "activation_id": activation_id,
                        "circuit_id": circuit_id,
                        "account_id": account_id,
                        "account_number": account_id,
                    },
                    conn=conn,
                )
    except psycopg.Error as exc:
        logger.error("Activation failed for order %s: %s", order_id, exc)
        return {"success": False, "error": f"Service activation error: {type(exc).__name__}"}

    ctx_fields: dict[str, Any] = {
        "status": "fulfilled",
        "activation": {"activation_id": activation_id, "circuit_id": circuit_id, "account_id": account_id,
                       "service_type": service_type, "activated_at": now},
    }
    if isinstance(order_ctx.get("installation"), dict):
        ctx_fields["installation"] = {**order_ctx["installation"], "status": "activated"}
    update_order_context(tool_context, order_id, **ctx_fields)
    logger.info("Service activated for order %s on circuit %s", order_id, circuit_id)
    return {
        "success": True,
        "activation_id": activation_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "service_type": service_type,
        "circuit_id": circuit_id,
        "account_id": account_id,
        "status": "active",
        "activated_at": now,
        "already_active": already_active,
        "customer_master_created": customer_master_created,
        "notification_queued": notification_id is not None,
        **_get_service_parameters(service_type),
        "message": f"Service activated successfully on circuit {circuit_id}",
    }


def run_service_tests(
    circuit_id: str,
    test_types: Optional[List[str]] = None,
) -> dict[str, Any]:
    """Runs service tests to verify connectivity and performance (simulated).

    Args:
        circuit_id: Circuit identifier
        test_types: Optional list of specific tests to run
            (default: speed_test, latency_test, packet_loss_test, connectivity_test)

    Returns:
        Test results
    """
    if test_types is None:
        test_types = ["speed_test", "latency_test", "packet_loss_test", "connectivity_test"]
    tests: dict[str, Any] = {}
    for test_type in test_types:
        if test_type == "speed_test":
            tests["speed_test"] = {
                "download_mbps": round(uniform(900, 980), 2),
                "upload_mbps": round(uniform(900, 980), 2),
                "passed": True,
            }
        elif test_type == "latency_test":
            tests["latency_test"] = {
                "latency_ms": round(uniform(5, 15), 2),
                "jitter_ms": round(uniform(1, 3), 2),
                "passed": True,
            }
        elif test_type == "packet_loss_test":
            tests["packet_loss_test"] = {
                "packet_loss_percent": 0.0,
                "packets_sent": 100,
                "packets_received": 100,
                "passed": True,
            }
        elif test_type == "connectivity_test":
            tests["connectivity_test"] = {
                "link_status": "up",
                "dhcp_status": "success",
                "dns_status": "success",
                "internet_connectivity": "success",
                "passed": True,
            }
    all_passed = all(t.get("passed", False) for t in tests.values())
    return {
        "success": True,
        "circuit_id": circuit_id,
        "tested_at": db.now_iso(),
        "tests": tests,
        "all_tests_passed": all_passed,
        "message": "All service tests passed" if all_passed else "Some tests failed",
    }


def get_service_details(
    circuit_id: Optional[str] = None,
    account_id: Optional[str] = None,
) -> dict[str, Any]:
    """Retrieves details of an activated service from the fulfillment records.

    Args:
        circuit_id: Circuit identifier
        account_id: Account identifier

    Returns:
        Service details and configuration
    """
    if not circuit_id and not account_id:
        return {"success": False, "error": "Either circuit_id or account_id must be provided"}
    try:
        row = db.fetch_one(
            "SELECT f.fulfillment_id, f.order_id, f.customer_id, f.circuit_id, f.account_id, "
            "f.activation_id, f.status, f.updated_at, "
            "(SELECT service_type FROM order_items oi WHERE oi.order_id = f.order_id ORDER BY id LIMIT 1) "
            "AS service_type FROM fulfillments f "
            "WHERE f.status = 'activated' AND (f.circuit_id = %s OR f.account_id = %s) "
            "ORDER BY f.updated_at DESC LIMIT 1",
            (circuit_id, account_id),
        )
    except psycopg.Error as exc:
        logger.error("Service details lookup failed: %s", exc)
        return {"success": False, "error": f"Service details error: {type(exc).__name__}"}
    if row is None:
        return {"success": False, "error": f"No active service found for {circuit_id or account_id}"}
    service_type = row["service_type"] or "Business Internet"
    return {
        "success": True,
        "circuit_id": row["circuit_id"],
        "account_id": row["account_id"],
        "activation_id": row["activation_id"],
        "order_id": row["order_id"],
        "customer_id": row["customer_id"],
        "service_type": service_type,
        "status": "active",
        "activated_at": row["updated_at"],
        "configuration": _get_service_parameters(service_type),
    }


def _get_service_parameters(service_type: str) -> dict[str, Any]:
    """Deterministic network parameters for a service type."""
    service_type = service_type or ""
    params: dict[str, Any] = {
        "ip_address": f"203.0.113.{stable_number(service_type, 250) + 1}",
        "subnet_mask": "255.255.255.248",
        "default_gateway": "203.0.113.1",
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
    }
    lowered = service_type.lower()
    if "fiber" in lowered:
        params.update(technology="FTTP", vlan_id=100)
    elif "coax" in lowered:
        params.update(technology="HFC", vlan_id=200)
    else:
        params.update(technology="Ethernet", vlan_id=300)
    return params
