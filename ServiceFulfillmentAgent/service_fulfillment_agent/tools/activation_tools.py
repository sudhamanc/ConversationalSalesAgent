"""
Service activation tools for the Service Fulfillment Agent.

These tools handle service activation, testing, and verification.
"""

import json
import os
import sqlite3
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from random import uniform

from google.adk.tools.tool_context import ToolContext

from ..utils.logger import get_logger

logger = get_logger(__name__)


def _get_db_connection():
    """Return a connection to the unified sales_agent.db, or None if not configured."""
    db_path = os.getenv("SALES_AGENT_DB_PATH")
    if not db_path:
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def activate_service(
    order_id: str,
    service_type: str,
    circuit_id: str = None,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """
    Activates service for a completed installation.

    For production: Integrates with service activation platform
    For testing: Simulates service activation

    Args:
        order_id: Order identifier
        service_type: Type of service to activate
        circuit_id: Circuit identifier (auto-generated if not provided)

    Returns:
        Service activation details
    """
    # Read order_context / payment_context from session state to resolve
    # order_id and service_type if the LLM didn't pass them. Existing DB
    # logic in _update_fulfillment_activation stays unchanged.
    if tool_context is not None:
        order_ctx = tool_context.state.get("order_context") or {}
        payment_ctx = tool_context.state.get("payment_context") or {}
        logger.info(f"[STATE READ] activate_service <- order_context order_id={order_ctx.get('order_id')} service_type={order_ctx.get('service_type')}")
        logger.info(f"[STATE READ] activate_service <- payment_context txn={payment_ctx.get('transaction_id')} status={payment_ctx.get('status')}")
        if not order_id:
            state_oid = order_ctx.get("order_id") or payment_ctx.get("order_id")
            if isinstance(state_oid, str):
                order_id = state_oid
        if not service_type:
            state_stype = order_ctx.get("service_type")
            if isinstance(state_stype, str):
                service_type = state_stype

    logger.info(f"Activating service for order {order_id}")

    try:
        # Generate circuit ID if not provided
        if not circuit_id:
            circuit_id = f"CKT-{datetime.now().strftime('%Y%m')}-{hash(order_id) % 100000:05d}"
        
        # Generate activation ID
        activation_id = f"ACT-{order_id.split('-')[-1]}"
        
        # Simulate service activation
        # In production: Call service activation platform API
        
        # Determine service parameters based on type
        service_params = _get_service_parameters(service_type)
        
        activation = {
            "success": True,
            "activation_id": activation_id,
            "order_id": order_id,
            "service_type": service_type,
            "circuit_id": circuit_id,
            "account_id": f"ACCT-{hash(order_id) % 1000000:06d}",
            "status": "active",
            "activated_at": datetime.now().isoformat(),
            **service_params,
            "message": f"Service activated successfully on circuit {circuit_id}"
        }
        
        logger.info(f"Service activated: {circuit_id}")
        
        # Update fulfillment record in unified DB — mark as activated
        _update_fulfillment_activation(
            order_id=order_id,
            activation_id=activation_id,
            circuit_id=circuit_id,
            account_id=activation["account_id"],
        )

        # Auto-send SERVICE_ACTIVATED notification
        _auto_send_notification(
            notification_type="SERVICE_ACTIVATED",
            order_id=order_id,
            metadata={"activation_id": activation_id, "circuit_id": circuit_id,
                       "service_type": service_type, "account_id": activation["account_id"]},
        )

        return activation
    
    except Exception as e:
        logger.error(f"Error activating service: {e}")
        return {
            "success": False,
            "error": f"Service activation error: {str(e)}"
        }


def run_service_tests(
    circuit_id: str,
    test_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Runs service tests to verify connectivity and performance.
    
    Args:
        circuit_id: Circuit identifier
        test_types: Optional list of specific tests to run
            (default: speed_test, latency_test, packet_loss_test)
    
    Returns:
        Test results
    """
    logger.info(f"Running service tests for circuit {circuit_id}")
    
    try:
        if test_types is None:
            test_types = ["speed_test", "latency_test", "packet_loss_test", "connectivity_test"]
        
        # Simulate service tests
        # In production: Run actual network tests
        
        test_results = {
            "success": True,
            "circuit_id": circuit_id,
            "tested_at": datetime.now().isoformat(),
            "tests": {}
        }
        
        # Run each test type
        for test_type in test_types:
            if test_type == "speed_test":
                test_results["tests"]["speed_test"] = {
                    "download_mbps": round(uniform(900, 980), 2),
                    "upload_mbps": round(uniform(900, 980), 2),
                    "passed": True
                }
            
            elif test_type == "latency_test":
                test_results["tests"]["latency_test"] = {
                    "latency_ms": round(uniform(5, 15), 2),
                    "jitter_ms": round(uniform(1, 3), 2),
                    "passed": True
                }
            
            elif test_type == "packet_loss_test":
                test_results["tests"]["packet_loss_test"] = {
                    "packet_loss_percent": 0.0,
                    "packets_sent": 100,
                    "packets_received": 100,
                    "passed": True
                }
            
            elif test_type == "connectivity_test":
                test_results["tests"]["connectivity_test"] = {
                    "link_status": "up",
                    "dhcp_status": "success",
                    "dns_status": "success",
                    "internet_connectivity": "success",
                    "passed": True
                }
        
        # Overall result
        all_passed = all(test.get("passed", False) for test in test_results["tests"].values())
        test_results["all_tests_passed"] = all_passed
        test_results["message"] = "All service tests passed" if all_passed else "Some tests failed"
        
        logger.info(f"Service tests completed: {'PASSED' if all_passed else 'FAILED'}")
        return test_results
    
    except Exception as e:
        logger.error(f"Error running service tests: {e}")
        return {
            "success": False,
            "error": f"Service test error: {str(e)}"
        }


def get_service_details(
    circuit_id: str = None,
    account_id: str = None
) -> Dict[str, Any]:
    """
    Retrieves detailed service information.
    
    Args:
        circuit_id: Circuit identifier
        account_id: Account identifier
    
    Returns:
        Service details and configuration
    """
    logger.info(f"Retrieving service details for circuit {circuit_id} / account {account_id}")
    
    try:
        if not circuit_id and not account_id:
            return {
                "success": False,
                "error": "Either circuit_id or account_id must be provided"
            }
        
        # Simulate retrieving service details
        # In production: Query service management platform
        
        details = {
            "success": True,
            "circuit_id": circuit_id or "CKT-202602-12345",
            "account_id": account_id or "ACCT-789012",
            "service_type": "Business Fiber 1 Gbps",
            "status": "active",
            "activated_at": datetime.now().isoformat(),
            "configuration": {
                "ip_address": "203.0.113.45",
                "subnet_mask": "255.255.255.248",
                "default_gateway": "203.0.113.1",
                "dns_servers": ["8.8.8.8", "8.8.4.4"],
                "vlan_id": 100
            },
            "equipment": [
                {
                    "type": "router",
                    "model": "XR-1000",
                    "serial": "SN123456789",
                    "ip_address": "203.0.113.45"
                },
                {
                    "type": "ont",
                    "model": "Fiber ONT",
                    "serial": "SN987654321",
                    "status": "online"
                }
            ],
            "service_level": {
                "bandwidth": "1 Gbps symmetric",
                "sla_uptime": "99.9%",
                "support_tier": "Business Premium"
            }
        }
        
        return details
    
    except Exception as e:
        logger.error(f"Error retrieving service details: {e}")
        return {
            "success": False,
            "error": f"Service details error: {str(e)}"
        }


# Helper function

def _get_service_parameters(service_type: str) -> Dict[str, Any]:
    """
    Generates service-specific parameters based on service type.
    
    Args:
        service_type: Type of service being activated
    
    Returns:
        Service parameters
    """
    # Default parameters
    params = {
        "ip_address": f"203.0.113.{hash(service_type) % 250 + 1}",
        "subnet_mask": "255.255.255.248",
        "default_gateway": "203.0.113.1",
        "dns_servers": ["8.8.8.8", "8.8.4.4"]
    }
    
    # Service-specific additions
    if "fiber" in service_type.lower():
        params["technology"] = "FTTP"
        params["vlan_id"] = 100
    elif "coax" in service_type.lower():
        params["technology"] = "HFC"
        params["vlan_id"] = 200
    else:
        params["technology"] = "Ethernet"
        params["vlan_id"] = 300
    
    return params


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------

def _update_fulfillment_activation(
    order_id: str,
    activation_id: str,
    circuit_id: str,
    account_id: str,
) -> None:
    """Mark the fulfillment as 'activated' and populate customer_master.

    This is the final lifecycle step — the prospect becomes a customer.
    """
    conn = _get_db_connection()
    if conn is None:
        return
    try:
        now = datetime.now().isoformat()

        # Update fulfillment row (match by order_id since that's what we have)
        conn.execute(
            """UPDATE fulfillments
               SET activation_id = ?, circuit_id = ?, account_id = ?,
                   status = 'activated', updated_at = ?
               WHERE order_id = ?""",
            (activation_id, circuit_id, account_id, now, order_id),
        )

        # Look up order + account data to populate customer_master
        order_row = conn.execute(
            "SELECT customer_id, customer_name, service_address, contact_phone, "
            "contact_email, total_amount FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()

        if order_row and order_row["customer_id"]:
            cust_id = order_row["customer_id"]

            # Look up account address
            acct = conn.execute(
                'SELECT "Company Name", Street, City, State, zip_code '
                "FROM accounts WHERE customer_id = ?",
                (cust_id,),
            ).fetchone()

            if acct:
                # Get ordered service types from order_items
                items = conn.execute(
                    "SELECT service_type FROM order_items WHERE order_id = ?",
                    (order_id,),
                ).fetchall()
                products = json.dumps([r["service_type"] for r in items])

                conn.execute(
                    """INSERT OR REPLACE INTO customer_master
                       (customer_id, company_name, street, city, state, zip_code,
                        contact_name, contact_email, contact_phone,
                        first_order_id, circuit_id, account_id,
                        contracted_products, monthly_revenue,
                        activated_at, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        cust_id,
                        acct["Company Name"],
                        acct["Street"],
                        acct["City"],
                        acct["State"],
                        acct["zip_code"],
                        order_row["customer_name"],
                        order_row["contact_email"],
                        order_row["contact_phone"],
                        order_id,
                        circuit_id,
                        account_id,
                        products,
                        order_row["total_amount"],
                        now,
                        now,
                        now,
                    ),
                )

                # Mark prospect as existing customer
                conn.execute(
                    'UPDATE accounts SET "Existing Customer" = \'Y\', updated_at = ? '
                    "WHERE customer_id = ?",
                    (now, cust_id),
                )

                # Mark order as fulfilled
                conn.execute(
                    "UPDATE orders SET status = 'fulfilled', updated_at = ? WHERE order_id = ?",
                    (now, order_id),
                )

                logger.info(
                    f"Customer {cust_id} activated: customer_master created, "
                    f"accounts.Existing Customer='Y', order={order_id} fulfilled"
                )

        conn.commit()
    except Exception as exc:
        logger.warning(f"Failed to update fulfillment activation (non-fatal): {exc}")
    finally:
        conn.close()


def _auto_send_notification(
    notification_type: str,
    order_id: str,
    metadata: dict,
    customer_id: str = "",
    recipient_email: str | None = None,
) -> None:
    """Send a notification via sys.modules dispatcher (best-effort, non-fatal)."""
    try:
        comms = sys.modules.get("customer_communication_agent.tools.notification_tools")
        if comms is None:
            return
        if hasattr(comms, "send_notification"):
            comms.send_notification(
                notification_type=notification_type,
                customer_id=customer_id,
                order_id=order_id,
                recipient_email=recipient_email,
                metadata=metadata,
            )
            logger.info(f"Auto-sent {notification_type} notification")
        elif notification_type == "SERVICE_ACTIVATED" and hasattr(comms, "send_service_activated_notification"):
            comms.send_service_activated_notification(
                order_id=order_id,
                customer_name=customer_id,
                customer_email=recipient_email,
                service_type=metadata.get("service_type", ""),
                account_number=metadata.get("account_id", ""),
                circuit_id=metadata.get("circuit_id", ""),
            )
            logger.info(f"Auto-sent {notification_type} notification")
    except Exception as exc:
        logger.warning(f"Auto notification {notification_type} failed (non-fatal): {exc}")
