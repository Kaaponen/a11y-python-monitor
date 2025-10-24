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


# Logger for this module
logger = get_logger(__name__)
health_monitor = get_health_monitor()


@log_performance
async def run_axe(url: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Skannaa sivun saavutettavuuden käyttäen axe-corea
    
    Args:
        url: Skannattavan sivun URL
        timeout: Aikakatkaisu sekunteina
        
    Returns:
        Axe-core tulokset dict muodossa
        
    Raises:
        ScannerError: Jos skannaus epäonnistuu
        BrowserError: Jos selainongelmat
        NetworkError: Jos verkko-ongelmat
        TimeoutError: Jos aikakatkaisu
    """
    from ..utils.validators import is_valid_url
    
    scan_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Aloita health monitoring
    health_monitor.start_scan(scan_id, url)
    
    # Validoi URL
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
                
                # Merkitse skannaus onnistuneeksi
                health_monitor.complete_scan(scan_id, violation_count)
                
                logger.info("Scan completed successfully", extra={
                    "url": url,
                    "scan_id": scan_id,
                    "duration": duration,
                    "violation_count": violation_count,
                    "pass_count": len(axe_results.get('passes', []))
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


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    results = asyncio.run(run_axe(url))
    formatted = format_results(results)
    print(json.dumps(formatted, indent=2))