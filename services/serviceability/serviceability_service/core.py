"""Serviceability business logic shared by the REST API and the MCP tools.

Moved from ``ServiceabilityAgent/serviceability_agent/tools/gis_tools.py``.
The legacy ``MOCK_COVERAGE_DATA`` now lives in PostgreSQL (``coverage_zones``,
seeded by ``scripts/export_coverage_seed.py``).

* ``USE_MOCK_DATA=true`` (default): coverage comes from ``coverage_zones``.
* ``USE_MOCK_DATA=false``: coverage comes from the upstream GIS API
  (:mod:`serviceability_service.gis_client`).

Every function takes plain arguments and returns a pydantic model; callers
serialize with :func:`serviceability_service.models.dump`.
"""

from __future__ import annotations

import logging

from sales_common.config import env_bool

from . import gis_client, repository
from .address import extract_zip_code, normalize_address, validate_and_parse_address
from .models import (
    Address,
    CoverageZonesResult,
    InfrastructureCapability,
    InfrastructureResult,
    ServiceabilityResult,
    product_categories,
)

logger = logging.getLogger("serviceability.core")

__all__ = [
    "INFRASTRUCTURE_DEFAULTS",
    "check_service_availability",
    "extract_zip_code",
    "get_coverage_zones",
    "get_infrastructure_by_technology",
    "normalize_address",
    "product_categories",
    "use_mock_data",
    "validate_and_parse_address",
]

NOT_IN_COVERAGE_REASON = "No infrastructure at location. We're constantly expanding our network."
NOT_SERVICEABLE_REASON = "Service not available at this location"

#: Infrastructure capabilities by technology (reference data, not zone-specific).
INFRASTRUCTURE_DEFAULTS: dict[str, InfrastructureCapability] = {
    "FTTP": InfrastructureCapability(
        technology="Fiber to the Premises (FTTP)",
        min_speed_mbps=100,
        max_speed_mbps=10000,
        symmetrical=True,
        service_classes=["Enterprise", "Business"],
        typical_equipment=["OLT", "ONT", "Fiber Optic Cable"],
        redundancy_capable=True,
    ),
    "HFC": InfrastructureCapability(
        technology="Hybrid Fiber-Coax (HFC)",
        min_speed_mbps=50,
        max_speed_mbps=1000,
        symmetrical=False,
        service_classes=["Business", "Standard"],
        typical_equipment=["CMTS", "Cable Modem", "Coax Cable"],
        redundancy_capable=False,
    ),
    "DOCSIS 3.1": InfrastructureCapability(
        technology="DOCSIS 3.1",
        min_speed_mbps=100,
        max_speed_mbps=1000,
        symmetrical=False,
        service_classes=["Business", "Standard"],
        typical_equipment=["CMTS", "DOCSIS 3.1 Modem", "Coax Cable"],
        redundancy_capable=False,
    ),
}

TECHNOLOGY_ALIASES = {"FIBER": "FTTP", "COAX": "HFC", "DOCSIS": "DOCSIS 3.1"}


def use_mock_data() -> bool:
    """``USE_MOCK_DATA`` (default true): read coverage from PostgreSQL, not the GIS API."""
    return env_bool("USE_MOCK_DATA", True)


def _lookup_coverage(address: Address) -> ServiceabilityResult:
    row = repository.get_coverage(address.zip_code)
    if row is None:
        logger.info("ZIP %s not in coverage", address.zip_code)
        return ServiceabilityResult(serviceable=False, address=address, reason=NOT_IN_COVERAGE_REASON)
    if not row["serviceable"]:
        return ServiceabilityResult(
            serviceable=False, address=address, reason=row["reason"] or NOT_SERVICEABLE_REASON
        )
    return ServiceabilityResult(
        serviceable=True,
        address=address,
        infrastructure=row["infrastructure"],
        infrastructure_type=row["infrastructure_type"],
        max_speed_mbps=row["max_speed_mbps"],
        service_zone=row["service_zone"],
        estimated_install_days=row["estimated_install_days"],
        available_product_categories=list(row["available_product_categories"] or []),
        available_products=list(row["available_products"] or []),
    )


def check_service_availability(address: Address) -> ServiceabilityResult:
    """Coverage decision for a validated address (never invents data)."""
    result = _lookup_coverage(address) if use_mock_data() else gis_client.check(address)
    logger.info(
        "Serviceability zip=%s serviceable=%s type=%s products=%d",
        address.zip_code, result.serviceable, result.infrastructure_type, len(result.available_products),
    )
    return result


def canonical_technology(technology: str) -> str:
    key = technology.strip().upper()
    return TECHNOLOGY_ALIASES.get(key, key)


def get_infrastructure_by_technology(technology: str, zone: str = "all") -> InfrastructureResult:
    """Capabilities for ``technology`` (FTTP/Fiber, HFC/Coax, DOCSIS 3.1/DOCSIS).

    ``zone`` is accepted for compatibility and ignored: no per-zone data exists.
    Unknown technologies return an empty ``infrastructure`` list.
    """
    key = canonical_technology(technology)
    capability = INFRASTRUCTURE_DEFAULTS.get(key)
    return InfrastructureResult(
        technology=key, zone=zone or "all", infrastructure=[capability] if capability else []
    )


def get_coverage_zones() -> CoverageZonesResult:
    """All service zones with at least one serviceable ZIP code, sorted."""
    zones = repository.list_service_zones()
    return CoverageZonesResult(zones=zones, count=len(zones))
