"""Connection Pool Manager

Hallitsee HTTP-yhteyksien pooleja tehokkaampaan verkkoliikenteeseen.
Vähentää yhteyksien luomisen overhead-kustannuksia ja parantaa suorituskykyä.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Set
import time
from contextlib import asynccontextmanager

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

from ..utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConnectionStats:
    """Yhteyspoolien tilastojen seuranta"""
    
    def __init__(self):
        self.connections_created = 0
        self.connections_reused = 0
        self.connections_closed = 0
        self.active_connections = 0
        self.failed_connections = 0
        self.total_requests = 0
        self.total_bytes_sent = 0
        self.total_bytes_received = 0
    
    @property
    def reuse_rate(self) -> float:
        """Yhteyksien uudelleenkäytön prosenttiosuus"""
        total = self.connections_created + self.connections_reused
        return (self.connections_reused / total * 100) if total > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Muunna tilastot dictionary:ksi"""
        return {
            'connections_created': self.connections_created,
            'connections_reused': self.connections_reused,
            'connections_closed': self.connections_closed,
            'active_connections': self.active_connections,
            'failed_connections': self.failed_connections,
            'total_requests': self.total_requests,
            'total_bytes_sent': self.total_bytes_sent,
            'total_bytes_received': self.total_bytes_received,
            'reuse_rate': round(self.reuse_rate, 2)
        }


