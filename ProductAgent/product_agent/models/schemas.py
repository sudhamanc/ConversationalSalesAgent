"""
Pydantic models for product specifications and queries.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ProductFeature(BaseModel):
    """Individual product feature"""
    name: str = Field(..., description="Feature name")
    description: str = Field(..., description="Feature description")
    included: bool = Field(default=True, description="Whether feature is included by default")
    additional_cost: Optional[str] = Field(None, description="Additional cost if not included")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Static IP Address",
                "description": "Dedicated static IP address for your business",
                "included": False,
                "additional_cost": "$15/month"
            }
        }


class HardwareSpec(BaseModel):
    """Hardware specifications"""
    model: str = Field(..., description="Hardware model name")
    type: str = Field(..., description="Hardware type (router, modem, etc.)")
    specifications: Dict[str, str] = Field(..., description="Technical specifications")
    included: bool = Field(default=True, description="Whether included in service")
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "Business Gateway 3000",
                "type": "Router/Modem Combo",
                "specifications": {
                    "WiFi": "WiFi 6 (802.11ax)",
                    "Ports": "4x Gigabit Ethernet",
                    "Security": "WPA3 encryption"
                },
                "included": True
            }
        }


class ServiceLevelAgreement(BaseModel):
    """Service Level Agreement details"""
    uptime_guarantee: str = Field(..., description="Uptime percentage guarantee")
    support_level: str = Field(..., description="Support level (Basic, Premium, Enterprise)")
    response_time: str = Field(..., description="Support response time")
    credits_policy: Optional[str] = Field(None, description="Service credit policy")
    
    class Config:
        json_schema_extra = {
            "example": {
                "uptime_guarantee": "99.9%",
                "support_level": "Premium",
                "response_time": "2 hours",
                "credits_policy": "Pro-rated credits for downtime > 0.1%"
            }
        }


class ProductSpec(BaseModel):
    """Complete product specification"""
    product_id: str = Field(..., description="Unique product identifier")
    product_name: str = Field(..., description="Human-readable product name")
    technology: str = Field(..., description="Technology type: FTTP, HFC, DOCSIS")
    speeds: Dict[str, str] = Field(..., description="Speed specifications")
    price: str = Field(..., description="Monthly price")
    features: List[ProductFeature] = Field(default_factory=list, description="Product features")
    hardware: Optional[HardwareSpec] = Field(None, description="Included hardware")
    sla: Optional[ServiceLevelAgreement] = Field(None, description="Service level agreement")
    description: str = Field(..., description="Product description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "FIB-5G",
                "product_name": "Business Fiber 5 Gbps",
                "technology": "FTTP",
                "speeds": {
                    "download": "5 Gbps",
                    "upload": "5 Gbps"
                },
                "price": "$599/month",
                "description": "High-speed fiber internet for demanding businesses",
                "features": [],
                "hardware": None,
                "sla": None
            }
        }


class ProductQuery(BaseModel):
    """Query for product information"""
    question: str = Field(..., description="User's question about products")
    product_id: Optional[str] = Field(None, description="Optional specific product ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the upload speed of Fiber 5G?",
                "product_id": "FIB-5G",
                "context": {}
            }
        }


class ProductComparison(BaseModel):
    """Product comparison request"""
    product_ids: List[str] = Field(..., description="List of product IDs to compare")
    comparison_criteria: Optional[List[str]] = Field(
        None, 
        description="Specific criteria to compare (speed, price, features, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_ids": ["FIB-1G", "FIB-5G", "FIB-10G"],
                "comparison_criteria": ["speed", "price", "sla"]
            }
        }


class RAGQueryResult(BaseModel):
    """Result from RAG query"""
    answer: str = Field(..., description="Answer to the query")
    sources: List[str] = Field(default_factory=list, description="Source documents used")
    confidence: float = Field(..., description="Confidence score (0-1)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "The Business Fiber 5G provides 5 Gbps symmetrical speeds...",
                "sources": ["fiber_5g_spec.pdf", "business_internet_guide.pdf"],
                "confidence": 0.95,
                "metadata": {"product_id": "FIB-5G"}
            }
        }


class ProductCatalogItem(BaseModel):
    """Simplified product catalog entry"""
    product_id: str = Field(..., description="Product identifier")
    product_name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    technology: str = Field(..., description="Technology type")
    base_price: str = Field(..., description="Starting price")
    available: bool = Field(default=True, description="Availability status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "FIB-5G",
                "product_name": "Business Fiber 5 Gbps",
                "category": "Fiber Internet",
                "technology": "FTTP",
                "base_price": "$599/month",
                "available": True
            }
        }
