"""
FAQ sub-agent – answers common questions about policies, billing, and support.
"""

import os

from google.adk.agents import Agent
from google.genai import types

faq_agent = Agent(
    name="faq_agent",
    model=os.getenv("GEMINI_MODEL"),
    instruction=(
        "Generate a clear phone script for a human sales agent to answer customer questions "
        "about cable MSO products, contracts, SLAs, installation timelines, support channels, and policies. "
        "The customer's question has been transcribed from their phone call. "
        "Provide accurate information in a conversational tone that sounds natural when read aloud by the agent. "
        "If the question is outside your knowledge, suggest: 'Let me check with our specialist team and get back to you.' "
        "Keep responses concise and phone-friendly. Sound professional but human."
    ),
    description="Handles frequently asked questions, policies, billing, and support topics.",
    tools=[],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=2048,
    ),
)
