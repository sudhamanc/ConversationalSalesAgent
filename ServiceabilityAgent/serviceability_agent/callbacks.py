"""Agent-side callbacks for ``serviceability_agent``.

The serviceability tools run in the serviceability service (MCP), so session
state cannot be written by the tool itself. ``record_serviceability_context``
reads the ``check_service_availability`` MCP result and writes
``serviceability_context``; the shared ``export_context_delta`` (next in the
``after_tool_callback`` list) then adds ``_context_update`` for the gateway.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sales_common.mcp_client import mcp_result_payload

logger = logging.getLogger("serviceability_agent.callbacks")

CHECK_TOOL = "check_service_availability"
STATE_KEY = "serviceability_context"


def build_serviceability_context(payload: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    """``serviceability_context`` from a ``check_service_availability`` result."""
    address = payload.get("address") if isinstance(payload.get("address"), dict) else args
    parts = [address.get(k) or "" for k in ("street", "city", "state", "zip_code")]
    service_address = f"{parts[0]}, {parts[1]}, {parts[2]} {parts[3]}".strip()
    serviceable = bool(payload.get("serviceable"))
    speed = payload.get("max_speed_mbps")
    if speed is None:
        speed = ((payload.get("infrastructure") or {}).get("speed_capability") or {}).get("max_speed_mbps")
    return {
        "is_serviceable": serviceable,
        "infrastructure_type": payload.get("infrastructure_type"),
        "max_speed_mbps": speed,
        "available_products": list(payload.get("available_products") or []) if serviceable else [],
        "available_product_categories": list(payload.get("available_product_categories") or [])
        if serviceable else [],
        "service_zone": payload.get("service_zone"),
        "estimated_install_days": payload.get("estimated_install_days"),
        "service_address": service_address,
    }


def record_serviceability_context(tool, args, tool_context, tool_response) -> Optional[dict]:
    """``after_tool_callback``: record ``serviceability_context`` in session state.

    Only acts on successful ``check_service_availability`` results (both
    serviceable and unserviceable outcomes are recorded). Always returns
    ``None`` so ``export_context_delta`` runs next and adds ``_context_update``.
    """
    if getattr(tool, "name", None) != CHECK_TOOL:
        return None
    payload = mcp_result_payload(tool_response)
    if not payload or "serviceable" not in payload:
        logger.warning("check_service_availability returned no usable result; state unchanged")
        return None
    context = build_serviceability_context(payload, args or {})
    tool_context.state[STATE_KEY] = context
    logger.info(
        "serviceability_context recorded serviceable=%s type=%s products=%d",
        context["is_serviceable"], context["infrastructure_type"], len(context["available_products"]),
    )
    return None
