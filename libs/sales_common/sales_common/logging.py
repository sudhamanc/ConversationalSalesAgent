"""Logging setup and secret masking."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlsplit, urlunsplit


def setup_logging(service: str) -> logging.Logger:
    """Configure root logging once and return the service logger."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format=f"%(asctime)s %(levelname)s [{service}] %(name)s: %(message)s",
        )
    else:
        root.setLevel(level)
    return logging.getLogger(service)


def mask_url(url: str) -> str:
    """Mask the password component of a URL (e.g. a database DSN) for logging."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "<unparseable url>"
    if parts.password is None:
        return url
    user = parts.username or ""
    host = parts.hostname or ""
    port = f":{parts.port}" if parts.port else ""
    netloc = f"{user}:***@{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
