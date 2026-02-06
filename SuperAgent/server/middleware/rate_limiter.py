"""
Token-bucket rate limiter scoped per session.

Enforces both per-minute and per-hour limits defined in config.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class _Bucket:
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.monotonic)


class RateLimiter:
    """Simple in-memory token-bucket rate limiter keyed by session ID."""

    def __init__(
        self,
        rpm: int = settings.rate_limit.requests_per_minute,
        rph: int = settings.rate_limit.requests_per_hour,
        burst: int = settings.rate_limit.burst_size,
    ):
        self._rpm = rpm
        self._rph = rph
        self._burst = burst
        self._minute_buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=float(burst))
        )
        self._hour_buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=float(rph))
        )

    def _refill(self, bucket: _Bucket, rate: float, cap: float) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(cap, bucket.tokens + elapsed * rate)
        bucket.last_refill = now

    def allow(self, session_id: str) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        # Per-minute check
        mb = self._minute_buckets[session_id]
        self._refill(mb, rate=self._rpm / 60.0, cap=float(self._burst))
        if mb.tokens < 1.0:
            logger.warning(f"Rate limit (per-minute) hit for session {session_id}")
            return False
        mb.tokens -= 1.0

        # Per-hour check
        hb = self._hour_buckets[session_id]
        self._refill(hb, rate=self._rph / 3600.0, cap=float(self._rph))
        if hb.tokens < 1.0:
            logger.warning(f"Rate limit (per-hour) hit for session {session_id}")
            mb.tokens += 1.0  # refund the minute token
            return False
        hb.tokens -= 1.0

        return True

    def cleanup_expired(self, max_age_seconds: float = 7200.0) -> None:
        """Remove buckets for sessions inactive longer than max_age_seconds."""
        now = time.monotonic()
        for store in (self._minute_buckets, self._hour_buckets):
            expired = [
                k for k, v in store.items() if now - v.last_refill > max_age_seconds
            ]
            for k in expired:
                del store[k]


# Module-level singleton
rate_limiter = RateLimiter()
