"""ADK ``App`` factory: context compaction + model context caching for every agent app."""

from __future__ import annotations

import logging
from typing import Optional, Sequence

from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.plugins.base_plugin import BasePlugin

from .config import ContextSettings

logger = logging.getLogger("sales_common.adk_app")


def compaction_config(settings: ContextSettings) -> EventsCompactionConfig:
    """Sliding-window + token-threshold compaction (token-based takes priority)."""
    return EventsCompactionConfig(
        compaction_interval=settings.compaction_interval,
        overlap_size=settings.compaction_overlap,
        token_threshold=settings.compaction_token_threshold,
        event_retention_size=settings.compaction_retention,
    )


def cache_config(settings: ContextSettings) -> ContextCacheConfig:
    return ContextCacheConfig(
        cache_intervals=settings.cache_intervals,
        ttl_seconds=settings.cache_ttl_seconds,
        min_tokens=settings.cache_min_tokens,
    )


def build_app(
    name: str,
    root_agent,
    *,
    plugins: Optional[Sequence[BasePlugin]] = None,
    settings: Optional[ContextSettings] = None,
) -> App:
    """Build an ``App`` with compaction and caching enabled.

    ``name`` must match ``^[a-zA-Z][a-zA-Z0-9_-]*$``.
    """
    settings = settings or ContextSettings.from_env()
    app = App(
        name=name,
        root_agent=root_agent,
        plugins=list(plugins or []),
        events_compaction_config=compaction_config(settings),
        context_cache_config=cache_config(settings),
    )
    logger.info(
        "App %s: compaction every %d invocations (overlap %d) or >%d tokens; "
        "context cache ttl=%ds intervals=%d min_tokens=%d",
        name,
        settings.compaction_interval,
        settings.compaction_overlap,
        settings.compaction_token_threshold,
        settings.cache_ttl_seconds,
        settings.cache_intervals,
        settings.cache_min_tokens,
    )
    return app
