"""Gateway ADK application: the ``sales_journey`` workflow wrapped in an ``App``.

Domain agents are remote A2A services (``RemoteA2aAgent``); the router is the
only in-process LLM. See ``workflow.py`` for the graph and
``openspec/changes/archive/2026-10-01-adk2-workflow-orchestration/design.md`` for the rationale.
"""

from __future__ import annotations

from typing import Mapping, Optional

from google.adk.agents import BaseAgent
from google.adk.apps import App

from sales_common.a2a_client import remote_agent
from sales_common.adk_app import build_app
from sales_common.config import model_name
from sales_common.context import build_forwarded_metadata

from .config import settings
from .plugins import ContextBridgePlugin
from .registry import AGENTS
from .workflow import build_workflow


def forwarded_metadata(ctx, _message) -> dict:
    """A2A request metadata: journey context, transcript, and user profile."""
    state = ctx.session.state
    profile = {
        "customer_id": state.get("user:customer_id"),
        "company_name": state.get("user:company_name"),
    }
    return build_forwarded_metadata(
        state,
        session_id=ctx.session.id,
        transcript=state.get("transcript", ""),
        user_profile={k: v for k, v in profile.items() if v},
    )


def build_remote_agents() -> dict[str, BaseAgent]:
    return {
        spec.name: remote_agent(
            spec.name, spec.base_url(), description=spec.description, meta_provider=forwarded_metadata
        )
        for spec in AGENTS
    }


def build_gateway_app(
    agents: Optional[Mapping[str, BaseAgent]] = None,
    router_model=None,
) -> App:
    """Build the gateway App. Tests pass in-process agents and a scripted router model."""
    workflow = build_workflow(agents or build_remote_agents(), router_model or model_name())
    return build_app(settings.agent.app_name, workflow, plugins=[ContextBridgePlugin()])
