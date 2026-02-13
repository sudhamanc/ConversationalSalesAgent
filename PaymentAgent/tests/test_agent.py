"""
Tests for the Payment Agent.
"""

import pytest
from payment_agent import get_agent


def test_agent_initialization():
    """Test that the agent initializes correctly."""
    agent = get_agent()
    assert agent is not None
    assert agent.name == "payment_agent"


def test_agent_has_tools():
    """Test that the agent has the required tools."""
    agent = get_agent()
    assert agent.tools is not None
    assert len(agent.tools) > 0


# Add more tests as needed
