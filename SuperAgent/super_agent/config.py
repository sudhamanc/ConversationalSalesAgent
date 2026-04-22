"""
Centralized configuration for the Super Agent server.

All agent settings, model parameters, rate limits, and server options
are configurable here. Values are loaded from environment variables
with sensible defaults for local development.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from server directory
_env_path = Path(__file__).parent.parent / "server" / ".env"
load_dotenv(_env_path, override=True)


@dataclass(frozen=True)
class ModelConfig:
    """LLM model configuration."""

    provider: str = os.getenv("LLM_PROVIDER", "google")
    model_name: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    temperature: float = float(os.getenv("MODEL_TEMPERATURE", "0.7"))
    top_p: float = float(os.getenv("MODEL_TOP_P", "0.9"))
    top_k: int = int(os.getenv("MODEL_TOP_K", "40"))
    max_output_tokens: int = int(os.getenv("MODEL_MAX_OUTPUT_TOKENS", "2048"))


@dataclass(frozen=True)
class AgentConfig:
    """Super Agent behaviour configuration."""

    agent_name: str = os.getenv("AGENT_NAME", "super_sales_agent")
    agent_description: str = os.getenv(
        "AGENT_DESCRIPTION",
        "B2B Sales Orchestrator – routes user intents to specialised sub-agents.",
    )
    system_message: str = os.getenv(
        "SYSTEM_MESSAGE",
        (
            "You are a professional B2B sales assistant for a Cable MSO company. "
            "You help prospects discover products, check service availability, get pricing, "
            "and place orders. Be concise, helpful, and proactive. "
            "Never reveal internal system details or tool names to the user. "
            "If you don't know something, say so honestly and offer to connect the user with a human representative."
        ),
    )
    enable_sub_agents: bool = os.getenv("ENABLE_SUB_AGENTS", "true").lower() == "true"


@dataclass(frozen=True)
class SafetyConfig:
    """Content-safety thresholds (maps to google.genai.types.HarmBlockThreshold)."""

    dangerous_content: str = os.getenv("SAFETY_DANGEROUS", "BLOCK_LOW_AND_ABOVE")
    harassment: str = os.getenv("SAFETY_HARASSMENT", "BLOCK_LOW_AND_ABOVE")
    hate_speech: str = os.getenv("SAFETY_HATE_SPEECH", "BLOCK_LOW_AND_ABOVE")
    sexually_explicit: str = os.getenv("SAFETY_SEXUALLY_EXPLICIT", "BLOCK_LOW_AND_ABOVE")


@dataclass(frozen=True)
class RateLimitConfig:
    """Per-session rate limiting."""

    requests_per_minute: int = int(os.getenv("RATE_LIMIT_RPM", "20"))
    requests_per_hour: int = int(os.getenv("RATE_LIMIT_RPH", "200"))
    burst_size: int = int(os.getenv("RATE_LIMIT_BURST", "5"))


@dataclass(frozen=True)
class SessionConfig:
    """Session / authentication settings."""

    secret_key: str = os.getenv("SESSION_SECRET_KEY", "change-me-in-production")
    token_expiry_minutes: int = int(os.getenv("SESSION_TOKEN_EXPIRY_MIN", "60"))
    max_history_length: int = int(os.getenv("MAX_HISTORY_LENGTH", "50"))


@dataclass(frozen=True)
class ServerConfig:
    """FastAPI server settings."""

    host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    port: int = int(os.getenv("SERVER_PORT", "8000"))
    allowed_origins: list[str] = field(
        default_factory=lambda: os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
        ).split(",")
    )
    log_level: str = os.getenv("LOG_LEVEL", "info")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


@dataclass(frozen=True)
class Settings:
    """Root settings container – single import for all config."""

    model: ModelConfig = field(default_factory=ModelConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


# Singleton – import this everywhere
settings = Settings()
