"""
Caching utility for Product Agent.

Provides TTL-based caching for query results to reduce redundant RAG queries.
"""

import time
from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TTLCache:
    """Time-to-live cache with size limit"""
    
    def __init__(self, ttl_hours: int = 24, max_size: int = 1000):
        """
        Initialize TTL cache.
        
        Args:
            ttl_hours: Time-to-live in hours (default 24)
            max_size: Maximum number of entries (default 1000)
        """
        self.ttl_seconds = ttl_hours * 3600
        self.max_size = max_size
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        
        logger.info(f"Cache initialized: TTL={ttl_hours}h, max_size={max_size}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if exists and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.misses += 1
            logger.debug(f"Cache MISS: {key}")
            return None
        
        value, timestamp = self.cache[key]
        
        # Check if expired
        if time.time() - timestamp > self.ttl_seconds:
            del self.cache[key]
            self.misses += 1
            logger.debug(f"Cache EXPIRED: {key}")
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        logger.debug(f"Cache HIT: {key}")
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with current timestamp.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # Remove oldest entry if at max size
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Cache EVICTED (size limit): {oldest_key}")
        
        self.cache[key] = (value, time.time())
        self.cache.move_to_end(key)
        logger.debug(f"Cache SET: {key}")
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "ttl_hours": self.ttl_seconds / 3600
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Cache cleanup: removed {len(expired_keys)} expired entries")
        
        return len(expired_keys)


# Global cache instance
import os
TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))
MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))

_global_cache = TTLCache(ttl_hours=TTL_HOURS, max_size=MAX_SIZE)


def cache_result(key: str, value: Any) -> None:
    """Cache a result with the given key"""
    _global_cache.set(key, value)


def get_cached_result(key: str) -> Optional[Any]:
    """Get cached result by key"""
    return _global_cache.get(key)


def clear_cache() -> None:
    """Clear all cached results"""
    _global_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return _global_cache.get_stats()


def cleanup_cache() -> int:
    """Cleanup expired cache entries"""
    return _global_cache.cleanup_expired()
