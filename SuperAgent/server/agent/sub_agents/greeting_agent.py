"""
Greeting sub-agent – handles introductions and small-talk.
"""

import os

from google.adk.agents import Agent

greeting_agent = Agent(
    name="greeting_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    instruction=(
        "You are a friendly B2B sales greeting assistant. "
        "When the user greets you or engages in small-talk, respond warmly "
        "and steer the conversation toward how you can help them with "
        "telecom products, service availability, or pricing. "
        "Keep responses to 2-3 sentences."
    ),
    description="Handles greetings, introductions, and casual conversation.",
    tools=[],
)
