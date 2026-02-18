"""
Greeting sub-agent – handles introductions and small-talk.
"""

import os

from google.adk.agents import Agent
from google.genai import types

greeting_agent = Agent(
    name="greeting_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    instruction=(
        "Generate a professional phone script for a human sales agent to read to the customer. "
        "The customer's speech has been transcribed. Provide a warm, natural greeting response "
        "that the agent can read aloud to acknowledge the customer and offer assistance. "
        "\n\n**IMPORTANT: Always explicitly mention ALL five products in your greeting:**\n"
        "1. Internet\n"
        "2. Ethernet\n"
        "3. TV\n"
        "4. SD-WAN\n"
        "5. Security Products\n\n"
        "Example: 'I'd be happy to help you with our Internet, Ethernet, TV, SD-WAN, or Security Products, "
        "whether you're looking for pricing or service availability.'\n\n"
        "Keep it conversational and phone-appropriate (2-3 sentences). Sound like a helpful human agent, not a bot."
    ),
    description="Handles greetings, introductions, and casual conversation.",
    tools=[],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=2048,
    ),
)
