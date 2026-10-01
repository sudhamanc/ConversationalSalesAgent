"""``sales_journey``: the ADK 2.x orchestration Workflow graph.

Custom template workflow (ADK 2.0 style: a graph ``Workflow`` of function nodes,
an LlmAgent router node, remote A2A agent nodes, and a custom ``Node`` subclass
for deterministic handoffs)::

    START -> prepare_turn --fast--> dispatch
                          --llm---> route_intent -> dispatch
    dispatch --<agent>--> <agent node> -> handoff_policy
    handoff_policy --serviceability_agent|payment_agent--> <agent node>   (<= 2 hops)
    handoff_policy --end--> finish_turn

State written here (session scope unless noted):
    turn_user_message, handoff_hops, last_agent, last_reply, transcript,
    appointment_confirmed_order (set by ContextBridgePlugin),
    user:customer_id, user:company_name (user scope, visible to later sessions)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Mapping, Optional

from google.adk import Agent, Context, Event, Workflow
from google.adk.agents import BaseAgent
from google.adk.workflow import Node
from google.genai import types
from pydantic import BaseModel, Field

from sales_common.a2a_client import OUTBOUND_MESSAGE_KEY
from sales_common.config import generate_config

from .prompts import ROUTER_INSTRUCTION
from .registry import AGENT_NAMES, AGENTS, FALLBACK_AGENT, GREETING_AGENT

logger = logging.getLogger("superagent.workflow")

MAX_HANDOFF_HOPS = 2
MAX_TRANSCRIPT_CHARS = 2000
MAX_REPLY_EXCERPT = 400
MAX_MEMORIES = 5
PAYMENT_DONE_STATUSES = {"completed", "approved", "captured"}
PAYABLE_ORDER_STATUSES = {None, "", "pending_payment", "draft"}

_GREETINGS = frozenset(
    {
        "hi", "hello", "hey", "howdy", "greetings", "hiya", "yo",
        "good morning", "good afternoon", "good evening", "good day",
        "hi there", "hello there", "hey there",
    }
)


class RouteDecision(BaseModel):
    """Structured output of the ``route_intent`` router node."""

    target: str = Field(description="Exactly one agent name from the agent list")
    reason: str = Field(default="", description="Short reason for the choice")


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without an LLM)
# ---------------------------------------------------------------------------


def is_pure_greeting(message: str) -> bool:
    if message.strip().startswith("[GREETING]"):
        return True
    cleaned = re.sub(r"[!.,?\s]+$", "", message.lower().strip())
    return cleaned in _GREETINGS


def journey_flags(state: Mapping[str, Any]) -> dict[str, Any]:
    customer = state.get("customer_context") or {}
    svc = state.get("serviceability_context") or {}
    offer = state.get("offer_context") or {}
    order = state.get("order_context") or {}
    payment = state.get("payment_context") or {}
    return {
        "customer_identified": bool(customer.get("customer_id")),
        "serviceability_checked": bool(svc),
        "serviceable": svc.get("is_serviceable"),
        "quote_ready": bool(offer.get("offer_id")),
        "order_created": bool(order.get("order_id")),
        "order_status": order.get("status"),
        "payment_status": payment.get("status"),
        "installation_scheduled": bool(state.get("appointment_confirmed_order"))
        or bool(state.get("installation_scheduled_order")),
    }


def append_transcript(transcript: str, speaker: str, text: str) -> str:
    line = f"{speaker}: {' '.join((text or '').split())}"
    combined = f"{transcript}\n{line}" if transcript else line
    return combined[-MAX_TRANSCRIPT_CHARS:]


def normalize_target(raw: Any) -> str:
    """Validate a router decision; unknown targets fall back to ``faq_agent``."""
    target = raw.get("target") if isinstance(raw, Mapping) else getattr(raw, "target", raw)
    target = str(target or "").strip()
    if target in AGENT_NAMES:
        return target
    logger.warning("Router returned unknown agent %r; falling back to %s", target, FALLBACK_AGENT)
    return FALLBACK_AGENT


@dataclass(frozen=True)
class Handoff:
    target: str
    message: str
    clear_keys: tuple[str, ...] = ()


def evaluate_handoff(state: Mapping[str, Any], last_agent: str, hops: int) -> Optional[Handoff]:
    """Deterministic handoff rules (see spec conversation-orchestration)."""
    if hops >= MAX_HANDOFF_HOPS:
        return None

    if last_agent == "discovery_agent":
        customer = state.get("customer_context") or {}
        address = customer.get("address") or {}
        zip_code = str(address.get("zip_code") or "").strip()
        svc = state.get("serviceability_context") or {}
        checked_zip = str((svc.get("service_address") or {}).get("zip_code") or "").strip() if isinstance(
            svc.get("service_address"), Mapping
        ) else ""
        if customer.get("customer_id") and zip_code and (not svc or (checked_zip and checked_zip != zip_code)):
            payload = {k: address.get(k) for k in ("street", "city", "state", "zip_code")}
            return Handoff(
                target="serviceability_agent",
                message="Check service availability for this address: " + json.dumps(payload),
            )

    if last_agent == "service_fulfillment_agent":
        order_id = state.get("appointment_confirmed_order")
        order = state.get("order_context") or {}
        payment = state.get("payment_context") or {}
        if (
            order_id
            and str(payment.get("status") or "").lower() not in PAYMENT_DONE_STATUSES
            and order.get("status") in PAYABLE_ORDER_STATUSES
        ):
            amount = order.get("total_amount")
            total = f"${float(amount):,.2f}" if isinstance(amount, (int, float)) else "the order total"
            return Handoff(
                target="payment_agent",
                message=(
                    f"Installation is scheduled for order {order_id}; total {total}. "
                    "Start payment: ask the customer for their payment method."
                ),
                clear_keys=("appointment_confirmed_order",),
            )
    return None


# ---------------------------------------------------------------------------
# Workflow nodes
# ---------------------------------------------------------------------------


async def prepare_turn(ctx: Context, node_input: str):
    """Record the user turn, recall memories, and build the router input."""
    message = (node_input or "").strip()
    transcript = append_transcript(ctx.state.get("transcript", ""), "user", message)
    state = {"turn_user_message": message, "handoff_hops": 0, "transcript": transcript}

    if is_pure_greeting(message):
        return Event(output={"target": GREETING_AGENT, "reason": "greeting"}, route="fast", state=state)

    memories: list[str] = []
    try:
        found = await ctx.search_memory(message)
        for entry in (found.memories or [])[:MAX_MEMORIES]:
            texts = [p.text for p in (entry.content.parts or []) if p.text] if entry.content else []
            if texts:
                memories.append(" ".join(texts)[:300])
    except ValueError:
        pass  # no memory service configured
    except Exception as exc:  # memory is best-effort context; never block the turn
        logger.warning("Memory search failed: %s", type(exc).__name__)

    router_input = {
        "message": message,
        "last_agent": ctx.state.get("last_agent"),
        "last_reply": (ctx.state.get("last_reply") or "")[-MAX_REPLY_EXCERPT:],
        "journey": journey_flags(ctx.state),
        "company_name": ctx.state.get("user:company_name")
        or (ctx.state.get("customer_context") or {}).get("company_name")
        or "",
        "memories": memories,
    }
    return Event(output=router_input, route="llm", state=state)


def dispatch(ctx: Context, node_input: Any):
    """Validate the routing decision and send the user's message to that agent."""
    target = normalize_target(node_input)
    logger.info("Routing turn to %s", target)
    message = ctx.state.get("turn_user_message", "")
    return Event(output=message, route=target, state={"last_agent": target, OUTBOUND_MESSAGE_KEY: message})


