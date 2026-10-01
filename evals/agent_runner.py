"""Run one golden case in-process (agent or router) and return actual turns.

Shared by ``record_golden.py``. Agent cases run the agent's ``root_agent`` with
the case's ``session_input.state`` (the journey keys the gateway would forward);
router cases run ``build_router(model_name())`` with the case's user content,
which is the JSON routing input built by ``prepare_turn``.
"""

from __future__ import annotations

import importlib
from typing import Any

from google.adk.evaluation.eval_case import EvalCase
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from evals.golden_io import AGENT_PACKAGES
from evals.trace import Turn, events_to_turns

APP_NAME = "csa_eval"


def _user_texts(case: EvalCase) -> list[str]:
    return ["".join(p.text or "" for p in inv.user_content.parts or []) for inv in case.conversation or []]


async def run_with_agent(agent: Any, case: EvalCase) -> list[Turn]:
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)
    state = dict(case.session_input.state) if case.session_input else {}
    user_id = case.session_input.user_id if case.session_input else "eval_user"
    session = await session_service.create_session(app_name=APP_NAME, user_id=user_id, state=state)
    events = []
    for text in _user_texts(case):
        user_event_content = types.Content(role="user", parts=[types.Part(text=text)])
        events.append(_UserEvent(user_event_content))
        async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=user_event_content):
            if event.author != "user":  # the scripted marker above already opened this turn
                events.append(event)
    return events_to_turns(events)


class _UserEvent:
    """Marker so events_to_turns starts a new turn for each scripted user message."""

    author = "user"
    partial = False
    invocation_id = ""

    def __init__(self, content: types.Content):
        self.content = content


async def run_agent_case(agent_name: str, case: EvalCase) -> list[Turn]:
    package = importlib.import_module(AGENT_PACKAGES[agent_name])
    return await run_with_agent(package.build_agent(), case)


async def run_router_case(case: EvalCase) -> list[Turn]:
    from sales_common.config import model_name
    from super_agent.workflow import build_router

    from evals.test_router import standalone_router

    return await run_with_agent(standalone_router(build_router(model_name())), case)
