#!/usr/bin/env python3
"""Command line interface for accessibility scanner"""

import asyncio
import click
from src.scanner.sitemap import get_urls_from_sitemap
from src.scanner.core import run_axe
from src.reports.reporter import save_report
from src.reports.csv_export import save_csv
from src.utils.health_cli import health
from src.utils.security_cli import security
from src.utils.performance_cli import performance
from src.utils.health_monitor import initialize_health_monitoring
from src.utils.logger import get_logger

logger = get_logger(__name__)


@click.group()
def cli():
    """Saavutettavuusskanneri - Accessibility Scanner"""
    # Initialize health monitoring when CLI starts
    initialize_health_monitoring(start_background=False)


@cli.command()
@click.argument("url", required=False)
@click.option("--sitemap", help="Sitemap URL to scan")
@click.option("--filter", help="URL prefix filter for sitemap")
@click.option("--timeout", default=30, help="Timeout for each scan in seconds")
@click.option("--output-dir", default="reports", help="Output directory for reports")
@click.option(
    "--format",
    "formats",
    multiple=True,
    default=["html", "json"],
    help="Output formats (html, json, csv)",
)
@click.option(
    "--screenshots", is_flag=True, help="Capture screenshots of violation elements"
)
@click.option(
    "--screenshot-dir", default="reports/screenshots", help="Directory for screenshots"
)
@click.option("--max-screenshots", default=10, help="Maximum screenshots per violation")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def scan(
    url,
    sitemap,
    filter,
    timeout,
    output_dir,
    formats,
    screenshots,
    screenshot_dir,
    max_screenshots,
    verbose,
):
    """Scan website(s) for accessibility issues"""

    # Determine URLs to scan
    if sitemap:
        click.echo(f"📄 Ladataan URL:eja sitemapista: {sitemap}")
        urls = get_urls_from_sitemap(sitemap, filter)
        if not urls:
            click.echo("❌ Ei URL:eja löytynyt sitemapista")
            return
        click.echo(f"✅ Löytyi {len(urls)} URL:ia")
    elif url:
        urls = [url]
    else:
        click.echo("❌ Anna URL tai käytä --sitemap")
        return

    if verbose:
        click.echo(f"🎯 Skannataan {len(urls)} sivua:")
        for u in urls[:5]:  # Show first 5
            click.echo(f"  • {u}")
        if len(urls) > 5:
            click.echo(f"  ... ja {len(urls) - 5} muuta")

    # Run scans
    async def run_scans():
        click.echo("🔍 Aloitetaan skannaukset...")

        # Configure screenshots if enabled
        screenshot_config = {}
        if screenshots:
            click.echo(f"📸 Kuvakaappaukset käytössä: {screenshot_dir}")
            screenshot_config = {
                "output_dir": screenshot_dir,
                "max_screenshots": min(max_screenshots, 5),
                "max_screenshots_per_node": 3,
                "capture_overview": True,
                "highlight_violations": True,
                "element_padding": 20,
                "image_format": "png",
            }

        with click.progressbar(urls, label="Skannataan") as progress_urls:
            tasks = []
            for scan_url in progress_urls:
                task = run_axe(
                    scan_url,
                    timeout=timeout,
                    capture_screenshots=screenshots,
                    screenshot_config=screenshot_config if screenshots else None,
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        results_by_url = {}
        successful_scans = 0

        for scan_url, result in zip(urls, results):
            if isinstance(result, Exception):
                click.echo(f"❌ Virhe skannattaessa {scan_url}: {result}")
                continue

            results_by_url[scan_url] = result
            successful_scans += 1

            if verbose:
                violation_count = len(result.get("violations", []))
                click.echo(f"✅ {scan_url}: {violation_count} rikkomusta")

        if not results_by_url:
            click.echo("❌ Kaikki skannaukset epäonnistuivat")
            return

        click.echo(f"✅ {successful_scans}/{len(urls)} skannausta onnistui")

        # Save reports
        if "html" in formats or "json" in formats:
            md_path, html_path = save_report(results_by_url, output_dir)
            if "html" in formats:
                click.echo(f"📄 HTML-raportti: {html_path}")
            if "json" in formats:
                click.echo(f"📄 JSON-raportti: {md_path}")

        if "csv" in formats:
            csv_path = save_csv(results_by_url, output_dir)
            click.echo(f"📄 CSV-raportti: {csv_path}")

        # Summary
        total_violations = sum(
            len(r.get("violations", [])) for r in results_by_url.values()
        )
        click.echo(f"\n📊 Yhteenveto:")
        click.echo(f"  • Rikkomuksia yhteensä: {total_violations}")
        click.echo(
            f"  • Keskimäärin per sivu: {total_violations/len(results_by_url):.1f}"
        )

    # Run async function
    asyncio.run(run_scans())


# Add health, security and performance commands
cli.add_command(health)
cli.add_command(security)
cli.add_command(performance)


@cli.command()
def version():
    """Show version information"""
    click.echo("Saavutettavuusskanneri v1.0.0")
    click.echo("Accessibility Scanner for Finnish websites")
    click.echo("Performance optimizations: Cache, Rate limiting, Connection pooling")


if __name__ == "__main__":
    cli()
