"""Suorituskykyoptimointien moduuli

Sisältää:
- Redis-pohjainen caching (fallback to in-memory)
- API rate limiting 
- Connection pooling
- Memory management
"""

# Try Redis cache first, fallback to in-memory cache
try:
    from .cache import CacheManager, cache_result
except Exception:
    from .fallback_cache import cache_result
    CacheManager = None

from .rate_limiter import APIRateLimiter, rate_limit
from .connection_pool import ConnectionPoolManager
from .memory_optimizer import MemoryOptimizer

__all__ = [
    'CacheManager',
    'cache_result', 
    'APIRateLimiter',
    'rate_limit',
    'ConnectionPoolManager',
    'MemoryOptimizer'
]