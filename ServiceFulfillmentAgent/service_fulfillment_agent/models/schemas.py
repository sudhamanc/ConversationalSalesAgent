"""
Pydantic models for service fulfillment operations.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class OrderStatusType(str, Enum):
    """Order status types"""
    RECEIVED = "received"
    SCHEDULED = "scheduled"
    EQUIPMENT_ORDERED = "equipment_ordered"
    EQUIPMENT_DELIVERED = "equipment_delivered"
    TECHNICIAN_DISPATCHED = "technician_dispatched"
    IN_PROGRESS = "in_progress"
    SERVICE_ACTIVE = "service_active"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class AppointmentWindow(str, Enum):
    """Installation appointment windows"""
    AM = "AM"  # 8AM-12PM
    PM = "PM"  # 1PM-5PM
    ALL_DAY = "all_day"  # 8AM-5PM


class EquipmentType(str, Enum):
    """Types of equipment"""
    ROUTER = "router"
    ONT = "ont"
    SWITCH = "switch"
    PHONE = "phone"
    UPS = "ups"
    MODEM = "modem"


class InstallationStatusType(str, Enum):
    """Installation progress status"""
    SCHEDULED = "scheduled"
    TECHNICIAN_EN_ROUTE = "technician_en_route"
    ON_SITE = "on_site"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    COMPLETE = "complete"
    FAILED = "failed"


class Address(BaseModel):
    """Service address"""
    street: str
    city: str
    state: str
    zip_code: str
    unit: Optional[str] = None
    
    def to_string(self) -> str:
        """Returns formatted address string"""
        base = f"{self.street}, {self.city}, {self.state} {self.zip_code}"
        return f"{base} Unit {self.unit}" if self.unit else base


class Order(BaseModel):
    """Service fulfillment order"""
    order_id: str = Field(..., description="Unique order identifier")
    customer_name: str
    customer_id: str
    service_address: Address
    service_type: str = Field(..., description="Type of service being installed")
    status: OrderStatusType = Field(default=OrderStatusType.RECEIVED)
    created_at: datetime = Field(default_factory=datetime.now)
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "ORD-20260213-001",
                "customer_name": "ABC Corporation",
                "customer_id": "CUST-12345",
                "service_type": "Business Fiber 1 Gbps",
                "status": "scheduled"
            }
        }


class Appointment(BaseModel):
    """Installation appointment"""
    appointment_id: str = Field(..., description="Unique appointment identifier")
    order_id: str = Field(..., description="Associated order ID")
    scheduled_date: datetime
    window: AppointmentWindow = Field(default=AppointmentWindow.AM)
    technician_id: Optional[str] = None
    customer_contact: str = Field(..., description="On-site contact name")
    customer_phone: str
    special_instructions: Optional[str] = None
    status: str = Field(default="scheduled")
    
    class Config:
        json_schema_extra = {
            "example": {
                "appointment_id": "APT-20260218-001",
                "order_id": "ORD-20260213-001",
                "scheduled_date": "2026-02-18T08:00:00",
                "window": "AM",
                "customer_contact": "John Smith",
                "customer_phone": "555-0123"
            }
        }


class Equipment(BaseModel):
    """Equipment item"""
    equipment_id: str
    equipment_type: EquipmentType
    model: str
    serial_number: Optional[str] = None
    tracking_number: Optional[str] = None
    status: str = Field(default="ordered")
    estimated_delivery: Optional[datetime] = None
    delivered_date: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "equipment_id": "EQ-001",
                "equipment_type": "router",
                "model": "XR-1000",
                "tracking_number": "TRACK-123456",
                "status": "in_transit",
                "estimated_delivery": "2026-02-16T17:00:00"
            }
        }


class InstallationStatus(BaseModel):
    """Installation progress tracking"""
    appointment_id: str
    order_id: str
    status: InstallationStatusType
    technician_id: Optional[str] = None
    technician_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    issues: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "appointment_id": "APT-20260218-001",
                "order_id": "ORD-20260213-001",
                "status": "in_progress",
                "technician_id": "TECH-456",
                "technician_name": "Mike Johnson",
                "started_at": "2026-02-18T08:15:00"
            }
        }


class ServiceActivation(BaseModel):
    """Service activation record"""
    activation_id: str
    order_id: str
    service_type: str
    circuit_id: str
    ip_address: Optional[str] = None
    gateway: Optional[str] = None
    speed_test_down: Optional[float] = None  # Mbps
    speed_test_up: Optional[float] = None  # Mbps
    latency_ms: Optional[float] = None
    packet_loss_percent: Optional[float] = None
    activated_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(default="active")
    
    class Config:
        json_schema_extra = {
            "example": {
                "activation_id": "ACT-001",
                "order_id": "ORD-20260213-001",
                "service_type": "Business Fiber 1 Gbps",
                "circuit_id": "CKT-PHI-12345",
                "ip_address": "203.0.113.45",
                "speed_test_down": 950.0,
                "speed_test_up": 940.0,
                "latency_ms": 8.0,
                "packet_loss_percent": 0.0,
                "status": "active"
            }
        }


class TechnicianDispatch(BaseModel):
    """Technician dispatch record"""
    dispatch_id: str
    appointment_id: str
    technician_id: str
    technician_name: str
    technician_phone: str
    vehicle_id: Optional[str] = None
    dispatched_at: datetime = Field(default_factory=datetime.now)
    eta: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    status: str = Field(default="dispatched")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dispatch_id": "DISP-001",
                "appointment_id": "APT-20260218-001",
                "technician_id": "TECH-456",
                "technician_name": "Mike Johnson",
                "technician_phone": "555-TECH",
                "eta": "2026-02-18T08:00:00",
                "status": "dispatched"
            }
        }


class TimeSlot(BaseModel):
    """Available installation time slot"""
    date: datetime
    window: AppointmentWindow
    available: bool = Field(default=True)
    technician_count: int = Field(default=1, description="Number of available technicians")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-02-18T08:00:00",
                "window": "AM",
                "available": True,
                "technician_count": 3
            }
        }
