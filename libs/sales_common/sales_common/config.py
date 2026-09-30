"""Fail-fast environment configuration shared by every service."""

from __future__ import annotations

import os
from dataclasses import dataclass

from google.genai import types


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def require_env(name: str) -> str:
    """Return a required environment variable or raise ``ConfigError``."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required")
    return value


def env_str(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def model_name() -> str:
    """Gemini model for LLM agents. No default: fail fast when unset."""
    return require_env("GEMINI_MODEL")


_THRESHOLDS = {
    "BLOCK_NONE": types.HarmBlockThreshold.BLOCK_NONE,
    "BLOCK_LOW_AND_ABOVE": types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    "BLOCK_MEDIUM_AND_ABOVE": types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "BLOCK_ONLY_HIGH": types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
}


def safety_settings() -> list[types.SafetySetting]:
    """Gemini safety settings from ``SAFETY_*`` env vars (default BLOCK_LOW_AND_ABOVE)."""
    pairs = [
        (types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "SAFETY_DANGEROUS"),
        (types.HarmCategory.HARM_CATEGORY_HARASSMENT, "SAFETY_HARASSMENT"),
        (types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, "SAFETY_HATE_SPEECH"),
        (types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "SAFETY_SEXUALLY_EXPLICIT"),
    ]
    settings = []
    for category, var in pairs:
        level = env_str(var, "BLOCK_LOW_AND_ABOVE").upper()
        if level not in _THRESHOLDS:
            raise ConfigError(f"{var} must be one of {sorted(_THRESHOLDS)}, got {level!r}")
        settings.append(types.SafetySetting(category=category, threshold=_THRESHOLDS[level]))
    return settings


def generate_config(temperature: float, max_output_tokens: int = 2048) -> types.GenerateContentConfig:
    """Standard generation config with safety settings and HTTP retries."""
    return types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        safety_settings=safety_settings(),
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(initial_delay=2.0, attempts=3),
        ),
    )


@dataclass(frozen=True)
class ContextSettings:
    """Context compaction and model context caching settings (ADK App)."""

    compaction_interval: int
    compaction_overlap: int
    compaction_token_threshold: int
    compaction_retention: int
    cache_intervals: int
    cache_ttl_seconds: int
    cache_min_tokens: int

    @classmethod
    def from_env(cls) -> "ContextSettings":
        return cls(
            compaction_interval=env_int("COMPACTION_INTERVAL", 8),
            compaction_overlap=env_int("COMPACTION_OVERLAP", 2),
            compaction_token_threshold=env_int("COMPACTION_TOKEN_THRESHOLD", 60_000),
            compaction_retention=env_int("COMPACTION_RETENTION_EVENTS", 10),
            cache_intervals=env_int("CONTEXT_CACHE_INTERVALS", 10),
            cache_ttl_seconds=env_int("CONTEXT_CACHE_TTL_SECONDS", 1800),
            cache_min_tokens=env_int("CONTEXT_CACHE_MIN_TOKENS", 4096),
        )
