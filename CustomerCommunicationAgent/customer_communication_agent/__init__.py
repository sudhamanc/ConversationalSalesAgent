"""
CustomerCommunicationAgent - Automated notification system for B2B telecommunications sales.

This agent handles all customer communications throughout the order lifecycle:
- Order confirmations
- Payment notifications (success/failure)
- Installation reminders and scheduling
- Service activation
- Abandoned cart recovery
- Order status updates
"""

from .agent import customer_communication_agent


def get_agent():
    """
    Returns the CustomerCommunicationAgent instance.
    
    This function provides a clean import interface for SuperAgent integration.
    """
    return customer_communication_agent


__all__ = ["customer_communication_agent", "get_agent"]
