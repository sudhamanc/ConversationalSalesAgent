"""MCP server (streamable HTTP, stateless, JSON responses) mounted at ``/mcp/``.

Tool names and docstrings are the legacy serviceability agent tool names, so
agent prompts keep working. Each tool is a thin wrapper over :mod:`core` and
returns the same JSON object as the matching REST endpoint. Invalid input
raises ``ToolError`` (an MCP ``isError`` result), the MCP analogue of HTTP 422.
"""

from __future__ import annotations

from typing import Any

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from . import core
from .models import Address, dump

mcp = MCPServer(
    name="serviceability",
    instructions=(
        "US business address validation and network coverage lookup. "
        "Validate the address first, then call check_service_availability."
    ),
)


def _address(street: str, city: str, state: str, zip_code: str) -> Address:
    try:
        return Address(street=street, city=city, state=state, zip_code=zip_code)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        raise ToolError(f"Invalid address: {problems}") from None


@mcp.tool()
def validate_and_parse_address(address_string: str) -> dict[str, Any]:
    """Validates and parses a raw address string into structured components.

    Validates the address format and extracts street, city, state and ZIP.
    Rejects PO boxes and non-US addresses. Does NOT check serviceability.

    Args:
        address_string: Raw address text from user input
            (e.g. "123 Market St, Philadelphia, PA 19107").

    Returns:
        {"valid": true, "address": {"street", "city", "state", "zip_code"}} or
        {"valid": false, "error": "<why, and the expected format>"}.
    """
    return dump(core.validate_and_parse_address(address_string))


@mcp.tool()
def normalize_address(street: str, city: str, state: str, zip_code: str) -> dict[str, Any]:
    """Normalizes address components to the standard one-line format.

    Args:
        street: Street address (e.g. "123 market st")
        city: City name (e.g. "philadelphia")
        state: State abbreviation (e.g. "PA")
        zip_code: ZIP code (e.g. "19107")

    Returns:
        {"normalized_address": "123 Market St, Philadelphia, PA 19107"}
    """
    return dump(core.normalize_address(_address(street, city, state, zip_code)))


@mcp.tool()
def extract_zip_code(address_string: str) -> dict[str, Any]:
    """Extracts just the 5-digit ZIP code from an address string.

    Args:
        address_string: Address text

    Returns:
        {"zip_code": "19107"} ("" when no ZIP code is found; ZIP+4 is truncated).
    """
    return dump(core.extract_zip_code(address_string))


@mcp.tool()
async def check_service_availability(street: str, city: str, state: str, zip_code: str) -> dict[str, Any]:
    """Checks if telecom services are available at the given address.

    This is the MAIN deterministic serviceability tool. It queries the coverage
    map (GIS) and NEVER invents data.

    Args:
        street: Street address (e.g. "123 Market Street")
        city: City name (e.g. "Philadelphia")
        state: State abbreviation (e.g. "PA")
        zip_code: ZIP code (e.g. "19107")

    Returns:
        {"serviceable": bool, "address": {...},
         "infrastructure": {"type", "network_element", "speed_capability",
                            "service_class", "redundancy_available"},
         "infrastructure_type": "FTTP" | "HFC" | "DOCSIS 3.1",
         "max_speed_mbps": int, "service_zone": str, "estimated_install_days": int,
         "available_product_categories": ["Internet", "Voice", "SD-WAN", "Mobile"],
         "available_products": ["FIB-1G", ...]}   # SKU ids sold at the address
        Unserviceable results have "serviceable": false, a "reason" and empty
        product lists.
    """
    address = _address(street, city, state, zip_code)
    result = await anyio.to_thread.run_sync(core.check_service_availability, address)
    return dump(result)


@mcp.tool()
def get_infrastructure_by_technology(technology: str, zone: str = "all") -> dict[str, Any]:
    """Returns infrastructure capabilities for a technology type.

    Returns network capabilities and speed ranges, NOT product plans or pricing.

    Args:
        technology: "FTTP"/"Fiber", "HFC"/"Coax" or "DOCSIS 3.1"/"DOCSIS"
        zone: Service zone identifier (accepted but ignored; capabilities are
            not zone-specific)

    Returns:
        {"technology": "FTTP", "zone": "all", "infrastructure": [{"technology",
         "min_speed_mbps", "max_speed_mbps", "symmetrical", "service_classes",
         "typical_equipment", "redundancy_capable"}]}  (empty list when unknown)
    """
    return dump(core.get_infrastructure_by_technology(technology, zone))


@mcp.tool()
async def get_coverage_zones() -> dict[str, Any]:
    """Returns the list of all service zones.

    Useful for informational queries about service areas.

    Returns:
        {"zones": ["Metro-Atlanta", ...], "count": int}
    """
    return dump(await anyio.to_thread.run_sync(core.get_coverage_zones))


TOOL_NAMES = (
    "validate_and_parse_address",
    "normalize_address",
    "extract_zip_code",
    "check_service_availability",
    "get_infrastructure_by_technology",
    "get_coverage_zones",
)


def streamable_http_app():
    """Starlette app serving MCP at its root; mount it at ``/mcp``."""
    return mcp.streamable_http_app(
        streamable_http_path="/", stateless_http=True, json_response=True, host="0.0.0.0"
    )
