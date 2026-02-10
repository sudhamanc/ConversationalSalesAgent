"""
Product Agent package.

A specialized AI agent for retrieving technical specifications,
product features, and documentation via RAG (Retrieval-Augmented Generation).
"""

from .agent import get_agent, product_agent

__all__ = ["get_agent", "product_agent"]
__version__ = "1.0.0"
