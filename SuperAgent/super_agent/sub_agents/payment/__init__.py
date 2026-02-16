"""
Payment sub-agent wrapper for SuperAgent.

Exports the payment_agent loaded from the PaymentAgent project.
"""

from .agent import payment_agent

__all__ = ["payment_agent"]
