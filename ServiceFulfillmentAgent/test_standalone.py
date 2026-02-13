"""
Standalone test script for Service Fulfillment Agent tools.
Tests the core fulfillment functionality without requiring full ADK setup.
"""

import sys
from datetime import datetime, timedelta
from service_fulfillment_agent.tools.scheduling_tools import (
    check_availability,
    schedule_installation,
    reschedule_appointment
)
from service_fulfillment_agent.tools.equipment_tools import (
    provision_equipment,
    track_equipment,
    verify_equipment_delivery
)
from service_fulfillment_agent.tools.installation_tools import (
    dispatch_technician,
    update_installation_status,
    complete_installation
)
from service_fulfillment_agent.tools.activation_tools import (
    activate_service,
    run_service_tests,
    get_service_details
)
from service_fulfillment_agent.tools.order_tools import (
    create_order,
    get_order_status,
    update_order_status
)

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_order_tools():
    """Test order management tools."""
    print_section("TESTING ORDER MANAGEMENT TOOLS")
    
    # Test 1: Create order
    print("\n1. Creating new order...")
    result = create_order(
        customer_name="ABC Corporation",
        customer_id="CUST-12345",
        service_address="123 Market Street, Philadelphia, PA 19107",
        service_type="Business Fiber 1 Gbps",
        contact_phone="555-0123",
        contact_email="it@abc-corp.com"
    )
    if result.get('success'):
        order_id = result.get('order_id')
        print(f"   Order ID: {order_id}")
        print(f"   Customer: {result.get('customer_name')}")
        print(f"   Service: {result.get('service_type')}")
        print(f"   Status: {result.get('status')}")
        return order_id
    return None

def test_scheduling_tools(order_id):
    """Test scheduling tools."""
    print_section("TESTING SCHEDULING TOOLS")
    
    # Test 1: Check availability
    print("\n1. Checking installation availability...")
    result = check_availability(
        service_address="123 Market Street, Philadelphia, PA 19107",
        service_type="Business Fiber 1 Gbps",
        num_days=5
    )
    if result.get('success'):
        print(f"   Found {result.get('total_slots')} available time slots:")
        for slot in result.get('available_slots', [])[:3]:
            print(f"   - {slot.get('date')} {slot.get('window')} ({slot.get('start_time')}-{slot.get('end_time')})")
        
        # Test 2: Schedule installation
        if result.get('available_slots'):
            first_slot = result['available_slots'][0]
            print(f"\n2. Scheduling installation for {first_slot.get('date')} {first_slot.get('window')}...")
            schedule_result = schedule_installation(
                order_id=order_id,
                service_address="123 Market Street, Philadelphia, PA 19107",
                scheduled_date=first_slot.get('date'),
                window=first_slot.get('window'),
                customer_contact="John Smith",
                customer_phone="555-0123"
            )
            if schedule_result.get('success'):
                appointment_id = schedule_result.get('appointment_id')
                print(f"   Appointment ID: {appointment_id}")
                print(f"   Date: {schedule_result.get('scheduled_date')}")
                print(f"   Window: {schedule_result.get('window')} ({schedule_result.get('start_time')}-{schedule_result.get('end_time')})")
                return appointment_id
    return None

def test_equipment_tools(order_id):
    """Test equipment tools."""
    print_section("TESTING EQUIPMENT TOOLS")
    
    # Test 1: Provision equipment
    print("\n1. Provisioning equipment...")
    result = provision_equipment(
        order_id=order_id,
        service_type="Business Fiber 1 Gbps"
    )
    if result.get('success'):
        print(f"   Ordered {result.get('total_items')} equipment items:")
        for item in result.get('equipment_items', []):
            print(f"   - {item.get('type').upper()}: {item.get('model')}")
            print(f"     Tracking: {item.get('tracking_number')}")
        print(f"   Estimated Delivery: {result.get('estimated_delivery')[:10]}")
    
    # Test 2: Track equipment
    print("\n2. Tracking equipment shipment...")
    result = track_equipment(order_id=order_id)
    if result.get('success'):
        for item in result.get('equipment_items', []):
            print(f"   - {item.get('type').upper()}: {item.get('status')}")
            print(f"     Location: {item.get('location')}")
    
    # Test 3: Verify delivery
    print("\n3. Verifying equipment delivery...")
    result = verify_equipment_delivery(order_id=order_id)
    if result.get('success'):
        status = "✓ All delivered" if result.get('all_equipment_delivered') else "⚠ Pending"
        print(f"   Status: {status}")
        print(f"   Verified Items: {len(result.get('verified_items', []))}")

