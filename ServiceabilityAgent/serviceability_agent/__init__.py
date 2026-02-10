"""
Serviceability Agent package.

This package provides address validation and service availability checking
for B2B telecommunications sales.
"""

from .agent import get_agent, serviceability_agent

__version__ = "1.0.0"
__all__ = ["get_agent", "serviceability_agent"]
