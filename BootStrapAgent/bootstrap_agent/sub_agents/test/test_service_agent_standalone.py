"""
Standalone Service Fulfillment Agent Test
Tests Service Fulfillment Agent independently without Super Agent dependency
"""

import asyncio
from datetime import datetime
from ...agent import AgentContext
from ..Service_Fulfillment.service_fulfillment_agent import ServiceFulfillmentAgent


def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


async def test_serviceability_checks():
    """Test serviceability verification"""
    print_section("TEST 1: Serviceability Checks")
    
    context = AgentContext(
        conversation_id="test_serviceability_001",
        user_id="test_user"
    )
    
    service_agent = ServiceFulfillmentAgent(context)
    
    # Test different locations
    locations = [
        {
            'name': 'Philadelphia (Serviceable)',
            'address': {
                'street': '123 Market Street',
                'city': 'Philadelphia',
                'state': 'PA',
                'zip_code': '19102'
            },
            'service_type': 'internet',
            'speed_tier': '1G'
        },
        {
            'name': 'New York City (Serviceable)',
            'address': {
                'street': '456 Broadway',
                'city': 'New York',
                'state': 'NY',
                'zip_code': '10001'
            },
            'service_type': 'internet',
            'speed_tier': '10G'
        },
        {
            'name': 'Rural Area (Not Serviceable)',
            'address': {
                'street': '789 Country Road',
                'city': 'Smalltown',
                'state': 'MT',
                'zip_code': '59001'
            },
            'service_type': 'internet',
            'speed_tier': '1G'
        },
        {
            'name': 'Los Angeles - Voice Service',
            'address': {
                'street': '100 Sunset Blvd',
                'city': 'Los Angeles',
                'state': 'CA',
                'zip_code': '90001'
            },
            'service_type': 'voice',
            'speed_tier': None
        }
    ]
    
    for location in locations:
        print(f"Location: {location['name']}")
        print(f"  Address: {location['address']['street']}, {location['address']['city']}, {location['address']['state']}")
        
        result = await service_agent.process({
            'action': 'check_serviceability',
            'params': {
                'address': location['address'],
                'service_type': location['service_type'],
                'speed_tier': location['speed_tier']
            }
        })
        
        service_data = result['result']
        print(f"  Serviceable: {'✓ YES' if service_data['serviceable'] else '✗ NO'}")
        print(f"  Status: {service_data['status'].upper()}")
        
        if service_data['serviceable']:
            print(f"  Available Services: {len(service_data['available_services'])}")
            for svc in service_data['available_services']:
                print(f"    - {svc['name']} ({svc['type']})")
                if 'speeds' in svc:
                    print(f"      Speeds: {', '.join(svc['speeds'])}")
            
            if service_data.get('available_speeds'):
                print(f"  Available Speeds: {', '.join(service_data['available_speeds'])}")
            
            print(f"  Facility Distance: {service_data['facility_distance_miles']:.0f} feet")
            print(f"  Installation Timeline: {service_data['estimated_install_days']} days")
            
            if service_data.get('monthly_recurring_charge'):
                print(f"  Monthly Charge: ${service_data['monthly_recurring_charge']:.2f}")
            
            if service_data.get('limitations'):
                print(f"  Limitations: {', '.join(service_data['limitations'])}")
        
        print()


