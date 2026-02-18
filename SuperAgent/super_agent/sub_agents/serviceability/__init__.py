"""
Serviceability sub-agent wrapper for SuperAgent.

Exports the serviceability_agent loaded from the ServiceabilityAgent project.
"""

from .agent import serviceability_agent

__all__ = ["serviceability_agent"]
