import json
import os
from typing import Optional
import logging
import vertexai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import agent_tool, google_search
from google.genai import types
from dotenv import load_dotenv


# configure logging __name__
custom_logger = logging.getLogger(__name__)
custom_logger.info("Initializing root agent...")

load_dotenv()

agent_model = os.environ.get("GEMINI_MODEL")
custom_logger.info(f"setting the agent model to {agent_model}")


from .sub_agents.test.test_agent import test_agent_simple
from .sub_agents.discovery.discovery_agent import discovery_agent
from .sub_agents.lead_gen.lead_gen_agent import lead_gen_agent



# The orchestrator will rely on its sub_agents.
root_agent = Agent(
    name="adk_agent",
    model=agent_model,
    instruction="""You are a disovery sub agent which will be called from the super agent orchestrator. Your job is to handle all sales discovery, customer research, company information, contact identification, and intent analysis queries. You will receive control from the orchestrator via the `transfer_to_agent` tool when the user's query matches these categories.
- For sales discovery, customer research, company information, contact identification, or intent analysis, delegate to the `discovery_agent`.
- For lead qualification, BANT scoring, sales readiness assessment, or pipeline prioritization, delegate to the `lead_gen_agent`.
- For simple tests, delegate to the `test_agent_simple`.

Route customer and prospecting queries to discovery_agent, and qualification/scoring queries to lead_gen_agent.
""",
    description="The main discovery sub-agent for all conversations. It determines the user's intent and delegates to the appropriate sub-agent or tool.",
    sub_agents=[
        discovery_agent,
        lead_gen_agent,
        test_agent_simple,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        top_p=0.1,
        top_k=10,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ],
    ),
)
