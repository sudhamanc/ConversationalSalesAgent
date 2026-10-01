"""Gateway configuration (environment variables; fail fast on critical values).

Local development loads ``.env`` from the repository root if present (without
overriding variables already set by the shell, compose or Cloud Run).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
if _ROOT_ENV.is_file():
    load_dotenv(_ROOT_ENV, override=False)


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class AgentConfig:
    app_name: str = os.getenv("AGENT_NAME", "super_sales_agent")
    router_temperature: float = 0.0


@dataclass(frozen=True)
class RateLimitConfig:
    requests_per_minute: int = _int("RATE_LIMIT_RPM", 20)
    requests_per_hour: int = _int("RATE_LIMIT_RPH", 200)
    burst_size: int = _int("RATE_LIMIT_BURST", 5)


@dataclass(frozen=True)
class SessionConfig:
    token_expiry_minutes: int = _int("SESSION_TOKEN_EXPIRY_MIN", 60)


@dataclass(frozen=True)
class ServerConfig:
    host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    port: int = _int("PORT", _int("SERVER_PORT", 8000))
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
            if o.strip()
        ]
    )
    log_level: str = os.getenv("LOG_LEVEL", "info").lower()
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    run_migrations: bool = os.getenv("RUN_MIGRATIONS", "false").lower() == "true"
    suggestions_enabled: bool = os.getenv("SUGGESTIONS_ENABLED", "true").lower() == "true"


@dataclass(frozen=True)
class Settings:
    agent: AgentConfig = field(default_factory=AgentConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


settings = Settings()
