"""Optional upstream GIS / coverage-map API client (``USE_MOCK_DATA=false``).

Contract assumed for the upstream (unchanged from the legacy agent)::

    POST {GIS_API_URL}/serviceability/check
    Authorization: Bearer {GIS_API_KEY}
    {"street", "city", "state", "zip_code"}
    -> {"available": bool, "technology", "zone", "install_days",
        "infrastructure": {...}, "available_products": [...], "reason"}

Results are cached in memory for ``GIS_CACHE_TTL_SECONDS`` (default 24 h).
The API key is never logged.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

import httpx

from sales_common.config import env_float, env_int, env_str

from .models import Address, ServiceabilityResult, product_categories

logger = logging.getLogger("serviceability.gis_client")

UNAVAILABLE_REASON = "Unable to verify serviceability at this time. Please contact our sales team."
TIMEOUT_REASON = "Service check timed out. Please try again or contact our sales team."

_cache: dict[str, tuple[float, ServiceabilityResult]] = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _cache_key(address: Address) -> str:
    return f"{address.zip_code}:{address.street.lower()}"


def _cache_get(key: str) -> Optional[ServiceabilityResult]:
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry[0] > time.monotonic():
            return entry[1]
        _cache.pop(key, None)
    return None


def _cache_put(key: str, result: ServiceabilityResult) -> None:
    ttl = env_int("GIS_CACHE_TTL_SECONDS", 86_400)
    if ttl > 0:
        with _cache_lock:
            _cache[key] = (time.monotonic() + ttl, result)


def _unserviceable(address: Address, reason: str) -> ServiceabilityResult:
    return ServiceabilityResult(serviceable=False, address=address, reason=reason)


def translate(address: Address, data: dict[str, Any]) -> ServiceabilityResult:
    """Map an upstream response onto :class:`ServiceabilityResult`."""
    if not data.get("available"):
        return _unserviceable(address, data.get("reason") or "Service not available at this location")
    infrastructure = data.get("infrastructure") or {}
    speed = (infrastructure.get("speed_capability") or {}).get("max_speed_mbps")
    technology = data.get("technology")
    return ServiceabilityResult(
        serviceable=True,
        address=address,
        infrastructure=infrastructure or None,
        infrastructure_type=technology,
        max_speed_mbps=speed,
        service_zone=data.get("zone"),
        estimated_install_days=data.get("install_days"),
        available_product_categories=product_categories(technology),
        available_products=list(data.get("available_products") or []),
    )


def check(address: Address, client: Optional[httpx.Client] = None) -> ServiceabilityResult:
    """Ask the upstream GIS API; failures become an unserviceable result with a reason."""
    key = _cache_key(address)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    api_url = env_str("GIS_API_URL", "")
    api_key = env_str("GIS_API_KEY", "")
    if not api_url or not api_key:
        logger.error("GIS_API_URL / GIS_API_KEY not configured while USE_MOCK_DATA=false")
        return _unserviceable(address, UNAVAILABLE_REASON)

    try:
        http = client or httpx.Client(timeout=env_float("GIS_TIMEOUT_SECONDS", 10.0))
        try:
            response = http.post(
                f"{api_url.rstrip('/')}/serviceability/check",
                headers={"Authorization": f"Bearer {api_key}"},
                json=address.model_dump(),
            )
        finally:
            if client is None:
                http.close()
        response.raise_for_status()
        result = translate(address, response.json())
    except httpx.TimeoutException:
        logger.error("GIS API timeout")
        return _unserviceable(address, TIMEOUT_REASON)
    except (httpx.HTTPError, ValueError) as exc:
        # Never include request headers (API key) in logs.
        logger.error("GIS API error: %s", type(exc).__name__)
        return _unserviceable(address, UNAVAILABLE_REASON)

    _cache_put(key, result)
    return result
