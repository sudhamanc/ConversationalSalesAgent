"""Domain agent registry: names, routing descriptions, and A2A endpoints.

Each domain agent runs as its own A2A service. Its base URL comes from
``AGENT_URL_<NAME>`` (e.g. ``AGENT_URL_ORDER_AGENT=http://order-agent:8205``).
The agent card is fetched from ``<base>/.well-known/agent-card.json``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSpec:
    name: str
    description: str
    default_url: str

    @property
    def env_var(self) -> str:
        return f"AGENT_URL_{self.name.upper()}"

    def base_url(self) -> str:
        return os.getenv(self.env_var, "").strip() or self.default_url


AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec("greeting_agent", "Greetings, introductions, phone scripts listing all products.", "http://localhost:8209"),
    AgentSpec("faq_agent", "Policies, SLAs, contracts, support and general questions.", "http://localhost:8210"),
    AgentSpec("discovery_agent", "Company identification/registration, contacts, BANT qualification.", "http://localhost:8201"),
    AgentSpec("serviceability_agent", "Address validation and network coverage (pre-sale).", "http://localhost:8202"),
    AgentSpec("product_agent", "Product catalog, specifications, comparisons (no pricing).", "http://localhost:8203"),
    AgentSpec("offer_management_agent", "Pricing, discounts, quotes (only pricing source).", "http://localhost:8204"),
    AgentSpec("order_agent", "Cart, orders, contracts, cancellations.", "http://localhost:8205"),
    AgentSpec("payment_agent", "Payment methods, credit checks, payment processing, invoices.", "http://localhost:8206"),
    AgentSpec("service_fulfillment_agent", "Installation scheduling, provisioning, activation.", "http://localhost:8207"),
    AgentSpec("customer_communication_agent", "Notifications and notification history.", "http://localhost:8208"),
)

AGENT_NAMES: frozenset[str] = frozenset(a.name for a in AGENTS)
FALLBACK_AGENT = "faq_agent"
GREETING_AGENT = "greeting_agent"


def spec(name: str) -> AgentSpec:
    for agent in AGENTS:
        if agent.name == name:
            return agent
    raise KeyError(name)


def display_name(name: str) -> str:
    return name.replace("_agent", "").replace("_", " ")