class ConnectionPoolManager:
    """HTTP-yhteyspoolien hallinta"""
    
    def __init__(self,
                 max_connections: int = 100,
                 max_connections_per_host: int = 10,
                 connection_timeout: int = 30,
                 read_timeout: int = 60,
                 keepalive_timeout: int = 30,
                 ttl_dns_cache: int = 300,
                 enable_cleanup: bool = True,
                 cleanup_interval: int = 60):
        """
        Alustaa connection pool managerin
        
        Args:
            max_connections: Maksimi yhteyksiä yhteensä
            max_connections_per_host: Maksimi yhteyksiä per host
            connection_timeout: Yhteyden timeout sekunnissa
            read_timeout: Lukutimeout sekunnissa  
            keepalive_timeout: Keep-alive timeout
            ttl_dns_cache: DNS-cachen elinaika
            enable_cleanup: Aktivoi automaattinen siivous
            cleanup_interval: Siivouksen aikaväli sekunnissa
        """
        if not AIOHTTP_AVAILABLE:
            raise ConfigurationError("aiohttp library not available. Install with: pip install aiohttp")
        
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout
        self.keepalive_timeout = keepalive_timeout
        self.ttl_dns_cache = ttl_dns_cache
        self.enable_cleanup = enable_cleanup
        self.cleanup_interval = cleanup_interval
        
        # Yhteyspoolit eri käyttötarkoituksille
        self.pools: Dict[str, aiohttp.ClientSession] = {}
        self.pool_configs: Dict[str, Dict[str, Any]] = {}
        
        # Tilastot
        self.stats = ConnectionStats()
        
        # Siivous task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_initialized = False
        
        logger.info("ConnectionPoolManager initialized", extra={
            "max_connections": max_connections,
            "max_connections_per_host": max_connections_per_host,
            "connection_timeout": connection_timeout
        })
    
    async def initialize(self) -> None:
        """Alusta connection poolit"""
        if self._is_initialized:
            return
        
        try:
            # Luo oletuspooli web-skannauksille
            await self.create_pool(
                'web_scanner',
                max_connections=self.max_connections,
                max_connections_per_host=self.max_connections_per_host,
                user_agent='A11y-Scanner/1.0 (Web Accessibility Scanner)'
            )
            
            # Luo pooli API-kutsuille
            await self.create_pool(
                'api_client',
                max_connections=20,
                max_connections_per_host=5,
                user_agent='A11y-Scanner/1.0 (API Client)'
            )
            
            # Luo pooli sitemap-hauille
            await self.create_pool(
                'sitemap_fetcher',
                max_connections=10,
                max_connections_per_host=2,
                user_agent='A11y-Scanner/1.0 (Sitemap Fetcher)'
            )
            
            # Käynnistä siivous jos aktivoitu
            if self.enable_cleanup:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self._is_initialized = True
            
            logger.info("Connection pools initialized", extra={
                "pools_created": len(self.pools)
            })
            
        except Exception as e:
            logger.error("Failed to initialize connection pools", extra={
                "error": str(e)
            })
            raise ConfigurationError(f"Connection pool initialization failed: {e}")
    
    async def create_pool(self,
                          pool_name: str,
                          max_connections: int = None,
                          max_connections_per_host: int = None,
                          user_agent: str = None,
                          headers: Dict[str, str] = None,
                          cookies: Dict[str, str] = None) -> None:
        """
        Luo nimetty yhteyspools
        
        Args:
            pool_name: Poolin nimi
            max_connections: Maksimi yhteyksiä (None = käytä oletusta)
            max_connections_per_host: Maksimi yhteyksiä per host
            user_agent: User-Agent string
            headers: Ylimääräiset headerit
            cookies: Evästeet
        """
        if pool_name in self.pools:
            logger.warning("Pool already exists", extra={"pool_name": pool_name})
            return
        
        # Määritä yhteyden asetukset
        connector = aiohttp.TCPConnector(
            limit=max_connections or self.max_connections,
            limit_per_host=max_connections_per_host or self.max_connections_per_host,
            ttl_dns_cache=self.ttl_dns_cache,
            keepalive_timeout=self.keepalive_timeout,
            enable_cleanup_closed=True
        )
        
        # Määritä timeout-asetukset
        timeout = aiohttp.ClientTimeout(
            total=self.connection_timeout + self.read_timeout,
            connect=self.connection_timeout,
            sock_read=self.read_timeout
        )
        
        # Määritä headerit
        default_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        if user_agent:
            default_headers['User-Agent'] = user_agent
        
        if headers:
            default_headers.update(headers)
        
        # Luo session
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=default_headers,
            cookies=cookies,
            auto_decompress=True
        )
        
        self.pools[pool_name] = session
        self.pool_configs[pool_name] = {
            'max_connections': max_connections or self.max_connections,
            'max_connections_per_host': max_connections_per_host or self.max_connections_per_host,
            'created_at': time.time(),
            'user_agent': user_agent
        }
        
        logger.info("Connection pool created", extra={
            "pool_name": pool_name,
            "max_connections": max_connections or self.max_connections,
            "max_connections_per_host": max_connections_per_host or self.max_connections_per_host
        })
    
    @asynccontextmanager
    async def get_session(self, pool_name: str = 'web_scanner'):
        """
        Hae session context managerina
        
        Args:
            pool_name: Poolin nimi
            
        Yields:
            aiohttp.ClientSession: HTTP-session
        """
        if not self._is_initialized:
            await self.initialize()
        
        if pool_name not in self.pools:
            raise ValueError(f"Pool '{pool_name}' not found")
        
        session = self.pools[pool_name]
        
        try:
            self.stats.active_connections += 1
            yield session
        except Exception as e:
            self.stats.failed_connections += 1
            logger.error("Session error", extra={
                "pool_name": pool_name,
                "error": str(e)
            })
            raise
        finally:
            self.stats.active_connections -= 1
    
    async def make_request(self,
                           method: str,
                           url: str,
                           pool_name: str = 'web_scanner',
                           **kwargs) -> aiohttp.ClientResponse:
        """
        Tee HTTP-pyyntö määrätyllä poolilla
        
        Args:
            method: HTTP-metodi
            url: Kohde-URL
            pool_name: Käytettävä pool
            **kwargs: Ylimääräiset parametrit requestille
            
        Returns:
            HTTP-vastaus
        """
        async with self.get_session(pool_name) as session:
            self.stats.total_requests += 1
            
            try:
                response = await session.request(method, url, **kwargs)
                
                # Päivitä tilastot
                if hasattr(response, 'content') and hasattr(response.content, 'total_bytes'):
                    self.stats.total_bytes_received += response.content.total_bytes
                
                logger.debug("HTTP request completed", extra={
                    "method": method,
                    "url": url,
                    "status": response.status,
                    "pool_name": pool_name
                })
                
                return response
                
            except Exception as e:
                self.stats.failed_connections += 1
                logger.error("HTTP request failed", extra={
                    "method": method,
                    "url": url,
                    "pool_name": pool_name,
                    "error": str(e)
                })
                raise
    
    async def close_pool(self, pool_name: str) -> bool:
        """
        Sulje nimetty pool
        
        Args:
            pool_name: Suljettava pool
            
        Returns:
            True jos sulkeminen onnistui
        """
        if pool_name not in self.pools:
            return False
        
        try:
            session = self.pools[pool_name]
            await session.close()
            
            del self.pools[pool_name]
            del self.pool_configs[pool_name]
            
            self.stats.connections_closed += 1
            
            logger.info("Connection pool closed", extra={"pool_name": pool_name})
            return True
            
        except Exception as e:
            logger.error("Failed to close connection pool", extra={
                "pool_name": pool_name,
                "error": str(e)
            })
            return False
    
    async def close_all(self) -> None:
        """Sulje kaikki poolit"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        for pool_name in list(self.pools.keys()):
            await self.close_pool(pool_name)
        
        self._is_initialized = False
        logger.info("All connection pools closed")
    
    async def _cleanup_loop(self) -> None:
        """Automaattinen siivous-silmukka"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup loop error", extra={"error": str(e)})
    
    async def _cleanup_connections(self) -> None:
        """Siivoa vanhat yhteydet"""
        current_time = time.time()
        
        for pool_name, session in self.pools.items():
            try:
                # Connector cleanup jos mahdollista
                if hasattr(session.connector, '_cleanup'):
                    await session.connector._cleanup()
                
                logger.debug("Pool cleanup completed", extra={
                    "pool_name": pool_name
                })
                
            except Exception as e:
                logger.error("Pool cleanup failed", extra={
                    "pool_name": pool_name,
                    "error": str(e)
                })
    
    async def get_pool_stats(self, pool_name: str = None) -> Dict[str, Any]:
        """
        Hae poolin tilastot
        
        Args:
            pool_name: Poolin nimi (None = kaikki poolit)
            
        Returns:
            Tilastotiedot
        """
        if pool_name and pool_name in self.pools:
            session = self.pools[pool_name]
            config = self.pool_configs[pool_name]
            
            connector_stats = {}
            if hasattr(session.connector, '_conns'):
                connector_stats = {
                    'open_connections': len(session.connector._conns),
                    'acquired_connections': len(getattr(session.connector, '_acquired', [])),
                }
            
            return {
                'pool_name': pool_name,
                'config': config,
                'connector_stats': connector_stats,
                'session_closed': session.closed
            }
        
        # Kaikki poolit
        all_stats = {
            'global_stats': self.stats.to_dict(),
            'pools': {}
        }
        
        for name in self.pools:
            all_stats['pools'][name] = await self.get_pool_stats(name)
        
        return all_stats


