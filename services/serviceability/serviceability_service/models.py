"""Pydantic request/response models shared by the REST API and the MCP tools."""

from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

US_STATE_CODES = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
})

_ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class AddressValidateRequest(BaseModel):
    """Body of ``POST /api/v1/addresses/validate``."""

    model_config = ConfigDict(extra="forbid")

    address: str = Field(..., min_length=1, max_length=500, description="Raw address text")

    @field_validator("address")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("address must not be blank")
        return value


class Address(BaseModel):
    """Structured US street address (also the body of normalize/check requests)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "street": "123 Market Street",
                "city": "Philadelphia",
                "state": "PA",
                "zip_code": "19107",
            }
        },
    )

    street: str = Field(..., min_length=1, max_length=200, description="Street address with number")
    city: str = Field(..., min_length=1, max_length=100, description="City name")
    state: str = Field(..., description="2-letter US state code")
    zip_code: str = Field(..., description="5-digit ZIP code (ZIP+4 accepted, truncated)")

    @field_validator("street", "city")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        code = value.strip().upper()
        if code not in US_STATE_CODES:
            raise ValueError(f"{value!r} is not a US state code (e.g. PA, CA, NY)")
        return code

    @field_validator("zip_code")
    @classmethod
    def _zip(cls, value: str) -> str:
        value = value.strip()
        if not _ZIP_RE.match(value):
            raise ValueError(f"{value!r} is not a 5-digit ZIP code")
        return value[:5]

    def one_line(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class AddressValidationResult(BaseModel):
    """Result of parsing a raw address string. ``valid=false`` carries ``error``."""

    valid: bool
    address: Optional[Address] = None
    error: Optional[str] = None


class NormalizedAddress(BaseModel):
    normalized_address: str


class ZipCodeResult(BaseModel):
    zip_code: str = Field("", description="5-digit ZIP code, or empty when none found")


class ServiceabilityResult(BaseModel):
    """Coverage decision for one address.

    Serviceable results carry infrastructure details, speeds, the service zone,
    install lead time, product categories and the SKU ids sold at the address.
    Unserviceable results carry ``reason`` and empty product lists.
    """

    serviceable: bool
    address: Address
    infrastructure: Optional[dict[str, Any]] = None
    infrastructure_type: Optional[str] = None
    max_speed_mbps: Optional[int] = None
    service_zone: Optional[str] = None
    estimated_install_days: Optional[int] = None
    available_product_categories: list[str] = Field(default_factory=list)
    available_products: list[str] = Field(default_factory=list)
    reason: Optional[str] = None


class InfrastructureCapability(BaseModel):
    technology: str
    min_speed_mbps: int
    max_speed_mbps: int
    symmetrical: bool
    service_classes: list[str]
    typical_equipment: list[str]
    redundancy_capable: bool


class InfrastructureResult(BaseModel):
    """Capabilities for one technology (empty ``infrastructure`` when unknown)."""

    technology: str = Field(..., description="Canonical technology key, e.g. FTTP")
    zone: str = Field("all", description="Accepted for compatibility; capabilities are not zone-specific")
    infrastructure: list[InfrastructureCapability] = Field(default_factory=list)


class CoverageZonesResult(BaseModel):
    zones: list[str]
    count: int


#: Technologies that carry an internet product.
INTERNET_TECHNOLOGIES = frozenset({"FTTP", "HFC", "DOCSIS 3.1"})


def product_categories(technology: Optional[str]) -> list[str]:
    """Product categories sold on a technology (Voice/SD-WAN/Mobile ride any access)."""
    categories = ["Internet"] if technology in INTERNET_TECHNOLOGIES else []
    return categories + ["Voice", "SD-WAN", "Mobile"]


def dump(model: BaseModel) -> dict[str, Any]:
    """Canonical JSON dump used by both REST and MCP (``None`` fields omitted)."""
    return model.model_dump(mode="json", exclude_none=True)
