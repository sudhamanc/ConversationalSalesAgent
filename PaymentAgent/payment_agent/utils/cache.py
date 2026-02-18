"""
Caching utilities for the Payment Agent.

Provides persistent caching for expensive operations like credit checks.
"""

import os
from typing import Any, Optional, Callable
from functools import wraps
import diskcache as dc

# Cache configuration from environment
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")


def get_cache() -> Optional[dc.Cache]:
    """
    Get the cache instance.
    
    Returns:
        Cache instance if enabled, None otherwise
    """
    if not CACHE_ENABLED:
        return None
    
    os.makedirs(CACHE_DIR, exist_ok=True)
    return dc.Cache(CACHE_DIR)


def cache_result(ttl: int = CACHE_TTL_SECONDS):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
    
    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not CACHE_ENABLED:
                return func(*args, **kwargs)
            
            cache = get_cache()
            if cache is None:
                return func(*args, **kwargs)
            
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, expire=ttl)
            
            return result
        
        return wrapper
    return decorator
