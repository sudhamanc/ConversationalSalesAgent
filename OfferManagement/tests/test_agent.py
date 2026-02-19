"""Integration tests for Offer Management agent initialization."""

from offer_management import get_agent


def test_offer_agent_initialization():
    agent = get_agent()
    assert agent.name == "offer_management_agent"
    assert len(agent.tools) >= 2


def test_offer_agent_config_deterministic():
    agent = get_agent()
    cfg = agent.generate_content_config
    assert cfg.temperature == 0.0
    assert cfg.top_p == 0.1
    assert cfg.top_k == 10
