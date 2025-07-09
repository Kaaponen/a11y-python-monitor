import asyncio
from playwright.async_api import async_playwright

AXE_JS_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js"

async def run_axe(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url)
        await page.add_script_tag(url=AXE_JS_URL)
        result = await page.evaluate("async () => await axe.run()")
        await browser.close()
        return result

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
