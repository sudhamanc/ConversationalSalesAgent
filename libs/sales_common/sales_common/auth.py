"""Service-to-service authentication.

``SERVICE_AUTH=none`` (default, local compose / dev): no credentials attached.
``SERVICE_AUTH=gcp_id_token`` (Cloud Run): attach a Google-signed ID token whose
audience is the target service base URL; target services are deployed with
``--no-allow-unauthenticated`` so Cloud Run IAM enforces ``roles/run.invoker``.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional
from urllib.parse import urlsplit

import httpx

from .config import env_str

logger = logging.getLogger("sales_common.auth")

_TOKEN_TTL_SECONDS = 55 * 60  # Google ID tokens live 60 min; refresh 5 min early
_cache: dict[str, tuple[str, float]] = {}
_lock = threading.Lock()


def auth_mode() -> str:
    mode = env_str("SERVICE_AUTH", "none").lower()
    if mode not in {"none", "gcp_id_token"}:
        raise ValueError(f"SERVICE_AUTH must be 'none' or 'gcp_id_token', got {mode!r}")
    return mode


def audience_for(url: str) -> str:
    """Cloud Run audience is the service base URL (scheme + host)."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _default_fetcher(audience: str) -> str:
    import google.auth.transport.requests
    from google.oauth2 import id_token

    return id_token.fetch_id_token(google.auth.transport.requests.Request(), audience)


def get_id_token(audience: str, fetcher: Optional[Callable[[str], str]] = None) -> str:
    now = time.time()
    with _lock:
        cached = _cache.get(audience)
        if cached and cached[1] > now:
            return cached[0]
    token = (fetcher or _default_fetcher)(audience)
    with _lock:
        _cache[audience] = (token, now + _TOKEN_TTL_SECONDS)
    return token


def service_headers(url: str, fetcher: Optional[Callable[[str], str]] = None) -> dict[str, str]:
    """Headers for calling another internal service at ``url``."""
    if auth_mode() == "none":
        return {}
    return {"Authorization": f"Bearer {get_id_token(audience_for(url), fetcher)}"}


class ServiceAuth(httpx.Auth):
    """httpx auth flow that adds an ID token per request audience (no-op when disabled)."""

    def auth_flow(self, request: httpx.Request):
        if auth_mode() != "none":
            token = get_id_token(audience_for(str(request.url)))
            request.headers["Authorization"] = f"Bearer {token}"
        yield request
