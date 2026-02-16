"""
Service Fulfillment sub-agent wrapper for SuperAgent.

Exports the service_fulfillment_agent loaded from the ServiceFulfillmentAgent project.
"""

from .agent import service_fulfillment_agent

__all__ = ["service_fulfillment_agent"]
