"""
Product sub-agent – answers questions about products, features, and plans.
"""

import os

from google.adk.agents import Agent
from google.genai import types

product_agent = Agent(
    name="product_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    instruction=(
        "Generate a knowledgeable phone script for a human sales agent to answer customer "
        "questions about cable MSO products: Internet plans, Ethernet services, TV packages, SD-WAN, "
        "managed Wi-Fi, voice services, and security products. The customer's question is transcribed from their call. "
        "Provide accurate, conversational responses that sound natural when read aloud over the phone. "
        "When comparing plans, use natural phrasing like 'We have three great options for you...' instead of bullet points. "
        "If unsure about specs, say: 'Let me pull up those exact details for you' or 'I can get you that specific information.' "
        "Sound like a knowledgeable human agent, not a script."
    ),
    description="Handles product inquiries, feature comparisons, and plan details.",
    tools=[],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=2048,
    ),
)
