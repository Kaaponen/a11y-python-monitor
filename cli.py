import asyncio
import sys
from src.scanner.sitemap import get_urls_from_sitemap
from src.scanner.core import run_axe
from src.reports.reporter import save_report
from src.reports.csv_export import save_csv

async def main():
    args = sys.argv[1:]
    if "--sitemap" in args:
        idx = args.index("--sitemap")
        sitemap_url = args[idx + 1]
        prefix = None
        if "--filter" in args:
            pidx = args.index("--filter")
            prefix = args[pidx + 1]
        urls = get_urls_from_sitemap(sitemap_url, prefix)
    else:
        urls = [args[0]] if args else ["https://example.com"]

    tasks = [run_axe(url) for url in urls]
    results = await asyncio.gather(*tasks)
    results_by_url = dict(zip(urls, results))

    for url, result in results_by_url.items():
        print(f"==> {url}")
        for v in result.get("violations", []):
            print(f"❌ {v['help']} ({v['id']}) - {v['helpUrl']}")

    md_path, html_path = save_report(results_by_url)
    print(f"Markdown report saved to: {md_path}")
    print(f"HTML report saved to: {html_path}")
    csv_path = save_csv(results_by_url)
    print(f"CSV report saved to: {csv_path}")

if __name__ == "__main__":
    asyncio.run(main())
