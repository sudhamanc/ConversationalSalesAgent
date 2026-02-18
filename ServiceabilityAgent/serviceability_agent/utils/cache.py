"""
Simple in-memory cache with TTL for serviceability results.

Caches address lookups to reduce API calls and improve response time.
Default TTL: 24 hours
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import threading
from .logger import get_logger

logger = get_logger(__name__)


class ServiceabilityCache:
    """Thread-safe in-memory cache with time-to-live (TTL)"""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    self._hits += 1
                    logger.debug(f"Cache HIT: {key}")
                    return value
                else:
                    # Expired, remove it
                    del self._cache[key]
                    self._misses += 1
                    logger.debug(f"Cache EXPIRED: {key}")
            else:
                self._misses += 1
                logger.debug(f"Cache MISS: {key}")
        
        return None
    
    def set(self, key: str, value: Any, ttl_hours: int = 24):
        """
        Cache a value with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_hours: Time to live in hours (default: 24)
        """
        with self._lock:
            expiry = datetime.now() + timedelta(hours=ttl_hours)
            self._cache[key] = (value, expiry)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_hours}h)")
    
    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info(f"Cache cleared: {count} entries removed")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats (size, hits, misses, hit_rate)
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%"
            }
    
    def cleanup_expired(self):
        """Remove all expired entries from cache"""
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, (_, expiry) in self._cache.items()
                if now >= expiry
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cache cleanup: removed {len(expired_keys)} expired entries")


# Global cache instance
_cache = ServiceabilityCache()


def cache_result(key: str, value: Any, ttl_hours: int = 24):
    """
    Cache a serviceability result.
    
    Args:
        key: Cache key (typically address-based)
        value: Serviceability result to cache
        ttl_hours: Time to live in hours
    """
    _cache.set(key, value, ttl_hours)


def get_cached_result(key: str) -> Optional[Any]:
    """
    Get cached serviceability result.
    
    Args:
        key: Cache key
        
    Returns:
        Cached result or None
    """
    return _cache.get(key)


def clear_cache():
    """Clear entire cache"""
    _cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return _cache.get_stats()


def cleanup_cache():
    """Remove expired entries"""
    _cache.cleanup_expired()
