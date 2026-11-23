"""Plain REST routes of the payment service (no model involved).

``POST /payment-methods`` tokenizes a card or bank account and saves the masked
method to the customer's account (spec: agent-services, payment methods REST
endpoint). The chat's secure payment form reaches it through the gateway
(``POST /api/payment-methods``), so card and bank details never pass through an
LLM. The response carries the masked method only, never the token or numbers.
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .tools.payment_tools import tokenize_payment_method

logger = logging.getLogger("payment_agent.rest")

_CARD_FIELDS = ("card_number", "expiry_month", "expiry_year", "cvv")
_ACH_FIELDS = ("routing_number", "account_number", "account_type")


def _str(body: dict, key: str) -> str | None:
    value = body.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


async def add_payment_method(request: Request) -> JSONResponse:
    try:
        body: Any = await request.json()
    except ValueError:
        return JSONResponse({"success": False, "error": "Body must be JSON"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"success": False, "error": "Body must be a JSON object"}, status_code=400)

    customer_id = _str(body, "customer_id")
    payment_type = _str(body, "payment_type")
    if not customer_id:
        return JSONResponse({"success": False, "error": "customer_id is required"}, status_code=400)
    if payment_type not in ("credit_card", "ach"):
        return JSONResponse({"success": False, "error": "payment_type must be credit_card or ach"}, status_code=400)

    fields = _CARD_FIELDS if payment_type == "credit_card" else _ACH_FIELDS
    kwargs = {k: _str(body, k) for k in fields}
    if payment_type == "ach" and kwargs.get("account_type") not in ("checking", "savings"):
        return JSONResponse({"success": False, "error": "account_type must be checking or savings"}, status_code=400)

    result = tokenize_payment_method(payment_type=payment_type, customer_id=customer_id, **kwargs)
    if not result.get("success"):
        # Validation messages never contain the submitted numbers.
        return JSONResponse({"success": False, "error": result.get("error") or "Invalid payment details"},
                            status_code=400)
    if not result.get("saved"):
        logger.warning("Payment method for %s tokenized but not saved", customer_id)
        return JSONResponse({"success": False, "error": "The payment method could not be saved"}, status_code=502)

    masked = {
        "success": True,
        "saved": True,
        "method_id": result.get("method_id"),
        "payment_type": payment_type,
        "card_brand": result.get("card_brand"),
        "account_type": result.get("account_type"),
        "last_four": result.get("last_four"),
        "expiry": result.get("expiry"),
    }
    logger.info("Payment method %s saved for %s (%s ending %s)",
                masked["method_id"], customer_id, payment_type, masked["last_four"])
    return JSONResponse({k: v for k, v in masked.items() if v is not None})


ROUTES = [Route("/payment-methods", add_payment_method, methods=["POST"])]
