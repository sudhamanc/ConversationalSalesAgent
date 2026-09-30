"""Map ADK workflow events to the chat UI's SSE payloads.

Contract (unchanged for the React client): ``token``, ``activity_update``,
``structured_card``, ``cart_update``, ``suggestions``, ``done``, ``error``.
Only events authored by domain agents produce ``token`` payloads; router and
workflow bookkeeping events are internal. Remote A2A agents can deliver the same
final text twice (status update + final task), so texts are de-duplicated per
author within a turn. Remote tool results (``function_response``) do cross the
A2A boundary and drive the activity/cart/quote events.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from super_agent.registry import AGENT_NAMES

CART_TOOLS = {"create_cart", "add_to_cart", "remove_from_cart", "get_cart", "clear_cart"}
ORDER_TOOLS = {"create_order", "modify_order", "get_order", "update_order_status"}
QUOTE_TOOLS = {"generate_offer_quote", "find_best_bundle_offer", "get_quote_details"}
SCHEDULING_TOOLS = {"schedule_installation", "check_availability"}
FULFILLMENT_TOOLS = {"provision_equipment", "dispatch_technician", "activate_service", "run_service_tests"}
PAYMENT_TOOLS = {"process_payment", "check_business_credit", "validate_payment_method"}
NOTIFICATION_TOOLS = {
    "send_order_confirmation",
    "send_payment_notification",
    "send_quote_confirmation",
    "send_installation_reminder",
    "send_service_activated_notification",
    "send_order_status_update",
    "send_abandoned_cart_reminder",
}
PAYMENT_SUCCESS = {"approved", "completed", "captured"}
_AUTO_NOTIFICATION_LABEL = {
    "create_order": "send_order_confirmation",
    "process_payment": "send_payment_notification",
}


def _clean_response(response: Any) -> Optional[dict]:
    if not isinstance(response, dict):
        return None
    return {k: v for k, v in response.items() if k != "_context_update"}


class EventMapper:
    """Stateful per-turn mapper from ADK events to SSE payload dicts."""

    def __init__(self) -> None:
        self._seen_texts: set[tuple[str, str]] = set()
        self.response_parts: list[str] = []
        self.last_text_author: Optional[str] = None
        self.current_target: Optional[str] = None
        self.provisioning_done = False
        self.domain_events_seen = False

    @property
    def sent_text(self) -> bool:
        return bool(self.response_parts)

    def consume(self, event) -> list[dict]:
        route = getattr(getattr(event, "actions", None), "route", None)
        if isinstance(route, str) and route in AGENT_NAMES:
            self.current_target = route

        if event.author not in AGENT_NAMES or not event.content or not event.content.parts:
            return []
        self.domain_events_seen = True
        payloads: list[dict] = []
        for part in event.content.parts:
            text = getattr(part, "text", None)
            if text and text.strip() and not getattr(part, "thought", False):
                key = (event.author, hashlib.sha256(text.strip().encode()).hexdigest())
                if key in self._seen_texts:
                    continue
                self._seen_texts.add(key)
                if self.response_parts and self.last_text_author != event.author:
                    payloads.append({"type": "token", "content": "\n\n", "author": event.author})
                self.response_parts.append(text)
                self.last_text_author = event.author
                payloads.append({"type": "token", "content": text, "author": event.author})
            fr = getattr(part, "function_response", None)
            if fr is not None:
                payloads.extend(self._tool_payloads(fr.name, _clean_response(fr.response), event.author))
        return payloads

    def _tool_payloads(self, name: str, response: Optional[dict], author: str) -> list[dict]:
        if response is None:
            return []
        out: list[dict] = []

        def activity(category: str, data: Any, tool: str = name) -> None:
            out.append({"type": "activity_update", "category": category, "tool": tool, "data": data})

        if response.get("success"):
            if response.get("customer_id") and response.get("company_name"):
                activity(
                    "customer",
                    {"customer_id": response["customer_id"], "company_name": response["company_name"]},
                )
            if name in ORDER_TOOLS:
                activity("order", response)
            if name in SCHEDULING_TOOLS:
                activity("scheduling", response)
            if name in FULFILLMENT_TOOLS:
                activity("fulfillment", response)
                if name == "dispatch_technician":
                    self.provisioning_done = True
            if name in PAYMENT_TOOLS:
                activity("payment", response)
                if name == "process_payment" and str(response.get("status", "")).lower() in PAYMENT_SUCCESS:
                    activity("order", {"payment_status": "paid", "status": "confirmed"}, tool="payment_update")
            if name in NOTIFICATION_TOOLS:
                activity("notification", response)
            notification_id = response.get("email_notification_id") or response.get("notification_id")
            if notification_id and name not in NOTIFICATION_TOOLS:
                activity(
                    "notification",
                    {"notification_id": notification_id, "triggered_by": name, "status": "queued"},
                    tool=_AUTO_NOTIFICATION_LABEL.get(name, name),
                )

        if name in QUOTE_TOOLS and response.get("offer_id"):
            activity("quote", response)
            out.append({"type": "structured_card", "card_type": "quote", "data": response})
            sent = response.get("notification_sent")
            if sent:
                activity(
                    "notification",
                    {"type": (sent.get("type") if isinstance(sent, dict) else None) or "QUOTE_CONFIRMATION", "status": "queued"},
                    tool="send_quote_confirmation",
                )

        cart_data = None
        if name in CART_TOOLS:
            cart_data = response.get("cart", response)
        elif name in ORDER_TOOLS:
            order = response.get("order") if isinstance(response.get("order"), dict) else None
            items = (order or {}).get("items") if order else response.get("items")
            if isinstance(items, list) and items:
                cart_data = {
                    "cart_id": (order or {}).get("order_id") or response.get("order_id", ""),
                    "items": items,
                    "total_amount": (order or {}).get("total_amount", response.get("total_amount", 0)),
                }
        if cart_data:
            out.append({"type": "cart_update", "tool": name, "data": cart_data, "author": author})
        return out