# Globaali connection pool manager
connection_pool_manager = ConnectionPoolManager()


# Convenience funktiot

async def get_web_session():
    """Hae web-skannauspoolin session"""
    return connection_pool_manager.get_session('web_scanner')


async def get_api_session():
    """Hae API-poolin session"""
    return connection_pool_manager.get_session('api_client')


async def fetch_url(url: str, method: str = 'GET', pool_name: str = 'web_scanner', **kwargs):
    """
    Hae URL connection poolin kautta
    
    Args:
        url: Kohde-URL
        method: HTTP-metodi
        pool_name: Käytettävä pool
        **kwargs: Request-parametrit
        
    Returns:
        Response objekti
    """
    return await connection_pool_manager.make_request(method, url, pool_name, **kwargs)


async def fetch_multiple_urls(urls: list, pool_name: str = 'web_scanner', max_concurrent: int = 10):
    """
    Hae useita URL:eja samanaikaisesti
    
    Args:
        urls: Lista URL:eja
        pool_name: Käytettävä pool
        max_concurrent: Maksimi samanaikaisia pyyntöjä
        
    Returns:
        Lista response objekteja
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_semaphore(url):
        async with semaphore:
            return await fetch_url(url, pool_name=pool_name)
    
    tasks = [fetch_with_semaphore(url) for url in urls]
    return await asyncio.gather(*tasks, return_exceptions=True)