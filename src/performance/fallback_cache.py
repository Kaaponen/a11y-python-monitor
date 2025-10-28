"""
Simple in-memory cache fallback for performance module
"""

import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class InMemoryCache:
    """Simple in-memory cache fallback"""

    def __init__(self, default_ttl: int = 3600):
        self.cache: Dict[str, Any] = {}
        self.expiry: Dict[str, float] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
        self.sets = 0

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            # Check if key exists and not expired
            if key in self.cache:
                if key in self.expiry and time.time() > self.expiry[key]:
                    # Expired, remove it
                    del self.cache[key]
                    del self.expiry[key]
                    self.misses += 1
                    return None
                else:
                    self.hits += 1
                    return self.cache[key]
            else:
                self.misses += 1
                return None
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            self.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            self.cache[key] = value
            if ttl is None:
                ttl = self.default_ttl
            self.expiry[key] = time.time() + ttl
            self.sets += 1
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if key in self.cache:
                del self.cache[key]
            if key in self.expiry:
                del self.expiry[key]
            return True
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cache"""
        try:
            self.cache.clear()
            self.expiry.clear()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "type": "in_memory",
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "hit_rate": round(hit_rate, 2),
            "size": len(self.cache),
            "total_requests": total_requests,
        }

    def cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key
            for key, expiry_time in self.expiry.items()
            if current_time > expiry_time
        ]

        for key in expired_keys:
            if key in self.cache:
                del self.cache[key]
            del self.expiry[key]

        return len(expired_keys)


# Global fallback cache instance
_fallback_cache = None


def get_fallback_cache() -> InMemoryCache:
    """Get global fallback cache instance"""
    global _fallback_cache
    if _fallback_cache is None:
        _fallback_cache = InMemoryCache()
    return _fallback_cache


# Simple cache functions that work without Redis
async def get_cached_scan_result(
    url: str, scan_type: str = "axe"
) -> Optional[Dict[str, Any]]:
    """Get cached scan result (fallback)"""
    try:
        cache = get_fallback_cache()
        key = f"scan:{scan_type}:{url}"
        result = await cache.get(key)

        if result:
            logger.debug(f"Cache hit for {key}")
            return json.loads(result) if isinstance(result, str) else result
        else:
            logger.debug(f"Cache miss for {key}")
            return None

    except Exception as e:
        logger.error(f"Error getting cached scan result: {e}")
        return None


async def cache_scan_result(
    url: str, result: Dict[str, Any], scan_type: str = "axe", ttl: int = 3600
) -> bool:
    """Cache scan result (fallback)"""
    try:
        cache = get_fallback_cache()
        key = f"scan:{scan_type}:{url}"

        # Serialize result
        serialized = json.dumps(result) if not isinstance(result, str) else result

        success = await cache.set(key, serialized, ttl)
        if success:
            logger.debug(f"Cached scan result for {key}")

        return success

    except Exception as e:
        logger.error(f"Error caching scan result: {e}")
        return False


def cache_result(key_func=None, ttl: int = 3600):
    """Decorator for caching function results (fallback)"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                # Try to get from cache
                cache = get_fallback_cache()
                cached_result = await cache.get(cache_key)

                if cached_result is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return (
                        json.loads(cached_result)
                        if isinstance(cached_result, str)
                        else cached_result
                    )

                # Execute function and cache result
                result = await func(*args, **kwargs)

                # Cache the result
                serialized = (
                    json.dumps(result) if not isinstance(result, str) else result
                )
                await cache.set(cache_key, serialized, ttl)

                logger.debug(f"Function executed and cached: {cache_key}")
                return result

            except Exception as e:
                logger.error(f"Error in cache decorator: {e}")
                # Fallback to direct function execution
                return await func(*args, **kwargs)

        return wrapper

    return decorator
