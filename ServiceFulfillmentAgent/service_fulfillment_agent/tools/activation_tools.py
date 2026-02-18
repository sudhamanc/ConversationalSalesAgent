"""
Service activation tools for the Service Fulfillment Agent.

These tools handle service activation, testing, and verification.
"""

import json
from typing import Dict, Any
from datetime import datetime
from random import uniform
from ..utils.logger import get_logger

logger = get_logger(__name__)


def activate_service(
    order_id: str,
    service_type: str,
    circuit_id: str = None
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
        return activation
    
    except Exception as e:
        logger.error(f"Error activating service: {e}")
        return {
            "success": False,
            "error": f"Service activation error: {str(e)}"
        }


def run_service_tests(
    circuit_id: str,
    test_types: list = None
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