async def test_network_capacity():
    """Test network capacity checks"""
    print_section("TEST 2: Network Capacity Analysis")
    
    context = AgentContext(
        conversation_id="test_capacity_001",
        user_id="test_user"
    )
    
    service_agent = ServiceFulfillmentAgent(context)
    
    # Test different capacity scenarios
    scenarios = [
        {
            'name': 'Small Business - 100M',
            'zip_code': '19102',
            'bandwidth_required': 100  # 100 Mbps
        },
        {
            'name': 'Medium Business - 1G',
            'zip_code': '10001',
            'bandwidth_required': 1000  # 1 Gbps
        },
        {
            'name': 'Large Enterprise - 10G',
            'zip_code': '90001',
            'bandwidth_required': 10000  # 10 Gbps
        },
        {
            'name': 'Data Center - 100G',
            'zip_code': '19103',
            'bandwidth_required': 100000  # 100 Gbps (may exceed capacity)
        }
    ]
    
    for scenario in scenarios:
        print(f"Scenario: {scenario['name']}")
        print(f"  Location: {scenario['zip_code']}")
        print(f"  Required Bandwidth: {scenario['bandwidth_required']} Mbps")
        
        result = await service_agent.process({
            'action': 'check_capacity',
            'params': {
                'zip_code': scenario['zip_code'],
                'bandwidth_required': scenario['bandwidth_required']
            }
        })
        
        capacity_data = result['result']
        print(f"  Available Capacity: {capacity_data['available_capacity_mbps']:,.2f} Mbps")
        print(f"  Current Utilization: {capacity_data['current_utilization_pct']}%")
        print(f"  Sufficient Capacity: {'✓ YES' if capacity_data['sufficient_capacity'] else '✗ NO'}")
        print(f"  Recommendation: {capacity_data['recommendation']}")
        print()


async def test_installation_scheduling():
    """Test installation slot retrieval and scheduling"""
    print_section("TEST 3: Installation Scheduling")
    
    context = AgentContext(
        conversation_id="test_scheduling_001",
        user_id="test_user"
    )
    
    service_agent = ServiceFulfillmentAgent(context)
    
    # Test different installation types
    installation_types = ['standard', 'expedited', 'premium']
    
    for install_type in installation_types:
        print(f"Installation Type: {install_type.upper()}")
        
        # Get available slots
        slots_result = await service_agent.process({
            'action': 'get_slots',
            'params': {
                'zip_code': '19102',
                'installation_type': install_type
            }
        })
        
        slots_data = slots_result['result']
        print(f"  Total Available Slots: {slots_data['total_available']}")
        print(f"  Earliest Available: {slots_data['earliest_available']['date']} at {slots_data['earliest_available']['start_time']}")
        print(f"  Duration: {slots_data['earliest_available']['duration_hours']} hours")
        
        print(f"\n  First 3 Available Slots:")
        for i, slot in enumerate(slots_data['available_slots'][:3], 1):
            print(f"    {i}. {slot['date']} {slot['start_time']}-{slot['end_time']}")
            print(f"       Slot ID: {slot['slot_id']}, Technician: {slot['technician_id']}")
        
        # Schedule the first available slot
        selected_slot = slots_data['available_slots'][0]
        
        schedule_result = await service_agent.process({
            'action': 'schedule',
            'params': {
                'order_id': f'order_install_{install_type}',
                'slot_id': selected_slot['slot_id'],
                'installation_type': install_type,
                'customer_contact': {
                    'name': 'John Doe',
                    'phone': '+1-215-555-1234',
                    'email': 'john.doe@example.com'
                }
            }
        })
        
        schedule_data = schedule_result['result']
        print(f"\n  ✓ Installation Scheduled")
        print(f"    Appointment ID: {schedule_data['appointment_id']}")
        print(f"    Status: {schedule_data['status']}")
        print(f"    Confirmation Sent: {schedule_data['confirmation_sent']}")
        print(f"    Technician Assigned: {schedule_data['technician_assigned']}")
        
        print(f"\n  Pre-Installation Checklist:")
        for item in schedule_data['pre_install_checklist']:
            print(f"    □ {item}")
        
        print("\n" + "-"*60 + "\n")


