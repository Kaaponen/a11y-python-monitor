#!/usr/bin/env python3
"""
Simple test scanner without Redis cache
"""
import asyncio
import json
from playwright.async_api import async_playwright

async def simple_scan(url: str):
    """Simple accessibility scan without cache"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate to page
            await page.goto(url, wait_until='networkidle')
            
            # Inject axe-core
            await page.add_script_tag(url="https://unpkg.com/axe-core@4.7.0/axe.min.js")
            
            # Run axe scan
            results = await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        axe.run((err, results) => {
                            if (err) resolve({error: err.message});
                            else resolve(results);
                        });
                    });
                }
            """)
            
            await browser.close()
            
            print(f"✅ Scan completed for {url}")
            print(f"Violations: {len(results.get('violations', []))}")
            print(f"Passes: {len(results.get('passes', []))}")
            
            return results
            
    except Exception as e:
        print(f"❌ Error scanning {url}: {e}")
        return None

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.example.com"
    results = asyncio.run(simple_scan(url))
    
    if results:
        with open("simple_scan_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("Results saved to simple_scan_results.json")