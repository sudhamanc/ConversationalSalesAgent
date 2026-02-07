"""
FAQ sub-agent – answers common questions about policies, billing, and support.
"""

import os

from google.adk.agents import Agent

faq_agent = Agent(
    name="faq_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    instruction=(
        "You are a helpful FAQ assistant for a B2B telecom company. "
        "Answer common questions about billing, contracts, SLAs, "
        "installation timelines, support channels, and company policies. "
        "Be clear and concise. If a question falls outside your knowledge, "
        "recommend the user speak with a sales representative."
    ),
    description="Handles frequently asked questions, policies, billing, and support topics.",
    tools=[],
)