async def test_service_provisioning():
    """Test service provisioning"""
    print_section("TEST 4: Service Provisioning")
    
    context = AgentContext(
        conversation_id="test_provisioning_001",
        user_id="test_user"
    )
    
    service_agent = ServiceFulfillmentAgent(context)
    
    # Test different service types
    service_configs = [
        {
            'name': 'Business Internet 1G',
            'service_type': 'internet',
            'speed_tier': '1G',
            'static_ip': True
        },
        {
            'name': 'Business Voice (5 lines)',
            'service_type': 'voice',
            'lines': 5,
            'features': ['auto_attendant', 'voicemail', 'call_forwarding']
        },
        {
            'name': 'Enterprise Internet 10G',
            'service_type': 'internet',
            'speed_tier': '10G',
            'static_ip': True,
            'dedicated': True
        }
    ]
    
    for config in service_configs:
        print(f"Service: {config['name']}")
        
        result = await service_agent.process({
            'action': 'provision',
            'params': {
                'order_id': f'order_{config["service_type"]}_{int(datetime.now().timestamp())}',
                'service_config': config
            }
        })
        
        provision_data = result['result']
        print(f"  Status: {provision_data['status'].upper()}")
        print(f"  Provisioning ID: {provision_data['provisioning_id']}")
        print(f"  Circuit ID: {provision_data['circuit_id']}")
        print(f"  Total Provisioning Time: {provision_data['total_duration_sec']} seconds")
        
        print(f"\n  Provisioning Steps:")
        for step in provision_data['provisioning_steps']:
            print(f"    ✓ {step['step']}: {step['status']} ({step['duration_sec']}s)")
        
        print(f"\n  Service Credentials:")
        creds = provision_data['service_credentials']
        if config['service_type'] == 'internet':
            print(f"    IP Address: {creds.get('ip_address')}")
            print(f"    Subnet Mask: {creds.get('subnet_mask')}")
            print(f"    Gateway: {creds.get('gateway')}")
            print(f"    DNS Primary: {creds.get('dns_primary')}")
            print(f"    DNS Secondary: {creds.get('dns_secondary')}")
        elif config['service_type'] == 'voice':
            print(f"    Phone Numbers: {', '.join(creds.get('phone_numbers', []))}")
            print(f"    SIP Domain: {creds.get('sip_domain')}")
            print(f"    SIP Username: {creds.get('sip_username')}")
        
        print("\n" + "-"*60 + "\n")


async def test_provisioning_status():
    """Test provision status checking"""
    print_section("TEST 5: Provisioning Status Tracking")
    
    context = AgentContext(
        conversation_id="test_status_001",
        user_id="test_user"
    )
    
    service_agent = ServiceFulfillmentAgent(context)
    
    # First, provision a service
    print("Step 1: Provisioning a new service...")
    order_id = f'order_status_test_{int(datetime.now().timestamp())}'
    
    provision_result = await service_agent.process({
        'action': 'provision',
        'params': {
            'order_id': order_id,
            'service_config': {
                'service_type': 'internet',
                'speed_tier': '1G'
            }
        }
    })
    
    print(f"  Order ID: {order_id}")
    print(f"  Initial Status: {provision_result['result']['status']}")
    print()
    
    # Now check status
    print("Step 2: Checking provision status...")
    status_result = await service_agent.process({
        'action': 'check_status',
        'params': {
            'order_id': order_id
        }
    })
    
    status_data = status_result['result']
    print(f"  Order ID: {status_data['order_id']}")
    print(f"  Status: {status_data['status'].upper()}")
    print(f"  Provisioning ID: {status_data.get('provisioning_id', 'N/A')}")
    print(f"  Circuit ID: {status_data.get('circuit_id', 'N/A')}")
    print(f"  Last Updated: {status_data['last_updated']}")
    print()
    
    # Check status for non-existent order
    print("Step 3: Checking status for non-existent order...")
    no_order_result = await service_agent.process({
        'action': 'check_status',
        'params': {
            'order_id': 'nonexistent_order_12345'
        }
    })
    
    no_order_data = no_order_result['result']
    print(f"  Order ID: {no_order_data['order_id']}")
    print(f"  Status: {no_order_data['status'].upper()}")
    print(f"  Message: {no_order_data.get('message', 'N/A')}")
    print()


