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


class Product(BaseModel):
    """Available product at location"""
    product_id: str = Field(..., description="Unique product identifier")
    product_name: str = Field(..., description="Human-readable product name")
    technology: str = Field(..., description="Technology type: Fiber, Coax, HFC")
    speeds: List[str] = Field(..., description="Available speed tiers")
    available: bool = Field(default=True, description="Product availability status")
    price: Optional[str] = Field(None, description="Monthly price if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "FIB-1G",
                "product_name": "Business Fiber 1 Gbps",
                "technology": "FTTP",
                "speeds": ["1 Gbps"],
                "available": True,
                "price": "$249/mo"
            }
        }


class ServiceabilityResult(BaseModel):
    """Response from serviceability check"""
    serviceable: bool = Field(..., description="Whether address can receive service")
    address: Address = Field(..., description="Validated address")
    available_products: List[Product] = Field(default_factory=list, description="Products available at location")
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
                "available_products": [
                    {
                        "product_id": "FIB-1G",
                        "product_name": "Business Fiber 1 Gbps",
                        "technology": "FTTP",
                        "speeds": ["1 Gbps"],
                        "available": True
                    }
                ],
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
