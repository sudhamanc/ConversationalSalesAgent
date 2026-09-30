import os
import subprocess
import sys

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION
from sales_common.testing import ScriptLlm

from faq_agent import build_agent, root_agent
from faq_agent.prompts import FAQ_AGENT_INSTRUCTION


def test_construction():
    assert root_agent.name == "faq_agent"
    assert root_agent.tools == []
    assert root_agent.static_instruction == FAQ_AGENT_INSTRUCTION
    assert root_agent.instruction == JOURNEY_CONTEXT_INSTRUCTION
    assert root_agent.generate_content_config.temperature == 0.7
    assert "transfer_to_agent" not in FAQ_AGENT_INSTRUCTION


async def test_runner_reply_authored_by_agent():
    llm = ScriptLlm(steps=[{"text": "Hello from faq_agent"}], requests=[])
    agent = build_agent(model=llm)
    runner = Runner(app_name="t", agent=agent, session_service=InMemorySessionService(),
                    auto_create_session=True)
    texts = []
    async for event in runner.run_async(
        user_id="u", session_id="s",
        new_message=types.Content(role="user", parts=[types.Part(text="Hi")]),
    ):
        if event.content and event.content.parts and event.content.parts[0].text:
            texts.append((event.author, event.content.parts[0].text))
    assert texts == [("faq_agent", "Hello from faq_agent")]
    assert llm.requests, "model was not called"


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")
def test_server_module_imports():
    # Subprocess: a2a-sdk's DatabaseTaskStore registers the "a2a_tasks" table in
    # process-global SQLAlchemy metadata, so only one server app per process.
    code = (
        "from faq_agent.server import app; "
        "paths = {getattr(r, 'path', None) for r in app.router.routes}; "
        "assert '/healthz' in paths, paths; print('ok')"
    )
    result = subprocess.run([sys.executable, "-c", code], env=dict(os.environ),
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("ok")