async def test_full_fulfillment_flow():
    """Test complete end-to-end fulfillment flow"""
    print_section("TEST 6: Complete Fulfillment Flow")
    
    context = AgentContext(
        conversation_id="test_full_flow_001",
        user_id="test_user"
    )
    
    service_agent = ServiceFulfillmentAgent(context)
    
    # Test different scenarios
    scenarios = [
        {
            'name': 'Standard Internet Installation',
            'address': {
                'street': '123 Market Street',
                'city': 'Philadelphia',
                'state': 'PA',
                'zip_code': '19102'
            },
            'service_type': 'internet',
            'speed_tier': '1G',
            'installation_type': 'standard'
        },
        {
            'name': 'Expedited Enterprise Setup',
            'address': {
                'street': '456 Broadway',
                'city': 'New York',
                'state': 'NY',
                'zip_code': '10001'
            },
            'service_type': 'internet',
            'speed_tier': '10G',
            'installation_type': 'expedited'
        },
        {
            'name': 'Not Serviceable Location',
            'address': {
                'street': '789 Rural Route',
                'city': 'Smalltown',
                'state': 'WY',
                'zip_code': '82001'
            },
            'service_type': 'internet',
            'speed_tier': '1G',
            'installation_type': 'standard'
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"Scenario {i}: {scenario['name']}")
        print("-" * 60)
        
        result = await service_agent.process({
            'action': 'full_fulfillment_flow',
            'address': scenario['address'],
            'service_type': scenario['service_type'],
            'speed_tier': scenario['speed_tier'],
            'installation_type': scenario['installation_type']
        })
        
        print(f"Overall Status: {result['overall_status'].upper()}")
        print(f"\nSteps Completed:")
        
        for step in result['steps']:
            step_name = step['step']
            step_result = step['result']
            
            if step_name == 'serviceability_check':
                service = step_result.get('result', {})
                print(f"  ✓ Serviceability Check")
                print(f"    - Serviceable: {service.get('serviceable')}")
                print(f"    - Status: {service.get('status')}")
                if service.get('serviceable'):
                    print(f"    - Available Services: {len(service.get('available_services', []))}")
                
            elif step_name == 'capacity_check':
                capacity = step_result.get('result', {})
                print(f"  ✓ Capacity Check")
                print(f"    - Sufficient: {capacity.get('sufficient_capacity')}")
                print(f"    - Available: {capacity.get('available_capacity_mbps', 0):.2f} Mbps")
                print(f"    - Utilization: {capacity.get('current_utilization_pct')}%")
                
            elif step_name == 'slot_availability':
                slots = step_result.get('result', {})
                print(f"  ✓ Slot Availability")
                print(f"    - Available Slots: {slots.get('total_available', 0)}")
                if slots.get('earliest_available'):
                    earliest = slots['earliest_available']
                    print(f"    - Earliest: {earliest['date']} at {earliest['start_time']}")
        
        if result['overall_status'] == 'ready_for_scheduling':
            print(f"\n✓ Service Available - Ready for Scheduling")
            if 'next_steps' in result:
                print(f"\nNext Steps:")
                for step in result['next_steps']:
                    print(f"  → {step}")
        else:
            print(f"\n✗ Service Not Available")
            print(f"  Reason: {result.get('reason', 'Unknown')}")
        
        print("\n")


async def test_multiple_services():
    """Test handling multiple service types"""
    print_section("TEST 7: Multiple Service Types")
    
    context = AgentContext(
        conversation_id="test_multi_services_001",
        user_id="test_user"
    )
    
    service_agent = ServiceFulfillmentAgent(context)
    
    # Check serviceability for multiple services at same location
    address = {
        'street': '100 Business Plaza',
        'city': 'Philadelphia',
        'state': 'PA',
        'zip_code': '19103'
    }
    
    service_types = ['internet', 'voice', 'cloud']
    
    print(f"Location: {address['street']}, {address['city']}, {address['state']}")
    print(f"ZIP Code: {address['zip_code']}\n")
    
    for service_type in service_types:
        result = await service_agent.process({
            'action': 'check_serviceability',
            'params': {
                'address': address,
                'service_type': service_type,
                'speed_tier': '1G' if service_type in ['internet', 'cloud'] else None
            }
        })
        
        service_data = result['result']
        print(f"Service Type: {service_type.upper()}")
        print(f"  Serviceable: {'✓' if service_data['serviceable'] else '✗'}")
        
        if service_data['serviceable']:
            # Find this service in available services
            service_info = next(
                (s for s in service_data['available_services'] if s['type'] == service_type),
                None
            )
            
            if service_info:
                print(f"  Name: {service_info['name']}")
                if 'speeds' in service_info:
                    print(f"  Available Speeds: {', '.join(service_info['speeds'])}")
                if 'features' in service_info:
                    print(f"  Features: {', '.join(service_info['features'])}")
                if 'sla' in service_info:
                    print(f"  SLA: {service_info['sla']}")
        
        print()


async def test_agent_state_and_memory():
    """Test agent state and memory features"""
    print_section("TEST 8: Agent State & Memory")
    
    context = AgentContext(
        conversation_id="test_state_001",
        user_id="test_user"
    )
    
    service_agent = ServiceFulfillmentAgent(context)
    
    # Perform several operations to build memory
    await service_agent.process({
        'action': 'check_serviceability',
        'params': {
            'address': {
                'street': '123 Main St',
                'city': 'Philadelphia',
                'state': 'PA',
                'zip_code': '19102'
            },
            'service_type': 'internet',
            'speed_tier': '1G'
        }
    })
    
    await service_agent.process({
        'action': 'check_capacity',
        'params': {
            'zip_code': '19102',
            'bandwidth_required': 1000
        }
    })
    
    await service_agent.process({
        'action': 'provision',
        'params': {
            'order_id': 'test_order_123',
            'service_config': {
                'service_type': 'internet',
                'speed_tier': '1G'
            }
        }
    })
    
    # Get agent state
    state = service_agent.get_state()
    print("Agent State:")
    print(f"  Agent ID: {state['agent_id']}")
    print(f"  Agent Name: {state['agent_name']}")
    print(f"  Status: {state['status']}")
    print(f"  Tools Available: {len(state['tools'])}")
    print(f"    - {', '.join(state['tools'])}")
    print(f"  Memory Entries: {state['memory_size']}")
    print()
    
    # Get memory
    all_memory = service_agent.get_memory()
    print(f"Total Memory Entries: {len(all_memory)}")
    print("\nMemory Timeline:")
    for entry in all_memory[-6:]:  # Last 6 entries
        print(f"  [{entry['timestamp']}] {entry['type']}")
    print()
    
    # Get filtered memory
    serviceability_checks = service_agent.get_memory(filter_type='serviceability_check')
    print(f"Serviceability Checks: {len(serviceability_checks)}")
    
    capacity_checks = service_agent.get_memory(filter_type='capacity_check')
    print(f"Capacity Checks: {len(capacity_checks)}")
    
    provisions = service_agent.get_memory(filter_type='service_provisioned')
    print(f"Services Provisioned: {len(provisions)}")
    print()
    
    # Show operational stats
    print("Operational Statistics:")
    print(f"  Scheduled Installations: {len(service_agent.scheduled_installations)}")
    print(f"  Provisioning Queue: {len(service_agent.provisioning_queue)}")
    print(f"  Coverage Areas: {len(service_agent.coverage_map)} states")
    print()


async def main():
    """Run all standalone service fulfillment agent tests"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  SERVICE FULFILLMENT AGENT - STANDALONE TEST SUITE".center(78) + "█")
    print("█" + "  No Super Agent Required".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    # Run all tests
    await test_serviceability_checks()
    await test_network_capacity()
    await test_installation_scheduling()
    await test_service_provisioning()
    await test_provisioning_status()
    await test_full_fulfillment_flow()
    await test_multiple_services()
    await test_agent_state_and_memory()
    
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  ALL SERVICE FULFILLMENT TESTS COMPLETED SUCCESSFULLY".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
