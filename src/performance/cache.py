"""Redis-pohjainen välimuistijärjestelmä

Tarjoaa tehokasta cachingía skannaustulosten tallentamiseen ja hakemiseen.
Vähentää toistuvien skannausten suoritusaikaa merkittävästi.
"""

import json
import hashlib
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, List
from functools import wraps
import pickle
import gzip

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..utils.exceptions import ConfigurationError
from ..utils.monitoring import PerformanceMonitor

logger = logging.getLogger(__name__)


class CacheStats:
    """Cache-tilastojen kerääminen"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
    
    @property
    def hit_rate(self) -> float:
        """Osumien prosenttiosuus"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Muunna statistiikka dictionary:ksi"""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'deletes': self.deletes,
            'errors': self.errors,
            'hit_rate': round(self.hit_rate, 2)
        }


class CacheManager:
    """Redis-pohjainen välimuistin hallinta"""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379/0",
                 default_ttl: int = 3600,
                 key_prefix: str = "a11y_scanner:",
                 compression: bool = True,
                 max_retries: int = 3):
        """
        Alustaa cache managerin
        
        Args:
            redis_url: Redis-palvelimen URL
            default_ttl: Oletusarvoinen Time-To-Live sekunnissa
            key_prefix: Avainten etuliite
            compression: Käytä gzip-pakkausta
            max_retries: Uudelleenyrityskertojen määrä
        """
        if not REDIS_AVAILABLE:
            raise ConfigurationError("Redis library not available. Install with: pip install redis")
        
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.compression = compression
        self.max_retries = max_retries
        self.redis_client: Optional[redis.Redis] = None
        self.stats = CacheStats()
        self.monitor = PerformanceMonitor()
        self._connection_pool = None
        
        logger.info("CacheManager initialized", extra={
            "redis_url": redis_url,
            "default_ttl": default_ttl,
            "compression": compression
        })
    
    async def connect(self) -> None:
        """Muodosta yhteys Redis-palvelimeen"""
        try:
            # Luo connection pool
            self._connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                decode_responses=False  # Käytetään binary dataa
            )
            
            self.redis_client = redis.Redis(
                connection_pool=self._connection_pool,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Testaa yhteys
            await self.redis_client.ping()
            
            logger.info("Connected to Redis successfully", extra={
                "redis_url": self.redis_url
            })
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.info("Falling back to in-memory cache")
            self.redis_client = None
            self._fallback_cache = {}
            self._fallback_expiry = {}
            raise ConfigurationError(f"Redis connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Sulje yhteys Redis-palvelimeen"""
        if self.redis_client:
            await self.redis_client.close()
            if self._connection_pool:
                await self._connection_pool.disconnect()
            logger.info("Disconnected from Redis")
    
    def _generate_key(self, key: str) -> str:
        """Generoi cache-avain etuliitteellä"""
        return f"{self.key_prefix}{key}"
    
    def _hash_key(self, data: Any) -> str:
        """Luo hash kompleksisesta datasta"""
        if isinstance(data, (dict, list)):
            serialized = json.dumps(data, sort_keys=True)
        else:
            serialized = str(data)
        
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialisoi data tallennusta varten"""
        try:
            # Lisää metadata
            cache_data = {
                'data': data,
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0'
            }
            
            serialized = pickle.dumps(cache_data)
            
            if self.compression:
                serialized = gzip.compress(serialized)
            
            return serialized
            
        except Exception as e:
            logger.error("Data serialization failed", extra={
                "error": str(e)
            })
            raise
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialisoi data cache:sta"""
        try:
            if self.compression:
                data = gzip.decompress(data)
            
            cache_data = pickle.loads(data)
            
            # Validoi metadata
            if not isinstance(cache_data, dict) or 'data' not in cache_data:
                raise ValueError("Invalid cache data format")
            
            return cache_data['data']
            
        except Exception as e:
            logger.error("Data deserialization failed", extra={
                "error": str(e)
            })
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Hae arvo cache:sta
        
        Args:
            key: Cache-avain
            
        Returns:
            Cachattu arvo tai None jos ei löydy
        """
        if not self.redis_client:
            await self.connect()
        
        cache_key = self._generate_key(key)
        
        try:
            with self.monitor.measure_time("cache_get"):
                data = await self.redis_client.get(cache_key)
            
            if data is None:
                self.stats.misses += 1
                logger.debug("Cache miss", extra={"key": key})
                return None
            
            result = self._deserialize_data(data)
            self.stats.hits += 1
            
            logger.debug("Cache hit", extra={
                "key": key,
                "data_size": len(data)
            })
            
            return result
            
        except Exception as e:
            self.stats.errors += 1
            logger.error("Cache get failed", extra={
                "key": key,
                "error": str(e)
            })
            return None
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[int] = None) -> bool:
        """
        Tallenna arvo cache:een
        
        Args:
            key: Cache-avain
            value: Tallennettava arvo
            ttl: Time-to-live sekunnissa
            
        Returns:
            True jos tallennus onnistui
        """
        if not self.redis_client:
            await self.connect()
        
        cache_key = self._generate_key(key)
        ttl = ttl or self.default_ttl
        
        try:
            serialized_data = self._serialize_data(value)
            
            with self.monitor.measure_time("cache_set"):
                await self.redis_client.setex(cache_key, ttl, serialized_data)
            
            self.stats.sets += 1
            
            logger.debug("Cache set successful", extra={
                "key": key,
                "ttl": ttl,
                "data_size": len(serialized_data)
            })
            
            return True
            
        except Exception as e:
            self.stats.errors += 1
            logger.error("Cache set failed", extra={
                "key": key,
                "error": str(e)
            })
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Poista arvo cache:sta
        
        Args:
            key: Cache-avain
            
        Returns:
            True jos poisto onnistui
        """
        if not self.redis_client:
            await self.connect()
        
        cache_key = self._generate_key(key)
        
        try:
            with self.monitor.measure_time("cache_delete"):
                result = await self.redis_client.delete(cache_key)
            
            self.stats.deletes += 1
            
            logger.debug("Cache delete", extra={
                "key": key,
                "deleted": bool(result)
            })
            
            return bool(result)
            
        except Exception as e:
            self.stats.errors += 1
            logger.error("Cache delete failed", extra={
                "key": key,
                "error": str(e)
            })
            return False
    
    async def exists(self, key: str) -> bool:
        """Tarkista onko avain cache:ssa"""
        if not self.redis_client:
            await self.connect()
        
        cache_key = self._generate_key(key)
        
        try:
            result = await self.redis_client.exists(cache_key)
            return bool(result)
        except Exception as e:
            logger.error("Cache exists check failed", extra={
                "key": key,
                "error": str(e)
            })
            return False
    
    async def clear(self, pattern: str = "*") -> int:
        """
        Tyhjennä cache annetun mallin mukaan
        
        Args:
            pattern: Redis pattern (oletuksena kaikki)
            
        Returns:
            Poistettujen avainten määrä
        """
        if not self.redis_client:
            await self.connect()
        
        search_pattern = self._generate_key(pattern)
        
        try:
            keys = await self.redis_client.keys(search_pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info("Cache cleared", extra={
                    "pattern": pattern,
                    "deleted_keys": deleted
                })
                return deleted
            return 0
            
        except Exception as e:
            logger.error("Cache clear failed", extra={
                "pattern": pattern,
                "error": str(e)
            })
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Hae cache-tilastot"""
        stats = self.stats.to_dict()
        
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                stats.update({
                    'redis_connected_clients': info.get('connected_clients', 0),
                    'redis_used_memory': info.get('used_memory_human', '0B'),
                    'redis_total_commands_processed': info.get('total_commands_processed', 0)
                })
            except Exception as e:
                logger.error("Failed to get Redis stats", extra={"error": str(e)})
        
        return stats


# Globaali cache manager instance
cache_manager = CacheManager()


def cache_result(key_func=None, ttl=None, skip_cache=None):
    """
    Decorator skannaustulosten cachingiin
    
    Args:
        key_func: Funktio cache-avaimen generointiin
        ttl: Time-to-live sekunnissa  
        skip_cache: Funktio joka määrittää ohitetaanko cache
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generoi cache-avain
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Oletusavain funktionnimestä ja argumenteista
                key_data = {
                    'function': func.__name__,
                    'args': args,
                    'kwargs': kwargs
                }
                cache_key = cache_manager._hash_key(key_data)
            
            # Tarkista ohitetaanko cache
            if skip_cache and skip_cache(*args, **kwargs):
                logger.debug("Cache skipped", extra={"function": func.__name__})
                return await func(*args, **kwargs)
            
        try:
            # Yritä hakea cache:sta
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit for function", extra={
                    "function": func.__name__,
                    "cache_key": cache_key
                })
                return cached_result
        except Exception as e:
            logger.warning(f"Cache get failed, falling back to function execution: {e}")
            # Jos cache epäonnistuu, suorita funktio suoraan
            return await func(*args, **kwargs)
            
            # Suorita funktio ja tallenna tulos
            result = await func(*args, **kwargs)
            
            if result is not None:
                await cache_manager.set(cache_key, result, ttl)
                logger.debug("Result cached", extra={
                    "function": func.__name__,
                    "cache_key": cache_key
                })
            
            return result
        
        return wrapper
    return decorator


# Apufunktiot eri cache-strategioille

async def cache_scan_result(url: str, scan_type: str, result: Any, ttl: int = 3600):
    """Cache skannauksen tulos"""
    key = f"scan:{scan_type}:{cache_manager._hash_key(url)}"
    return await cache_manager.set(key, result, ttl)


async def get_cached_scan_result(url: str, scan_type: str) -> Optional[Any]:
    """Hae cachattu skannauksen tulos"""
    key = f"scan:{scan_type}:{cache_manager._hash_key(url)}"
    return await cache_manager.get(key)


async def cache_sitemap_urls(sitemap_url: str, urls: List[str], ttl: int = 7200):
    """Cache sitemap URL:t"""
    key = f"sitemap:{cache_manager._hash_key(sitemap_url)}"
    return await cache_manager.set(key, urls, ttl)


async def get_cached_sitemap_urls(sitemap_url: str) -> Optional[List[str]]:
    """Hae cachatut sitemap URL:t"""
    key = f"sitemap:{cache_manager._hash_key(sitemap_url)}"
    return await cache_manager.get(key)