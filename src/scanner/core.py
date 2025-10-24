import asyncio
import logging
from playwright.async_api import async_playwright
from typing import Dict, Any, Optional

# Importit tulevat juurihakemistosta kunnes ne on siirretty
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AXE_JS_URL, DEFAULT_TIMEOUT
from utils import validate_url, ScannerError

logger = logging.getLogger(__name__)

async def run_axe(url: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    Skannaa sivun saavutettavuuden käyttäen axe-corea
    
    Args:
        url: Skannattavan sivun URL
        timeout: Aikakatkaisu millisekunneissa
        
    Returns:
        Axe-core tulokset dict muodossa
        
    Raises:
        ScannerError: Jos skannaus epäonnistuu
        ValidationError: Jos URL ei ole kelvollinen
    """
    if not validate_url(url):
        raise ScannerError(f"Virheellinen URL: {url}")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Aseta timeout
            page.set_default_timeout(timeout)
            
            logger.info(f"Ladataan sivua: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            
            # Lisää axe-core skripti
            await page.add_script_tag(url=AXE_JS_URL)
            
            # Odota että axe on ladattu
            await page.wait_for_function("typeof axe !== 'undefined'")
            
            logger.info(f"Suoritetaan axe-skannaus: {url}")
            result = await page.evaluate("async () => await axe.run()")
            
            await browser.close()
            logger.info(f"Skannaus valmis: {url}")
            return result
            
    except Exception as e:
        logger.error(f"Skannaus epäonnistui URL:lle {url}: {str(e)}")
        raise ScannerError(f"Skannaus epäonnistui: {str(e)}") from e

def format_results(results, url):
    print(f"==> {url}")
    for violation in results.get("violations", []):
        print(f"❌ {violation['help']} ({violation['id']})")
        print(f"   📖 {violation['helpUrl']}")
        for node in violation['nodes']:
            print(f"   🔹 {node['html']}")
            for check in node['any']:
                print(f"     - {check['message']}")

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    results = asyncio.run(run_axe(url))
    format_results(results, url)