class HandoffPolicyNode(Node):
    """Custom workflow node: deterministic same-turn handoffs between agents."""

    async def run_node_impl(self, *, ctx: Context, node_input: Any) -> AsyncGenerator[Any, None]:
        reply = node_input if isinstance(node_input, str) else json.dumps(node_input, default=str)
        last_agent = ctx.state.get("last_agent") or ""
        hops = int(ctx.state.get("handoff_hops") or 0)
        transcript = append_transcript(ctx.state.get("transcript", ""), last_agent or "agent", reply)
        state: dict[str, Any] = {"last_reply": reply[-2000:], "transcript": transcript}

        handoff = evaluate_handoff(ctx.state, last_agent, hops)
        if handoff is None:
            yield Event(output=reply, route="end", state=state)
            return
        logger.info("Handoff %s -> %s (hop %d)", last_agent, handoff.target, hops + 1)
        state.update(
            {"last_agent": handoff.target, "handoff_hops": hops + 1, OUTBOUND_MESSAGE_KEY: handoff.message}
        )
        for key in handoff.clear_keys:
            state[key] = None
        if handoff.target == "payment_agent":
            state["installation_scheduled_order"] = ctx.state.get("appointment_confirmed_order")
        yield Event(output=handoff.message, route=handoff.target, state=state)


def finish_turn(ctx: Context, node_input: Any):
    """Persist user-scoped profile keys for returning sessions."""
    customer = ctx.state.get("customer_context") or {}
    state: dict[str, Any] = {}
    if customer.get("customer_id"):
        state["user:customer_id"] = customer["customer_id"]
    if customer.get("company_name"):
        state["user:company_name"] = customer["company_name"]
    return Event(output=node_input, state=state)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_router(model) -> Agent:
    # Thinking tokens count toward max_output_tokens. Gemini 3 thinks by default and
    # used ~250-700 tokens per routing call, truncating the JSON; routing needs none.
    config = generate_config(temperature=0.0, max_output_tokens=1024)
    if isinstance(model, str) and model.startswith("gemini-3"):
        config.thinking_config = types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)
    return Agent(
        name="route_intent",
        model=model,
        description="Classifies the customer's intent and picks one specialist agent.",
        mode="single_turn",
        static_instruction=ROUTER_INSTRUCTION,
        include_contents="none",
        output_schema=RouteDecision,
        generate_content_config=config,
    )


def build_workflow(agents: Mapping[str, BaseAgent], router_model) -> Workflow:
    """Assemble ``sales_journey`` from the 10 domain agent nodes and a router model."""
    missing = AGENT_NAMES - set(agents)
    if missing:
        raise ValueError(f"Missing agent nodes: {sorted(missing)}")
    router = build_router(router_model)
    handoff = HandoffPolicyNode(name="handoff_policy")
    edges: list = [
        ("START", prepare_turn),
        (prepare_turn, {"fast": dispatch, "llm": router}),
        (router, dispatch),
        (dispatch, {spec.name: agents[spec.name] for spec in AGENTS}),
    ]
    edges.extend((agents[spec.name], handoff) for spec in AGENTS)
    edges.append(
        (
            handoff,
            {
                "serviceability_agent": agents["serviceability_agent"],
                "payment_agent": agents["payment_agent"],
                "end": finish_turn,
            },
        )
    )
    return Workflow(
        name="sales_journey",
        description="Routes each customer turn to one specialist agent with deterministic handoffs.",
        edges=edges,
    )
