"""Customer Communication Agent: customer notifications (outbox dispatcher + A2A agent)."""

from .agent import build_agent, root_agent

__all__ = ["build_agent", "root_agent"]
