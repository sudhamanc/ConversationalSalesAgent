"""
Order Agent package.

This package provides order lifecycle management including cart operations,
order creation, contract generation, and order finalization for B2B sales.
"""

from .agent import get_agent, order_agent

__version__ = "1.0.0"
__all__ = ["get_agent", "order_agent"]
