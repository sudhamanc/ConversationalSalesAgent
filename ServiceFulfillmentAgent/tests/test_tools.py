"""
Tests for service fulfillment agent tools.
"""

import pytest
from datetime import datetime, timedelta
from service_fulfillment_agent.tools.scheduling_tools import (
    check_availability,
    schedule_installation,
)
from service_fulfillment_agent.tools.equipment_tools import (
    provision_equipment,
    track_equipment,
)
from service_fulfillment_agent.tools.installation_tools import (
    dispatch_technician,
    update_installation_status,
)
from service_fulfillment_agent.tools.activation_tools import (
    activate_service,
    run_service_tests,
)
from service_fulfillment_agent.tools.order_tools import (
    create_order,
    get_order_status,
)


class TestSchedulingTools:
    """Tests for scheduling tools."""
    
    def test_check_availability(self):
        """Test availability checking."""
        result = check_availability(
            service_address="123 Main St, Philadelphia, PA 19107",
            service_type="Business Fiber 1 Gbps"
        )
        assert result["success"] is True
        assert len(result["available_slots"]) > 0
    
    def test_schedule_installation(self):
        """Test installation scheduling."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = schedule_installation(
            order_id="ORD-TEST-001",
            service_address="123 Main St",
            scheduled_date=tomorrow,
            window="AM",
            customer_contact="John Doe",
            customer_phone="555-0123"
        )
        assert result["success"] is True
        assert "appointment_id" in result


class TestEquipmentTools:
    """Tests for equipment tools."""
    
    def test_provision_equipment(self):
        """Test equipment provisioning."""
        result = provision_equipment(
            order_id="ORD-TEST-001",
            service_type="Business Fiber 1 Gbps"
        )
        assert result["success"] is True
        assert len(result["equipment_items"]) > 0
    
    def test_track_equipment(self):
        """Test equipment tracking."""
        result = track_equipment(order_id="ORD-TEST-001")
        assert result["success"] is True


class TestInstallationTools:
    """Tests for installation tools."""
    
    def test_dispatch_technician(self):
        """Test technician dispatch."""
        result = dispatch_technician(
            appointment_id="APT-TEST-001",
            order_id="ORD-TEST-001",
            scheduled_date="2026-02-18"
        )
        assert result["success"] is True
        assert "technician_name" in result
    
    def test_update_installation_status(self):
        """Test installation status update."""
        result = update_installation_status(
            appointment_id="APT-TEST-001",
            status="in_progress"
        )
        assert result["success"] is True


class TestActivationTools:
    """Tests for activation tools."""
    
    def test_activate_service(self):
        """Test service activation."""
        result = activate_service(
            order_id="ORD-TEST-001",
            service_type="Business Fiber 1 Gbps"
        )
        assert result["success"] is True
        assert "circuit_id" in result
    
    def test_run_service_tests(self):
        """Test service testing."""
        result = run_service_tests(circuit_id="CKT-TEST-001")
        assert result["success"] is True
        assert result["all_tests_passed"] is True


class TestOrderTools:
    """Tests for order tools."""
    
    def test_create_order(self):
        """Test order creation."""
        result = create_order(
            customer_name="ABC Corporation",
            customer_id="CUST-123",
            service_address="123 Main St, Philadelphia, PA 19107",
            service_type="Business Fiber 1 Gbps",
            contact_phone="555-0123"
        )
        assert result["success"] is True
        assert "order_id" in result
    
    def test_get_order_status(self):
        """Test order status retrieval."""
        result = get_order_status(order_id="ORD-TEST-001")
        assert result["success"] is True
        assert "current_status" in result
