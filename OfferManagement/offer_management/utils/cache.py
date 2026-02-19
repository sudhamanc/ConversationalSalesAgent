"""
Simple in-memory cache with TTL for offer management results.

Caches offer lookups to reduce API calls and improve response time.
Default TTL: 1 hour (offers may change more frequently than serviceability).
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import threading
from .logger import get_logger

logger = get_logger(__name__)


class OfferCache:
    """Thread-safe in-memory cache with time-to-live (TTL)"""

    def __init__(self):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    self._hits += 1
                    return value
                else:
                    del self._cache[key]
                    self._misses += 1
            else:
                self._misses += 1
        return None

    def set(self, key: str, value: Any, ttl_hours: int = 1):
        with self._lock:
            expiry = datetime.now() + timedelta(hours=ttl_hours)
            self._cache[key] = (value, expiry)

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%"
            }


# Global cache instance
_cache = OfferCache()


def cache_result(key: str, value: Any, ttl_hours: int = 1):
    _cache.set(key, value, ttl_hours)


def get_cached_result(key: str) -> Optional[Any]:
    return _cache.get(key)


def clear_cache():
    _cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    return _cache.get_stats()
