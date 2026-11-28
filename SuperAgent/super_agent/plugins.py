"""Gateway App plugins."""

from __future__ import annotations

import logging
from typing import Any, Optional

from google.adk.plugins.base_plugin import BasePlugin

from sales_common.context import extract_context_updates

from .registry import AGENT_NAMES

logger = logging.getLogger("superagent.audit")
PAYMENT_DONE = {"completed", "approved", "captured"}


class ContextBridgePlugin(BasePlugin):
    """Merge remote agents' journey-context updates into gateway session state.

    Remote A2A agents cannot return ``state_delta``. Their tools append
    ``_context_update`` to function responses (``sales_common.context``), which
    do cross the A2A boundary; this plugin copies them into the event's
    ``state_delta`` before the event is persisted, so downstream workflow nodes
    (e.g. ``HandoffPolicyNode``) and later turns see them. It also records a
    successful ``create_order`` (order -> scheduling handoff), a new registration without a
    contact email (``registration_waiting_for_contact``), a successful ``process_payment``
    (``payment_completed_order``, payment -> fulfillment handoff) and ``schedule_installation``
    (scheduling -> payment handoff),
    and writes a delegation audit log line per tool call.
    """

    def __init__(self) -> None:
        super().__init__(name="context_bridge")

    async def on_event_callback(self, *, invocation_context, event) -> Optional[Any]:
        if event.author not in AGENT_NAMES or not event.content or not event.content.parts:
            return None
        responses = []
        registered = False
        for part in event.content.parts:
            fr = getattr(part, "function_response", None)
            if fr is None:
                continue
            response = fr.response if isinstance(fr.response, dict) else {"result": fr.response}
            responses.append(response)
            logger.info(
                "delegation author=%s tool=%s success=%s session=%s",
                event.author,
                fr.name,
                response.get("success"),
                invocation_context.session.id,
            )
            if fr.name == "create_order" and response.get("success") and response.get("order_id"):
                # order -> fulfillment handoff (spec: guided-checkout)
                event.actions.state_delta["order_created_order"] = response["order_id"]
                event.actions.state_delta["order_waiting_for_contact"] = None
            if fr.name == "create_order" and response.get("error") == "contact_email_required":
                # discovery -> order handoff once the contact is saved (spec: guided-checkout)
                event.actions.state_delta["order_waiting_for_contact"] = True
            if (fr.name == "process_payment" and response.get("success") and response.get("order_id")
                    and str(response.get("status") or "").lower() in PAYMENT_DONE):
                # payment -> fulfillment handoff: provisioning starts (spec: conversation-orchestration)
                event.actions.state_delta["payment_completed_order"] = response["order_id"]
            if fr.name == "add_new_company" and response.get("success"):
                registered = True
            if fr.name == "schedule_installation" and response.get("success"):
                order_ctx = invocation_context.session.state.get("order_context") or {}
                order_id = response.get("order_id") or order_ctx.get("order_id")
                if order_id:
                    event.actions.state_delta["appointment_confirmed_order"] = order_id
        updates = extract_context_updates(responses)
        if updates:
            event.actions.state_delta.update(updates)
            logger.info("context_update keys=%s from %s", sorted(updates), event.author)
        customer = updates.get("customer_context") or invocation_context.session.state.get("customer_context") or {}
        has_email = bool(((customer.get("contact") if isinstance(customer, dict) else None) or {}).get("email"))
        if registered and not has_email:
            # discovery -> serviceability waits for the contact card (spec: conversation-orchestration)
            event.actions.state_delta["registration_waiting_for_contact"] = True
        return None
