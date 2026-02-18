"""
Service Fulfillment Agent - B2B Agentic Sales System
Handles service availability verification, installation scheduling, and order provisioning

This agent follows the Hybrid Cognitive Model:
- LLM: Intent understanding, scheduling optimization
- Deterministic: Serviceability API, inventory checks, provisioning systems
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, time
from enum import Enum
import hashlib
import random

from ...agent import BaseAgent, AgentContext, AgentMessage, Tool, AgentStatus


class ServiceStatus(Enum):
    """Service availability status"""
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"
    PLANNED = "planned"


class InstallationType(Enum):
    """Installation types"""
    STANDARD = "standard"
    EXPEDITED = "expedited"
    PREMIUM = "premium"
    SELF_INSTALL = "self_install"


class ProvisioningStatus(Enum):
    """Order provisioning status"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ServiceType(Enum):
    """Types of B2B services"""
    INTERNET = "internet"
    VOICE = "voice"
    TV = "tv"
    CLOUD = "cloud"
    MANAGED_SERVICES = "managed_services"


class ServiceFulfillmentAgent(BaseAgent):
    """
    Service Fulfillment Agent for B2B Sales System
    
    Responsibilities:
    - Check service availability at customer location
    - Verify network capacity and infrastructure
    - Schedule installation appointments
    - Coordinate with field technicians
    - Provision services and activate orders
    - Track installation progress
    
    Tools:
    - check_serviceability
    - check_network_capacity
    - get_available_slots
    - schedule_installation
    - provision_service
    - check_provision_status
    """
    
    def __init__(self, context: AgentContext):
        super().__init__(
            agent_id="service_fulfillment_agent_001",
            agent_name="Service Fulfillment Agent",
            description="Handles service availability, installation scheduling, and order provisioning for B2B services",
            context=context
        )
        
        # Service fulfillment state
        self.scheduled_installations: Dict[str, Dict] = {}
        self.provisioning_queue: List[Dict] = []
        self.coverage_map: Dict[str, List[str]] = self._initialize_coverage_map()
        
        # Service parameters
        self.installation_duration = {
            InstallationType.STANDARD: 4,  # hours
            InstallationType.EXPEDITED: 2,
            InstallationType.PREMIUM: 6,
            InstallationType.SELF_INSTALL: 0
        }
        
        # Business hours for installations
        self.business_hours_start = time(8, 0)
        self.business_hours_end = time(18, 0)
    
    def _initialize_coverage_map(self) -> Dict[str, List[str]]:
        """
        Initialize service coverage map
        
        In production, this would query:
        - GIS database
        - Network topology database
        - Infrastructure management system
        """
        return {
            # Major metropolitan areas with full coverage
            "PA": ["19102", "19103", "19104", "19106", "19107", "19109", "19110"],
            "NY": ["10001", "10002", "10003", "10004", "10005"],
            "CA": ["90001", "90002", "90003", "94102", "94103"],
            "TX": ["75201", "75202", "78701", "78702"],
            "IL": ["60601", "60602", "60603", "60604"],
            # Expand as needed
        }
    
    def _register_tools(self):
        """Register service fulfillment tools"""
        
        # Serviceability Check Tool
        self.register_tool(Tool(
            name="check_serviceability",
            description="Check if service is available at a given address",
            parameters={
                "address": {"type": "object", "required": True},
                "service_type": {"type": "string", "enum": [s.value for s in ServiceType]},
                "speed_tier": {"type": "string"}
            },
            function=self._check_serviceability
        ))
        
        # Network Capacity Tool
        self.register_tool(Tool(
            name="check_network_capacity",
            description="Check available network capacity for new service",
            parameters={
                "zip_code": {"type": "string", "required": True},
                "bandwidth_required": {"type": "number", "required": True}
            },
            function=self._check_network_capacity
        ))
        
        # Available Time Slots Tool
        self.register_tool(Tool(
            name="get_available_slots",
            description="Get available installation time slots",
            parameters={
                "zip_code": {"type": "string", "required": True},
                "installation_type": {"type": "string", "enum": [t.value for t in InstallationType]},
                "preferred_dates": {"type": "array"}
            },
            function=self._get_available_slots
        ))
        
        # Schedule Installation Tool
        self.register_tool(Tool(
            name="schedule_installation",
            description="Schedule installation appointment",
            parameters={
                "order_id": {"type": "string", "required": True},
                "slot_id": {"type": "string", "required": True},
                "installation_type": {"type": "string", "required": True},
                "customer_contact": {"type": "object", "required": True}
            },
            function=self._schedule_installation
        ))
        
        # Service Provisioning Tool
        self.register_tool(Tool(
            name="provision_service",
            description="Provision and activate service",
            parameters={
                "order_id": {"type": "string", "required": True},
                "service_config": {"type": "object", "required": True}
            },
            function=self._provision_service
        ))
        
        # Provision Status Tool
        self.register_tool(Tool(
            name="check_provision_status",
            description="Check provisioning status of an order",
            parameters={
                "order_id": {"type": "string", "required": True}
            },
            function=self._check_provision_status
        ))
    
    # ==================== TOOL IMPLEMENTATIONS ====================
    
    def _check_serviceability(self,
                             address: Dict[str, Any],
                             service_type: str,
                             speed_tier: Optional[str] = None) -> Dict[str, Any]:
        """
        Check service availability at address
        
        In production, integrates with:
        - GIS/mapping systems
        - Network infrastructure database
        - OSS/BSS systems
        
        Args:
            address: Address dictionary with street, city, state, zip
            service_type: Type of service requested
            speed_tier: Optional speed tier (e.g., "1G", "10G")
            
        Returns:
            Serviceability result
        """
        self.logger.info(f"Checking serviceability for {address.get('zip_code')}")
        
        zip_code = address.get('zip_code')
        state = address.get('state')
        
        # Check coverage
        is_serviceable = self._is_in_coverage(state, zip_code)
        
        # Determine available services and speeds
        available_services = []
        available_speeds = []
        
        if is_serviceable:
            # Mock available services based on location
            service_availability = self._get_service_availability(zip_code)
            available_services = service_availability['services']
            
            if service_type in [s['type'] for s in available_services]:
                service_info = next(s for s in available_services if s['type'] == service_type)
                available_speeds = service_info.get('speeds', [])
        
        # Calculate distance to nearest facility (mock)
        facility_distance = self._calculate_facility_distance(address)
        
        # Determine installation requirements
        installation_required = service_type != ServiceType.CLOUD.value
        
        result = {
            "serviceable": is_serviceable,
            "status": ServiceStatus.AVAILABLE.value if is_serviceable else ServiceStatus.UNAVAILABLE.value,
            "address": address,
            "service_type": service_type,
            "available_services": available_services,
            "available_speeds": available_speeds,
            "facility_distance_miles": facility_distance,
            "installation_required": installation_required,
            "estimated_install_days": self._estimate_install_timeline(is_serviceable),
            "monthly_recurring_charge": self._calculate_mrc(service_type, speed_tier) if is_serviceable else None,
            "one_time_charges": self._calculate_otc(installation_required) if is_serviceable else None,
            "checked_at": datetime.now().isoformat()
        }
        
        # Add limitations if partially serviceable
        if is_serviceable and facility_distance > 1000:
            result['status'] = ServiceStatus.LIMITED.value
            result['limitations'] = [
                "Extended distance from facility",
                "May require additional construction",
                "Longer installation timeline"
            ]
        
        self.add_to_memory({
            'type': 'serviceability_check',
            'zip_code': zip_code,
            'serviceable': is_serviceable,
            'service_type': service_type
        })
        
        return result
    
    def _is_in_coverage(self, state: str, zip_code: str) -> bool:
        """Check if location is in coverage area"""
        if state not in self.coverage_map:
            return False
        return zip_code in self.coverage_map[state]
    
    def _get_service_availability(self, zip_code: str) -> Dict[str, Any]:
        """Get available services for a zip code"""
        # Mock service availability
        # In production: query service catalog and network database
        
        base_services = [
            {
                "type": ServiceType.INTERNET.value,
                "name": "Business Internet",
                "speeds": ["100M", "500M", "1G", "10G"],
                "sla": "99.9%"
            },
            {
                "type": ServiceType.VOICE.value,
                "name": "Business Voice",
                "features": ["Unlimited calling", "Auto attendant", "Call forwarding"],
                "sla": "99.95%"
            }
        ]
        
        # Premium locations get additional services
        premium_zips = ["19102", "10001", "90001"]
        if zip_code in premium_zips:
            base_services.extend([
                {
                    "type": ServiceType.CLOUD.value,
                    "name": "Cloud Connect",
                    "speeds": ["1G", "10G", "100G"],
                    "sla": "99.99%"
                },
                {
                    "type": ServiceType.MANAGED_SERVICES.value,
                    "name": "Managed Network Services",
                    "features": ["24/7 monitoring", "Proactive maintenance"],
                    "sla": "99.99%"
                }
            ])
        
        return {"services": base_services}
    
    def _calculate_facility_distance(self, address: Dict[str, Any]) -> float:
        """Calculate distance to nearest facility (mock)"""
        # Mock calculation based on zip hash
        zip_hash = int(hashlib.md5(address.get('zip_code', '').encode()).hexdigest()[:8], 16)
        return 100 + (zip_hash % 2000)  # 100-2100 feet
    
    def _estimate_install_timeline(self, serviceable: bool) -> int:
        """Estimate installation timeline in days"""
        if not serviceable:
            return 0
        return random.randint(5, 14)  # 5-14 business days
    
    def _calculate_mrc(self, service_type: str, speed_tier: Optional[str]) -> float:
        """Calculate monthly recurring charge"""
        base_rates = {
            ServiceType.INTERNET.value: {
                "100M": 299.00,
                "500M": 499.00,
                "1G": 799.00,
                "10G": 1999.00
            },
            ServiceType.VOICE.value: 49.99,
            ServiceType.TV.value: 199.99,
            ServiceType.CLOUD.value: 999.00,
            ServiceType.MANAGED_SERVICES.value: 1499.00
        }
        
        if service_type == ServiceType.INTERNET.value and speed_tier:
            return base_rates[service_type].get(speed_tier, 799.00)
        
        return base_rates.get(service_type, 0.0)
    
    def _calculate_otc(self, installation_required: bool) -> Dict[str, float]:
        """Calculate one-time charges"""
        charges = {
            "activation_fee": 99.00
        }
        
        if installation_required:
            charges["installation_fee"] = 299.00
            charges["equipment_fee"] = 199.00
        
        return charges
    
    def _check_network_capacity(self, 
                               zip_code: str, 
                               bandwidth_required: float) -> Dict[str, Any]:
        """
        Check available network capacity
        
        In production, queries:
        - Network management system
        - Capacity planning database
        - Real-time port utilization
        
        Args:
            zip_code: Service location zip code
            bandwidth_required: Required bandwidth in Mbps
            
        Returns:
            Capacity availability result
        """
        self.logger.info(f"Checking network capacity for {zip_code}")
        
        # Mock capacity check
        # Simulate current utilization
        zip_hash = int(hashlib.md5(zip_code.encode()).hexdigest()[:8], 16)
        current_utilization_pct = 40 + (zip_hash % 40)  # 40-80% utilized
        
        total_capacity_gbps = 100  # 100 Gbps total capacity
        available_capacity_gbps = total_capacity_gbps * (100 - current_utilization_pct) / 100
        available_capacity_mbps = available_capacity_gbps * 1000
        
        sufficient_capacity = available_capacity_mbps >= bandwidth_required
        
        result = {
            "zip_code": zip_code,
            "bandwidth_required_mbps": bandwidth_required,
            "available_capacity_mbps": round(available_capacity_mbps, 2),
            "current_utilization_pct": current_utilization_pct,
            "sufficient_capacity": sufficient_capacity,
            "recommendation": self._get_capacity_recommendation(
                sufficient_capacity, 
                current_utilization_pct
            ),
            "checked_at": datetime.now().isoformat()
        }
        
        self.add_to_memory({
            'type': 'capacity_check',
            'zip_code': zip_code,
            'sufficient': sufficient_capacity
        })
        
        return result
    
    def _get_capacity_recommendation(self, 
                                    sufficient: bool, 
                                    utilization: float) -> str:
        """Get capacity recommendation"""
        if not sufficient:
            return "Insufficient capacity - network upgrade required"
        elif utilization > 75:
            return "Capacity available but high utilization - monitor closely"
        else:
            return "Sufficient capacity available"
    
    def _get_available_slots(self,
                            zip_code: str,
                            installation_type: str,
                            preferred_dates: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get available installation time slots
        
        In production, integrates with:
        - Field service management system
        - Technician scheduling system
        - Work order management
        
        Args:
            zip_code: Service location
            installation_type: Type of installation
            preferred_dates: Optional preferred dates
            
        Returns:
            Available time slots
        """
        self.logger.info(f"Getting available slots for {zip_code}")
        
        install_type = InstallationType[installation_type.upper()]
        duration_hours = self.installation_duration[install_type]
        
        # Generate available slots for next 14 days
        available_slots = []
        start_date = datetime.now() + timedelta(days=3)  # Earliest is 3 days out
        
        for day_offset in range(14):
            current_date = start_date + timedelta(days=day_offset)
            
            # Skip weekends for standard installations
            if current_date.weekday() >= 5 and install_type == InstallationType.STANDARD:
                continue
            
            # Generate time slots for the day
            day_slots = self._generate_day_slots(current_date, duration_hours, zip_code)
            available_slots.extend(day_slots)
        
        # Filter by preferred dates if provided
        if preferred_dates:
            preferred_dates_set = set(preferred_dates)
            available_slots = [
                slot for slot in available_slots
                if slot['date'] in preferred_dates_set
            ]
        
        result = {
            "zip_code": zip_code,
            "installation_type": installation_type,
            "available_slots": available_slots[:20],  # Return top 20 slots
            "total_available": len(available_slots),
            "earliest_available": available_slots[0] if available_slots else None,
            "retrieved_at": datetime.now().isoformat()
        }
        
        return result
    
    def _generate_day_slots(self, 
                          date: datetime, 
                          duration_hours: int,
                          zip_code: str) -> List[Dict[str, Any]]:
        """Generate available time slots for a specific day"""
        slots = []
        
        # Mock technician availability (in production: query scheduling system)
        zip_hash = int(hashlib.md5(zip_code.encode()).hexdigest()[:4], 16)
        available_techs = 2 + (zip_hash % 3)  # 2-4 technicians
        
        # Generate slots during business hours
        current_time = datetime.combine(date.date(), self.business_hours_start)
        end_time = datetime.combine(date.date(), self.business_hours_end)
        
        slot_num = 1
        while current_time + timedelta(hours=duration_hours) <= end_time:
            # Each slot can accommodate multiple technicians
            for tech_num in range(available_techs):
                slot_id = f"slot_{date.strftime('%Y%m%d')}_{slot_num:02d}_{tech_num}"
                
                slots.append({
                    "slot_id": slot_id,
                    "date": date.strftime('%Y-%m-%d'),
                    "start_time": current_time.strftime('%H:%M'),
                    "end_time": (current_time + timedelta(hours=duration_hours)).strftime('%H:%M'),
                    "duration_hours": duration_hours,
                    "technician_id": f"tech_{tech_num + 1}",
                    "available": True
                })
            
            current_time += timedelta(hours=2)  # 2-hour slot intervals
            slot_num += 1
        
        return slots
    
    def _schedule_installation(self,
                              order_id: str,
                              slot_id: str,
                              installation_type: str,
                              customer_contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Schedule installation appointment
        
        Args:
            order_id: Order identifier
            slot_id: Selected time slot ID
            installation_type: Type of installation
            customer_contact: Customer contact information
            
        Returns:
            Scheduling confirmation
        """
        self.logger.info(f"Scheduling installation for order {order_id}")
        
        # Validate slot is still available (mock)
        # In production: lock the slot in scheduling system
        
        appointment_id = f"appt_{hashlib.md5(f'{order_id}{slot_id}'.encode()).hexdigest()[:12]}"
        
        installation = {
            "appointment_id": appointment_id,
            "order_id": order_id,
            "slot_id": slot_id,
            "installation_type": installation_type,
            "customer_contact": customer_contact,
            "status": "scheduled",
            "scheduled_at": datetime.now().isoformat(),
            "confirmation_sent": True,
            "technician_assigned": True,
            "work_order_created": True
        }
        
        # Store in scheduled installations
        self.scheduled_installations[appointment_id] = installation
        
        result = {
            **installation,
            "confirmation_message": f"Installation scheduled successfully. Appointment ID: {appointment_id}",
            "pre_install_checklist": self._get_pre_install_checklist(installation_type)
        }
        
        self.add_to_memory({
            'type': 'installation_scheduled',
            'appointment_id': appointment_id,
            'order_id': order_id
        })
        
        return result
    
    def _get_pre_install_checklist(self, installation_type: str) -> List[str]:
        """Get pre-installation checklist"""
        base_checklist = [
            "Ensure access to equipment room/telecommunications closet",
            "Provide parking information for technician",
            "Designate on-site contact person"
        ]
        
        if installation_type != InstallationType.SELF_INSTALL.value:
            base_checklist.extend([
                "Clear path to equipment installation location",
                "Provide building access codes if applicable",
                "Review network diagram with IT team"
            ])
        
        return base_checklist
    
    def _provision_service(self,
                          order_id: str,
                          service_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provision and activate service
        
        In production, integrates with:
        - OSS/BSS systems
        - Network element managers
        - Service activation platform
        
        Args:
            order_id: Order identifier
            service_config: Service configuration parameters
            
        Returns:
            Provisioning result
        """
        self.logger.info(f"Provisioning service for order {order_id}")
        
        provisioning_id = f"prov_{hashlib.md5(f'{order_id}{datetime.now()}'.encode()).hexdigest()[:12]}"
        
        # Simulate provisioning steps
        provisioning_steps = [
            {"step": "validate_order", "status": "completed", "duration_sec": 2},
            {"step": "allocate_resources", "status": "completed", "duration_sec": 5},
            {"step": "configure_network_elements", "status": "completed", "duration_sec": 10},
            {"step": "activate_circuit", "status": "completed", "duration_sec": 8},
            {"step": "run_diagnostics", "status": "completed", "duration_sec": 15},
            {"step": "notify_customer", "status": "completed", "duration_sec": 1}
        ]
        
        # Calculate total provisioning time
        total_duration = sum(step['duration_sec'] for step in provisioning_steps)
        
        # Generate service credentials
        service_credentials = self._generate_service_credentials(service_config)
        
        provisioning_record = {
            "provisioning_id": provisioning_id,
            "order_id": order_id,
            "status": ProvisioningStatus.COMPLETED.value,
            "service_config": service_config,
            "provisioning_steps": provisioning_steps,
            "total_duration_sec": total_duration,
            "service_credentials": service_credentials,
            "circuit_id": f"CKT-{hashlib.md5(order_id.encode()).hexdigest()[:10].upper()}",
            "provisioned_at": datetime.now().isoformat(),
            "activation_date": datetime.now().isoformat()
        }
        
        # Add to provisioning queue
        self.provisioning_queue.append(provisioning_record)
        
        self.add_to_memory({
            'type': 'service_provisioned',
            'provisioning_id': provisioning_id,
            'order_id': order_id
        })
        
        return provisioning_record
    
    def _generate_service_credentials(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate service access credentials"""
        service_type = service_config.get('service_type')
        
        credentials = {
            "service_type": service_type,
            "generated_at": datetime.now().isoformat()
        }
        
        if service_type == ServiceType.INTERNET.value:
            credentials.update({
                "ip_address": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
                "subnet_mask": "255.255.255.0",
                "gateway": "10.0.0.1",
                "dns_primary": "8.8.8.8",
                "dns_secondary": "8.8.4.4"
            })
        elif service_type == ServiceType.VOICE.value:
            credentials.update({
                "phone_numbers": [f"+1-215-555-{random.randint(1000,9999)}" for _ in range(service_config.get('lines', 1))],
                "sip_domain": "voice.business.example.com",
                "sip_username": f"user{random.randint(10000,99999)}",
                "sip_password": hashlib.md5(str(random.random()).encode()).hexdigest()[:12]
            })
        
        return credentials
    
    def _check_provision_status(self, order_id: str) -> Dict[str, Any]:
        """
        Check provisioning status
        
        Args:
            order_id: Order identifier
            
        Returns:
            Current provisioning status
        """
        self.logger.info(f"Checking provision status for order {order_id}")
        
        # Search provisioning queue
        provision_record = next(
            (p for p in self.provisioning_queue if p['order_id'] == order_id),
            None
        )
        
        if not provision_record:
            return {
                "order_id": order_id,
                "status": ProvisioningStatus.PENDING.value,
                "message": "Order not yet in provisioning queue"
            }
        
        return {
            "order_id": order_id,
            "provisioning_id": provision_record['provisioning_id'],
            "status": provision_record['status'],
            "circuit_id": provision_record.get('circuit_id'),
            "provisioned_at": provision_record.get('provisioned_at'),
            "last_updated": datetime.now().isoformat()
        }
    
    # ==================== AGENT PROCESSING ====================
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method for Service Fulfillment Agent
        
        Args:
            input_data: Contains action and relevant parameters
            
        Returns:
            Processing result
        """
        self.update_status(AgentStatus.PROCESSING)
        
        action = input_data.get('action')
        self.logger.info(f"Processing action: {action}")
        
        try:
            if action == 'full_fulfillment_flow':
                result = await self._full_fulfillment_flow(input_data)
            elif action == 'check_serviceability':
                result = self.execute_tool('check_serviceability', **input_data.get('params', {}))
            elif action == 'check_capacity':
                result = self.execute_tool('check_network_capacity', **input_data.get('params', {}))
            elif action == 'get_slots':
                result = self.execute_tool('get_available_slots', **input_data.get('params', {}))
            elif action == 'schedule':
                result = self.execute_tool('schedule_installation', **input_data.get('params', {}))
            elif action == 'provision':
                result = self.execute_tool('provision_service', **input_data.get('params', {}))
            elif action == 'check_status':
                result = self.execute_tool('check_provision_status', **input_data.get('params', {}))
            else:
                result = {
                    'status': 'error',
                    'error': f'Unknown action: {action}'
                }
            
            self.update_status(AgentStatus.COMPLETED)
            return result
            
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            self.update_status(AgentStatus.ERROR)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _full_fulfillment_flow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete fulfillment flow
        
        Args:
            input_data: Complete order information
            
        Returns:
            Full fulfillment result
        """
        flow_result = {
            'flow': 'complete_service_fulfillment',
            'steps': [],
            'overall_status': 'pending'
        }
        
        # Step 1: Serviceability Check
        serviceability = self.execute_tool(
            'check_serviceability',
            address=input_data.get('address'),
            service_type=input_data.get('service_type'),
            speed_tier=input_data.get('speed_tier')
        )
        flow_result['steps'].append({
            'step': 'serviceability_check',
            'result': serviceability
        })
        
        if not serviceability.get('result', {}).get('serviceable'):
            flow_result['overall_status'] = 'not_serviceable'
            flow_result['reason'] = 'Service not available at this location'
            return flow_result
        
        # Step 2: Network Capacity Check
        capacity = self.execute_tool(
            'check_network_capacity',
            zip_code=input_data.get('address', {}).get('zip_code'),
            bandwidth_required=self._parse_bandwidth(input_data.get('speed_tier', '1G'))
        )
        flow_result['steps'].append({
            'step': 'capacity_check',
            'result': capacity
        })
        
        if not capacity.get('result', {}).get('sufficient_capacity'):
            flow_result['overall_status'] = 'insufficient_capacity'
            flow_result['reason'] = 'Insufficient network capacity'
            return flow_result
        
        # Step 3: Get Available Installation Slots
        slots = self.execute_tool(
            'get_available_slots',
            zip_code=input_data.get('address', {}).get('zip_code'),
            installation_type=input_data.get('installation_type', 'standard'),
            preferred_dates=input_data.get('preferred_dates')
        )
        flow_result['steps'].append({
            'step': 'slot_availability',
            'result': slots
        })
        
        flow_result['overall_status'] = 'ready_for_scheduling'
        flow_result['next_steps'] = [
            "Customer should select installation slot",
            "Schedule installation appointment",
            "Provision service after installation"
        ]
        
        return flow_result
    
    def _parse_bandwidth(self, speed_tier: str) -> float:
        """Parse bandwidth from speed tier string"""
        # Convert speed tier like "1G", "10G", "100M" to Mbps
        if 'G' in speed_tier.upper():
            return float(speed_tier.upper().replace('G', '')) * 1000
        elif 'M' in speed_tier.upper():
            return float(speed_tier.upper().replace('M', ''))
        return 1000.0  # Default 1 Gbps
    
    async def _handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle A2A messages from other agents
        
        Args:
            message: Incoming message from another agent
            
        Returns:
            Response to the message
        """
        content = message.content
        message_type = content.get('type')
        
        if message_type == 'serviceability_inquiry':
            # Prospect Agent asking about service availability
            return await self._handle_serviceability_inquiry(content)
        
        elif message_type == 'schedule_request':
            # Order Agent requesting installation scheduling
            return await self._handle_schedule_request(content)
        
        elif message_type == 'provision_request':
            # Order Agent requesting service provisioning
            return await self._handle_provision_request(content)
        
        elif message_type == 'status_inquiry':
            # Any agent checking order status
            return await self._handle_status_inquiry(content)
        
        else:
            return {
                'status': 'error',
                'error': f'Unknown message type: {message_type}'
            }
    
    async def _handle_serviceability_inquiry(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle serviceability inquiry from another agent"""
        serviceability = self.execute_tool(
            'check_serviceability',
            address=content.get('address'),
            service_type=content.get('service_type'),
            speed_tier=content.get('speed_tier')
        )
        
        return {
            'type': 'serviceability_response',
            'serviceable': serviceability['result']['serviceable'],
            'status': serviceability['result']['status'],
            'available_services': serviceability['result']['available_services'],
            'installation_timeline': serviceability['result']['estimated_install_days']
        }
    
    async def _handle_schedule_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle installation scheduling request"""
        result = self.execute_tool(
            'schedule_installation',
            order_id=content.get('order_id'),
            slot_id=content.get('slot_id'),
            installation_type=content.get('installation_type'),
            customer_contact=content.get('customer_contact')
        )
        
        return {
            'type': 'schedule_response',
            'status': 'scheduled',
            'appointment_id': result['result']['appointment_id'],
            'details': result['result']
        }
    
    async def _handle_provision_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle provisioning request from Order Agent"""
        result = self.execute_tool(
            'provision_service',
            order_id=content.get('order_id'),
            service_config=content.get('service_config')
        )
        
        return {
            'type': 'provision_response',
            'status': result['result']['status'],
            'provisioning_id': result['result']['provisioning_id'],
            'circuit_id': result['result']['circuit_id'],
            'credentials': result['result']['service_credentials']
        }
    
    async def _handle_status_inquiry(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status inquiry"""
        result = self.execute_tool(
            'check_provision_status',
            order_id=content.get('order_id')
        )
        
        return {
            'type': 'status_response',
            'order_id': content.get('order_id'),
            'status': result['result']['status'],
            'details': result['result']
        }