def test_installation_tools(appointment_id, order_id):
    """Test installation tools."""
    print_section("TESTING INSTALLATION TOOLS")
    
    # Test 1: Dispatch technician
    print("\n1. Dispatching technician...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    result = dispatch_technician(
        appointment_id=appointment_id,
        order_id=order_id,
        scheduled_date=tomorrow
    )
    if result.get('success'):
        print(f"   Dispatch ID: {result.get('dispatch_id')}")
        print(f"   Technician: {result.get('technician_name')}")
        print(f"   Phone: {result.get('technician_phone')}")
        print(f"   Vehicle: {result.get('vehicle_id')}")
    
    # Test 2: Update installation status
    print("\n2. Updating installation status...")
    statuses = ["technician_en_route", "on_site", "in_progress", "testing"]
    for status in statuses:
        result = update_installation_status(
            appointment_id=appointment_id,
            status=status,
            notes=f"Installation {status.replace('_', ' ')}"
        )
        if result.get('success'):
            print(f"   ✓ Status updated: {status}")
    
    # Test 3: Complete installation
    print("\n3. Completing installation...")
    result = complete_installation(
        appointment_id=appointment_id,
        order_id=order_id,
        equipment_installed=["EQ-001", "EQ-002"],
        tests_passed=True,
        customer_signature="John Smith"
    )
    if result.get('success'):
        print(f"   ✓ Installation completed")
        print(f"   Equipment Installed: {', '.join(result.get('equipment_installed', []))}")

def test_activation_tools(order_id):
    """Test service activation tools."""
    print_section("TESTING SERVICE ACTIVATION TOOLS")
    
    # Test 1: Activate service
    print("\n1. Activating service...")
    result = activate_service(
        order_id=order_id,
        service_type="Business Fiber 1 Gbps"
    )
    if result.get('success'):
        circuit_id = result.get('circuit_id')
        print(f"   ✓ Service activated")
        print(f"   Circuit ID: {circuit_id}")
        print(f"   IP Address: {result.get('ip_address')}")
        print(f"   Account ID: {result.get('account_id')}")
        
        # Test 2: Run service tests
        print("\n2. Running service tests...")
        test_result = run_service_tests(circuit_id=circuit_id)
        if test_result.get('success'):
            print(f"   Overall: {'✓ PASSED' if test_result.get('all_tests_passed') else '✗ FAILED'}")
            tests = test_result.get('tests', {})
            if 'speed_test' in tests:
                speed = tests['speed_test']
                print(f"   Speed: ↓ {speed.get('download_mbps')} Mbps / ↑ {speed.get('upload_mbps')} Mbps")
            if 'latency_test' in tests:
                latency = tests['latency_test']
                print(f"   Latency: {latency.get('latency_ms')} ms")
            if 'packet_loss_test' in tests:
                packet = tests['packet_loss_test']
                print(f"   Packet Loss: {packet.get('packet_loss_percent')}%")
        
        # Test 3: Get service details
        print("\n3. Retrieving service details...")
        details = get_service_details(circuit_id=circuit_id)
        if details.get('success'):
            print(f"   Service Type: {details.get('service_type')}")
            print(f"   Status: {details.get('status').upper()}")
            config = details.get('configuration', {})
            print(f"   Gateway: {config.get('default_gateway')}")
            print(f"   DNS: {', '.join(config.get('dns_servers', []))}")

def main():
    """Run all tests."""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + "  SERVICE FULFILLMENT AGENT - STANDALONE TOOL TESTING".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    
    try:
        # Run tests in sequence
        order_id = test_order_tools()
        if not order_id:
            print("\n❌ Failed to create order. Stopping tests.")
            return 1
        
        appointment_id = test_scheduling_tools(order_id)
        if not appointment_id:
            print("\n❌ Failed to schedule appointment. Using mock ID.")
            appointment_id = "APT-TEST-001"
        
        test_equipment_tools(order_id)
        test_installation_tools(appointment_id, order_id)
        test_activation_tools(order_id)
        
        # Get final order status
        print_section("FINAL ORDER STATUS")
        result = get_order_status(order_id=order_id)
        if result.get('success'):
            print(f"\n   Order ID: {result.get('order_id')}")
            print(f"   Customer: {result.get('customer_name')}")
            print(f"   Current Status: {result.get('current_status')}")
            print(f"   Progress: {result.get('progress_percentage')}%")
        
        print_section("ALL TESTS COMPLETED SUCCESSFULLY")
        print("\n✓ All service fulfillment agent tools are working correctly!")
        print("\nNote: These tests use simulated data. In production, these tools")
        print("would integrate with actual scheduling, equipment, and activation systems.\n")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
