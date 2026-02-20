"""
Offer Management Agent package.

Provides deterministic pricing, discount, and quote generation tools.
"""

from .agent import get_agent, offer_management_agent

__version__ = "1.0.0"
__all__ = ["get_agent", "offer_management_agent"]
