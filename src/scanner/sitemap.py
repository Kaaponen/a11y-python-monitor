"""Sitemap processing with performance optimizations"""

import asyncio
import xml.etree.ElementTree as ET
from typing import List, Optional
from ..utils.logger import get_logger
from ..utils.exceptions import NetworkError, ScannerError
# Use fallback cache to avoid Redis connection issues
from ..performance.fallback_cache import get_fallback_cache
from ..performance.connection_pool import fetch_url
from ..performance.memory_optimizer import optimize_memory

logger = get_logger(__name__)


@optimize_memory(track_objects=True)
async def get_urls_from_sitemap(sitemap_url: str, 
                                prefix_filter: Optional[str] = None,
                                use_cache: bool = True) -> List[str]:
    """
    Hae URL:t sitemap.xml tiedostosta suorituskykyoptimoinneilla
    
    Args:
        sitemap_url: Sitemap URL
        prefix_filter: Suodata URL:t tällä etuliitteellä
        use_cache: Käytä välimuistia
        
    Returns:
        Lista URL:eja
        
    Raises:
        NetworkError: Jos sitemap haku epäonnistuu
        ScannerError: Jos XML parsing epäonnistuu
    """
    logger.info("Processing sitemap", extra={
        "sitemap_url": sitemap_url,
        "prefix_filter": prefix_filter,
        "use_cache": use_cache
    })
    
        # Try to get from cache first
    cache = get_fallback_cache()
    cache_key = f"sitemap:{sitemap_url}"
    cached_urls = await cache.get(cache_key)
    if cached_urls:
        logger.info(f"Retrieved {len(cached_urls)} URLs from cache for {sitemap_url}")
        return cached_urls
    
    # Fetch sitemap
    urls = []
    try:
        urls = await _parse_sitemap(sitemap_url, prefix_filter)
        
        # Cache results if successful
        if use_cache and urls:
            try:
                cache = get_fallback_cache()
                cache_key = f"sitemap:{sitemap_url}"
                await cache.set(cache_key, urls, ttl=7200)  # 2 hours
                logger.debug("Sitemap URLs cached", extra={
                    "sitemap_url": sitemap_url,
                    "url_count": len(urls),
                    "cache_ttl": 7200
                })
            except Exception as cache_error:
                logger.warning("Failed to cache sitemap URLs", extra={
                    "sitemap_url": sitemap_url,
                    "cache_error": str(cache_error)
                })
        
        logger.info("Sitemap processing completed", extra={
            "sitemap_url": sitemap_url,
            "url_count": len(urls),
            "cached": use_cache
        })
        
        return urls
        
    except Exception as e:
        logger.error("Sitemap processing failed", extra={
            "sitemap_url": sitemap_url,
            "error": str(e)
        })
        raise


async def _parse_sitemap(sitemap_url: str, prefix_filter: Optional[str] = None) -> List[str]:
    """
    Parse sitemap XML with connection pooling
    
    Args:
        sitemap_url: Sitemap URL
        prefix_filter: URL prefix filter
        
    Returns:
        List of URLs
    """
    urls = []
    
    try:
        # Use connection pool for fetching
        response = await fetch_url(sitemap_url, pool_name='sitemap_fetcher')
        
        if response.status != 200:
            raise NetworkError(f"Failed to fetch sitemap: HTTP {response.status}", sitemap_url, response.status)
        
        content = await response.read()
        root = ET.fromstring(content)
        
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        
        # Check if this is a sitemap index
        if root.tag.endswith("sitemapindex"):
            logger.debug("Processing sitemap index", extra={"sitemap_url": sitemap_url})
            
            # Process all sitemaps in the index
            sitemap_tasks = []
            for sitemap in root.findall("ns:sitemap", ns):
                loc = sitemap.find("ns:loc", ns)
                if loc is not None:
                    sitemap_tasks.append(_parse_sitemap(loc.text, prefix_filter))
            
            # Execute all sitemap parsing concurrently
            if sitemap_tasks:
                results = await asyncio.gather(*sitemap_tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, list):
                        urls.extend(result)
                    elif isinstance(result, Exception):
                        logger.warning("Sitemap parsing failed", extra={
                            "error": str(result)
                        })
        else:
            # Process regular sitemap
            logger.debug("Processing regular sitemap", extra={"sitemap_url": sitemap_url})
            
            for url_tag in root.findall("ns:url", ns):
                loc = url_tag.find("ns:loc", ns)
                if loc is not None:
                    url = loc.text
                    if not prefix_filter or url.startswith(prefix_filter):
                        urls.append(url)
        
        logger.debug("Sitemap parsed successfully", extra={
            "sitemap_url": sitemap_url,
            "urls_found": len(urls)
        })
        
        return urls
        
    except ET.ParseError as e:
        logger.error("XML parsing failed", extra={
            "sitemap_url": sitemap_url,
            "error": str(e)
        })
        raise ScannerError(f"Invalid XML in sitemap: {e}")
    
    except Exception as e:
        logger.error("Sitemap parsing error", extra={
            "sitemap_url": sitemap_url,
            "error": str(e)
        })
        raise NetworkError(f"Failed to process sitemap: {e}", sitemap_url)


# Legacy sync function for backwards compatibility
def get_urls_from_sitemap_sync(sitemap_url: str, prefix_filter: Optional[str] = None) -> List[str]:
    """
    Synchronous version for backwards compatibility
    
    Args:
        sitemap_url: Sitemap URL
        prefix_filter: URL prefix filter
        
    Returns:
        List of URLs
    """
    logger.warning("Using legacy sync sitemap function", extra={
        "sitemap_url": sitemap_url
    })
    
    return asyncio.run(get_urls_from_sitemap(sitemap_url, prefix_filter, use_cache=False))
