"""
Product sub-agent – answers questions about products, features, and plans.
"""

import os

from google.adk.agents import Agent

product_agent = Agent(
    name="product_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    instruction=(
        "You are a knowledgeable B2B telecom product specialist. "
        "Answer questions about internet plans, fiber services, SD-WAN, "
        "managed Wi-Fi, voice services, and security products. "
        "Provide accurate details. If you are unsure about a specification, "
        "say so and offer to look it up. Format responses with clear headings "
        "and bullet points when comparing plans."
    ),
    description="Handles product inquiries, feature comparisons, and plan details.",
    tools=[],
)
