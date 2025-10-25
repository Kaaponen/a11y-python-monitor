"""Core accessibility scanning functionality using Playwright and axe-core"""

import asyncio
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright
from ..utils.logger import get_logger, log_performance
from ..utils.exceptions import ScannerError, BrowserError, NetworkError, TimeoutError
from ..utils.health_monitor import get_health_monitor
from ..security.input_validation import get_security_validator
from ..security.rate_limiting import get_rate_limiter

# Try to import Redis cache, fallback to in-memory cache
try:
    from ..performance.cache import CacheManager
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

# Always use fallback cache to avoid Redis connection issues
from ..performance.fallback_cache import cache_result, get_cached_scan_result, cache_scan_result

from ..performance.memory_optimizer import optimize_memory, track_scan_result

# Screenshot capture
from ..reports.screenshots import create_screenshot_capture


# Logger for this module
logger = get_logger(__name__)
health_monitor = get_health_monitor()
security_validator = get_security_validator()
rate_limiter = get_rate_limiter()


@optimize_memory(track_objects=True)
@cache_result(
    key_func=lambda url, timeout=30, capture_screenshots=False, **kwargs: f"axe_scan:{url}:{timeout}:{capture_screenshots}",
    ttl=3600  # Cache results for 1 hour
)
@log_performance
async def run_axe(url: str, 
                  timeout: int = 30, 
                  client_id: Optional[str] = None, 
                  use_cache: bool = True,
                  capture_screenshots: bool = False,
                  screenshot_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Skannaa sivun saavutettavuuden käyttäen axe-corea
    
    Args:
        url: Skannattavan sivun URL
        timeout: Aikakatkaisu sekunteina
        client_id: Client ID for rate limiting
        use_cache: Käytä välimuistia
        capture_screenshots: Ota kuvakaappauksia virheellisistä elementeistä
        screenshot_config: Kuvakaappausten konfiguraatio
        
    Returns:
        Axe-core tulokset dict muodossa, mahdollisesti kuvakaappausten kanssa
        
    Raises:
        ScannerError: Jos skannaus epäonnistuu
        BrowserError: Jos selainongelmat
        NetworkError: Jos verkko-ongelmat
        TimeoutError: Jos aikakatkaisu
        SecurityError: Jos turvallisuusvalidointi epäonnistuu
    """
    scan_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Generate client ID if not provided
    if client_id is None:
        client_id = f"scanner_{hash(url) % 10000}"
    
    # Check cache first if enabled
    if use_cache:
        cached_result = await get_cached_scan_result(url, "axe")
        if cached_result:
            logger.info("Returning cached scan result", extra={
                "url": url,
                "scan_id": scan_id,
                "cache_hit": True
            })
            # track_scan_result(cached_result, "axe_cached") # Temporarily disabled due to weak reference issue
            return cached_result
    
    # Rate limiting check
    allowed, reason = rate_limiter.check_rate_limit(client_id, "scan")
    if not allowed:
        logger.warning("Rate limit exceeded", extra={
            "client_id": client_id,
            "url": url,
            "reason": reason
        })
        raise ScannerError(f"Rate limit exceeded: {reason}")
    
    # Aloita health monitoring
    health_monitor.start_scan(scan_id, url)
    
    # Security validation
    try:
        validation_result = security_validator.validate_url(url, allow_private=False)
        if not validation_result['valid']:
            security_issues = ', '.join(validation_result['security_issues'])
            logger.error("URL security validation failed", extra={
                "url": url,
                "scan_id": scan_id,
                "security_issues": validation_result['security_issues']
            })
            health_monitor.fail_scan(scan_id, "security_validation_failed")
            raise ScannerError(f"URL security validation failed: {security_issues}")
    except Exception as e:
        if "SecurityError" in str(type(e)):
            raise
        # Fallback to basic validation
        from ..utils.validators import is_valid_url
        if not is_valid_url(url):
            logger.error("Invalid URL provided", extra={
                "url": url,
                "scan_id": scan_id,
                "error_type": "validation_error"
            })
            health_monitor.fail_scan(scan_id, "validation_error")
            raise ScannerError(f"Invalid URL: {url}")
    
    logger.info("Starting accessibility scan", extra={
        "url": url,
        "scan_id": scan_id,
        "timeout": timeout
    })
    
    try:
        async with async_playwright() as p:
            # Käynnistä selain
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="SaavutettavuusSkanneri/1.0"
            )
            page = await context.new_page()
            
            # Aseta timeout
            page.set_default_timeout(timeout * 1000)  # Muunna sekunneista millisekunneiksi
            
            try:
                # Siirry sivulle
                response = await page.goto(url, wait_until='networkidle')
                
                if not response or response.status >= 400:
                    health_monitor.fail_scan(scan_id, "network_error")
                    raise NetworkError(f"HTTP {response.status if response else 'No response'}", url, response.status if response else None)
                
                # Lataa axe-core
                axe_js_url = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.2/axe.min.js"
                await page.add_script_tag(url=axe_js_url)
                
                # Suorita axe-analyysi
                axe_results = await page.evaluate("""
                    () => {
                        return new Promise((resolve, reject) => {
                            axe.run((err, results) => {
                                if (err) reject(err);
                                else resolve(results);
                            });
                        });
                    }
                """)
                
                duration = time.time() - start_time
                violation_count = len(axe_results.get('violations', []))
                
                # Capture screenshots if requested
                if capture_screenshots and violation_count > 0:
                    await _capture_violation_screenshots(
                        page, 
                        axe_results, 
                        url, 
                        scan_id, 
                        screenshot_config or {}
                    )
                
                # Merkitse skannaus onnistuneeksi
                health_monitor.complete_scan(scan_id, violation_count)
                
                # Cache results if successful and caching enabled
                if use_cache and axe_results:
                    try:
                        await cache_scan_result(url, "axe", axe_results, ttl=3600)
                        logger.debug("Scan result cached", extra={
                            "url": url,
                            "scan_id": scan_id,
                            "cache_ttl": 3600
                        })
                    except Exception as cache_error:
                        logger.warning("Failed to cache scan result", extra={
                            "url": url,
                            "scan_id": scan_id,
                            "cache_error": str(cache_error)
                        })
                
                # Track result for memory optimization
                # track_scan_result(axe_results, "axe") # Temporarily disabled due to weak reference issue
                
                logger.info("Scan completed successfully", extra={
                    "url": url,
                    "scan_id": scan_id,
                    "duration": duration,
                    "violation_count": violation_count,
                    "pass_count": len(axe_results.get('passes', [])),
                    "cached": use_cache
                })
                
                return axe_results
                
            except Exception as e:
                duration = time.time() - start_time
                
                if "Timeout" in str(e):
                    logger.error("Scan timed out", extra={
                        "url": url,
                        "scan_id": scan_id,
                        "duration": duration,
                        "timeout": timeout
                    })
                    health_monitor.fail_scan(scan_id, "timeout_error")
                    raise TimeoutError(f"Scan timed out after {timeout}s", timeout, "accessibility_scan")
                else:
                    logger.error("Browser error during scan", extra={
                        "url": url,
                        "scan_id": scan_id,
                        "duration": duration,
                        "error_type": type(e).__name__
                    }, exc_info=True)
                    health_monitor.fail_scan(scan_id, "browser_error")
                    raise BrowserError(f"Browser error: {str(e)}", "chromium", url)
            
            finally:
                await browser.close()
                
    except Exception as e:
        duration = time.time() - start_time
        
        logger.error("Scan failed with unexpected error", extra={
            "url": url,
            "scan_id": scan_id,
            "duration": duration,
            "error_type": type(e).__name__
        }, exc_info=True)
        
        # Re-raise jos jo oikea tyyppi
        if isinstance(e, (ScannerError, BrowserError, NetworkError, TimeoutError)):
            raise
        else:
            health_monitor.fail_scan(scan_id, "unexpected_error")
            raise ScannerError(f"Unexpected error during scan: {str(e)}")


def format_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Muotoile axe-core tulokset raporttia varten
    
    Args:
        results: Raakadata axe-coresta
        
    Returns:
        Muotoillut tulokset
    """
    logger.debug("Formatting scan results", extra={
        "violation_count": len(results.get('violations', [])),
        "pass_count": len(results.get('passes', []))
    })
    
    formatted = {
        'url': results.get('url', ''),
        'timestamp': results.get('timestamp'),
        'violations': [],
        'passes': len(results.get('passes', [])),
        'violations_count': len(results.get('violations', [])),
        'inapplicable': len(results.get('inapplicable', [])),
        'incomplete': len(results.get('incomplete', []))
    }
    
    # Käsittele rikkomukset
    for violation in results.get('violations', []):
        formatted_violation = {
            'id': violation.get('id'),
            'impact': violation.get('impact'),
            'description': violation.get('description'),
            'help': violation.get('help'),
            'helpUrl': violation.get('helpUrl'),
            'nodes': len(violation.get('nodes', []))
        }
        formatted['violations'].append(formatted_violation)
    
    logger.debug("Results formatted successfully", extra={
        "formatted_violations": len(formatted['violations'])
    })
    
    return formatted


async def _capture_violation_screenshots(page, 
                                       axe_results: Dict[str, Any], 
                                       url: str, 
                                       scan_id: str,
                                       screenshot_config: Dict[str, Any]):
    """
    Capture screenshots of elements with accessibility violations
    
    Args:
        page: Playwright page object
        axe_results: Results from axe-core analysis
        url: Page URL
        scan_id: Unique scan identifier
        screenshot_config: Screenshot configuration
    """
    try:
        # Initialize screenshot capture
        screenshot_capture = create_screenshot_capture(**screenshot_config)
        
        violations = axe_results.get('violations', [])
        screenshot_count = 0
        
        logger.info("Starting screenshot capture", extra={
            "url": url,
            "scan_id": scan_id,
            "violations_count": len(violations)
        })
        
        # Capture page overview first
        if screenshot_config.get('capture_overview', True):
            overview_info = await screenshot_capture.capture_page_overview(page, violations)
            if overview_info:
                axe_results['page_overview_screenshot'] = overview_info
        
        # Process each violation
        for violation in violations:
            violation_screenshots = []
            
            # Process each node in the violation
            for node_index, node in enumerate(violation.get('nodes', [])):
                node_screenshots = []
                
                # Process each target selector
                for target in node.get('target', []):
                    try:
                        screenshot_info = await screenshot_capture.capture_violation_element(
                            page, 
                            target, 
                            violation, 
                            node_index
                        )
                        
                        if screenshot_info:
                            node_screenshots.append(screenshot_info)
                            screenshot_count += 1
                            
                            # Add base64 data directly to node for UI display
                            if 'base64_data' in screenshot_info and not node.get('screenshot'):
                                node['screenshot'] = screenshot_info['base64_data']
                            
                            # Limit screenshots per violation to prevent overflow
                            if len(node_screenshots) >= screenshot_config.get('max_screenshots_per_node', 3):
                                break
                                
                    except Exception as e:
                        logger.warning("Failed to capture screenshot for target", extra={
                            "target": target,
                            "violation_id": violation.get('id'),
                            "error": str(e)
                        })
                        continue
                
                # Add screenshots to node data
                if node_screenshots:
                    node['screenshots'] = node_screenshots
                    violation_screenshots.extend(node_screenshots)
                
                # Limit nodes per violation
                if node_index >= screenshot_config.get('max_nodes_per_violation', 5):
                    break
            
            # Add violation-level screenshot info
            if violation_screenshots:
                violation['screenshots'] = violation_screenshots
        
        # Add metadata about screenshots
        axe_results['screenshot_metadata'] = {
            'total_screenshots': screenshot_count,
            'capture_timestamp': time.time(),
            'scan_id': scan_id,
            'output_directory': str(screenshot_capture.output_dir),
            'image_format': screenshot_capture.image_format
        }
        
        logger.info("Screenshot capture completed", extra={
            "url": url,
            "scan_id": scan_id,
            "total_screenshots": screenshot_count
        })
        
    except Exception as e:
        logger.error("Failed to capture violation screenshots", extra={
            "url": url,
            "scan_id": scan_id,
            "error": str(e)
        }, exc_info=True)
        
        # Add error info to results
        axe_results['screenshot_error'] = {
            'error': str(e),
            'timestamp': time.time()
        }


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    results = asyncio.run(run_axe(url))
    formatted = format_results(results)
    print(json.dumps(formatted, indent=2))