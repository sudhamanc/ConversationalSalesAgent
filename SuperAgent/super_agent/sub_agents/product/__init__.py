"""
Product sub-agent wrapper for SuperAgent integration.

Exports the product_agent instance loaded via importlib isolation.
"""

from .agent import product_agent

__all__ = ["product_agent"]
