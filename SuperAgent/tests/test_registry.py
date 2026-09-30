from google.adk.a2a.agent import RemoteA2aAgent

from super_agent.agent import build_remote_agents
from super_agent.registry import AGENTS, AGENT_NAMES


def test_builds_all_remote_agents(monkeypatch):
    monkeypatch.setenv("AGENT_URL_ORDER_AGENT", "http://order-agent:8205")
    agents = build_remote_agents()
    assert set(agents) == AGENT_NAMES and len(agents) == 10
    assert all(isinstance(a, RemoteA2aAgent) for a in agents.values())
    assert agents["order_agent"].name == "order_agent"


def test_env_override_and_defaults(monkeypatch):
    spec = next(a for a in AGENTS if a.name == "payment_agent")
    monkeypatch.delenv(spec.env_var, raising=False)
    assert spec.base_url() == "http://localhost:8206"
    monkeypatch.setenv(spec.env_var, "https://csa-agent-payment-x.a.run.app")
    assert spec.base_url() == "https://csa-agent-payment-x.a.run.app"


def test_router_prompt_names_every_agent():
    from super_agent.prompts import ROUTER_INSTRUCTION

    assert all(name in ROUTER_INSTRUCTION for name in AGENT_NAMES)
