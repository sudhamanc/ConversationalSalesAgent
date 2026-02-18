"""
Pydantic models for address validation and serviceability responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class Address(BaseModel):
    """Structured address input"""
    street: str = Field(..., description="Street address with number")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="2-letter state code")
    zip_code: str = Field(..., description="5-digit ZIP code")
    
    def to_normalized_string(self) -> str:
        """Returns normalized address for API calls"""
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"
    
    class Config:
        json_schema_extra = {
            "example": {
                "street": "123 Market Street",
                "city": "Philadelphia",
                "state": "PA",
                "zip_code": "19107"
            }
        }


class NetworkElement(BaseModel):
    """Network infrastructure element details"""
    switch_id: Optional[str] = Field(None, description="Switch/Node identifier")
    switch_location: Optional[str] = Field(None, description="Physical switch location")
    cabinet_id: Optional[str] = Field(None, description="Cabinet identifier")
    fiber_pairs_available: Optional[int] = Field(None, description="Available fiber pairs")
    cable_pairs_available: Optional[int] = Field(None, description="Available cable pairs")
    splice_point: Optional[str] = Field(None, description="Splice point identifier")
    olt_chassis: Optional[str] = Field(None, description="OLT chassis identifier")
    olt_port: Optional[str] = Field(None, description="OLT port assignment")
    node_id: Optional[str] = Field(None, description="Node identifier for HFC")
    cmts_id: Optional[str] = Field(None, description="CMTS identifier")
    cmts_port: Optional[str] = Field(None, description="CMTS port")
    
    class Config:
        json_schema_extra = {
            "example": {
                "switch_id": "PHI-SW-001",
                "cabinet_id": "PHI-CAB-015",
                "fiber_pairs_available": 48,
                "olt_chassis": "CISCO-ASR9K-001"
            }
        }


class SpeedCapability(BaseModel):
    """Speed capability for the location"""
    min_speed_mbps: int = Field(..., description="Minimum supported speed in Mbps")
    max_speed_mbps: int = Field(..., description="Maximum supported speed in Mbps")
    symmetrical: bool = Field(..., description="Whether speeds are symmetrical (same up/down)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "min_speed_mbps": 100,
                "max_speed_mbps": 10000,
                "symmetrical": True
            }
        }


class InfrastructureDetails(BaseModel):
    """Infrastructure availability at location"""
    type: str = Field(..., description="Infrastructure type: Fiber, Coax/HFC, Coax/DOCSIS 3.1")
    network_element: NetworkElement = Field(..., description="Network element details")
    speed_capability: SpeedCapability = Field(..., description="Speed capabilities")
    service_class: str = Field(..., description="Service class: Enterprise, Business, Standard")
    redundancy_available: bool = Field(..., description="Whether redundant paths available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "Fiber",
                "network_element": {
                    "switch_id": "PHI-SW-001",
                    "fiber_pairs_available": 48
                },
                "speed_capability": {
                    "min_speed_mbps": 100,
                    "max_speed_mbps": 10000,
                    "symmetrical": True
                },
                "service_class": "Enterprise",
                "redundancy_available": True
            }
        }


class ServiceabilityResult(BaseModel):
    """Response from serviceability check"""
    serviceable: bool = Field(..., description="Whether address can receive service")
    address: Address = Field(..., description="Validated address")
    infrastructure: Optional[InfrastructureDetails] = Field(None, description="Infrastructure details at location")
    service_zone: Optional[str] = Field(None, description="Service zone identifier")
    reason: Optional[str] = Field(None, description="Reason if not serviceable")
    estimated_install_days: Optional[int] = Field(None, description="Installation timeline in days")
    infrastructure_type: Optional[str] = Field(None, description="Infrastructure type: FTTP, HFC, DOCSIS 3.1")
    
    class Config:
        json_schema_extra = {
            "example": {
                "serviceable": True,
                "address": {
                    "street": "123 Market Street",
                    "city": "Philadelphia",
                    "state": "PA",
                    "zip_code": "19107"
                },
                "infrastructure": {
                    "type": "Fiber",
                    "network_element": {
                        "switch_id": "PHI-SW-001",
                        "fiber_pairs_available": 48
                    },
                    "speed_capability": {
                        "min_speed_mbps": 100,
                        "max_speed_mbps": 10000,
                        "symmetrical": True
                    },
                    "service_class": "Enterprise",
                    "redundancy_available": True
                },
                "service_zone": "Metro-East-PA",
                "estimated_install_days": 5,
                "infrastructure_type": "FTTP"
            }
        }


class GISAPIResponse(BaseModel):
    """Raw response from GIS API (for future integration)"""
    status: str = Field(..., description="API response status")
    coverage_available: bool = Field(..., description="Coverage availability flag")
    technology_type: str = Field(..., description="Infrastructure technology type")
    available_services: List[dict] = Field(default_factory=list, description="Available service list")
    zone_id: str = Field(..., description="Geographic zone identifier")
    error_message: Optional[str] = Field(None, description="Error message if any")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "coverage_available": True,
                "technology_type": "FTTP",
                "available_services": [{"service_id": "fiber_1g", "name": "Fiber 1G"}],
                "zone_id": "PA-PHI-001"
            }
        }
