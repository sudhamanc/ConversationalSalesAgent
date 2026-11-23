"""POST /api/payment-methods – the chat's secure payment form (spec: guided-checkout).

The browser's ``SecurePaymentForm`` posts card or bank details here; the
gateway forwards them to the payment service's model-free
``POST /payment-methods``, which tokenizes and saves the masked method to the
customer's account. The details never reach a model, an SSE event or a log.

``customer_id`` comes only from the chat session's journey state
(``customer_context`` / ``order_context``), never from the browser.

Responses: 200 ``{payment_type, card_brand|account_type, last_four, expiry}`` ·
400 invalid details · 401 bad session · 409 no customer in this session yet ·
429 rate limited · 502 payment service unavailable.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from middleware.auth import get_authenticator
from middleware.rate_limiter import RateLimiter
from runtime import app_name, get_runner
from sales_common.auth import service_headers
from super_agent.registry import spec
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

#: Fields forwarded to the payment service; anything else in the body is dropped.
_FIELDS = (
    "payment_type", "card_number", "expiry_month", "expiry_year", "cvv",
    "routing_number", "account_number", "account_type",
)
_TIMEOUT_S = 15.0

payment_methods_limiter = RateLimiter()


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"success": False, "error": message}, status_code=status)


async def _customer_id(user_id: str, session_id: str) -> Optional[str]:
    try:
        adk_session = await get_runner().session_service.get_session(
            app_name=app_name(), user_id=user_id, session_id=session_id
        )
    except Exception as exc:
        logger.warning("Could not read session state for payment method: %s", type(exc).__name__)
        return None
    state = dict(getattr(adk_session, "state", None) or {})
    for key in ("customer_context", "order_context"):
        ctx = state.get(key)
        if isinstance(ctx, dict) and ctx.get("customer_id"):
            return str(ctx["customer_id"])
    return state.get("user:customer_id") or None


def payment_service_url() -> str:
    return spec("payment_agent").base_url().rstrip("/") + "/payment-methods"


@router.post("/api/payment-methods")
async def add_payment_method(request: Request, authorization: str = Header(default="")):
    session = get_authenticator().validate_token(authorization.removeprefix("Bearer ").strip())
    if not session:
        return _error("invalid session", 401)
    if not payment_methods_limiter.allow(session.session_id):
        return _error("Too many attempts. Please wait a moment.", 429)
    try:
        body: Any = await request.json()
    except ValueError:
        return _error("invalid json", 400)
    if not isinstance(body, dict):
        return _error("invalid body", 400)

    customer_id = await _customer_id(session.user_id, session.session_id)
    if not customer_id:
        return _error("Tell the assistant your company name first, then add a payment method.", 409)

    payload = {k: body[k] for k in _FIELDS if body.get(k) not in (None, "")}
    payload["customer_id"] = customer_id
    url = payment_service_url()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.post(url, json=payload, headers=service_headers(url))
    except httpx.HTTPError as exc:
        logger.warning("Payment service unreachable: %s", type(exc).__name__)
        return _error("The payment service is unavailable. Please try again shortly.", 502)
    try:
        result = response.json()
    except ValueError:
        result = {}
    if response.status_code == 400:
        return _error(str(result.get("error") or "Invalid payment details"), 400)
    if response.status_code != 200 or not result.get("success"):
        logger.warning("Payment service returned %s", response.status_code)
        return _error("The payment method could not be saved. Please try again.", 502)

    masked = {k: result.get(k) for k in ("payment_type", "card_brand", "account_type", "last_four", "expiry")}
    logger.info("Payment method saved for %s (%s ending %s)", customer_id, masked["payment_type"], masked["last_four"])
    return JSONResponse({"success": True, **{k: v for k, v in masked.items() if v is not None}})
