"""Health monitoring CLI and API endpoints"""

import asyncio
import json
from typing import Dict, Any
import click
from datetime import datetime
from ..utils.health_monitor import get_health_monitor, initialize_health_monitoring
from ..utils.logger import get_logger


logger = get_logger(__name__)


@click.group()
def health():
    """Health monitoring commands"""
    pass


@health.command()
@click.option(
    "--format",
    "output_format",
    default="json",
    type=click.Choice(["json", "table"]),
    help="Output format",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def status(output_format: str, verbose: bool):
    """Show current health status"""
    monitor = get_health_monitor()
    health_data = monitor.get_health_status()

    if output_format == "json":
        if verbose:
            click.echo(json.dumps(health_data, indent=2))
        else:
            # Simplified output
            simplified = {
                "status": health_data["status"],
                "uptime": health_data["uptime_human"],
                "success_rate": health_data["performance"]["success_rate_percent"],
                "total_scans": health_data["performance"]["total_scans"],
                "active_scans": health_data["recent_activity"]["active_scans"],
            }
            click.echo(json.dumps(simplified, indent=2))
    else:
        # Table format
        click.echo("\n🏥 Saavutettavuusskannerin Terveydentila")
        click.echo("=" * 50)

        status_emoji = {"healthy": "✅", "ok": "👍", "warning": "⚠️", "critical": "🚨"}

        click.echo(
            f"Status: {status_emoji.get(health_data['status'], '❓')} {health_data['status'].upper()}"
        )
        click.echo(f"Uptime: {health_data['uptime_human']}")
        click.echo(
            f"Monitoring: {'🟢 Active' if health_data['system_resources']['monitoring_active'] else '🔴 Inactive'}"
        )

        click.echo(f"\n📊 Suorituskyky:")
        perf = health_data["performance"]
        click.echo(f"  • Skannauksia yhteensä: {perf['total_scans']}")
        click.echo(f"  • Onnistuneita: {perf['successful_scans']}")
        click.echo(f"  • Epäonnistuneita: {perf['failed_scans']}")
        click.echo(f"  • Onnistumisprosentti: {perf['success_rate_percent']:.1f}%")
        click.echo(f"  • Keskimääräinen kesto: {perf['avg_scan_duration']:.2f}s")
        click.echo(f"  • Rikkomuksia löydetty: {perf['total_violations_found']}")

        if verbose:
            click.echo(f"\n💻 Järjestelmäresurssit (10min keskiarvo):")
            res = health_data["system_resources"]
            click.echo(f"  • CPU: {res['avg_cpu_percent_10min']}%")
            click.echo(f"  • Muisti: {res['avg_memory_percent_10min']}%")

            recent = health_data["recent_activity"]
            click.echo(f"\n⏱️ Viimeaikainen toiminta:")
            click.echo(f"  • Skannauksia viime tunnissa: {recent['scans_last_hour']}")
            click.echo(f"  • Aktiivisia skannauksia: {recent['active_scans']}")

            if health_data["error_breakdown"]:
                click.echo(f"\n🐛 Virhetyypit:")
                for error_type, count in health_data["error_breakdown"].items():
                    click.echo(f"  • {error_type}: {count}")


@health.command()
@click.option("--hours", default=24, help="Time period in hours")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["json", "table"]),
    help="Output format",
)
def metrics(hours: int, output_format: str):
    """Show performance metrics for specified time period"""
    monitor = get_health_monitor()
    metrics_data = monitor.get_metrics_summary(hours)

    if output_format == "json":
        click.echo(json.dumps(metrics_data, indent=2))
    else:
        if metrics_data.get("no_data"):
            click.echo(f"🔍 Ei dataa viimeiseltä {hours} tunnilta")
            return

        click.echo(f"\n📈 Suorituskykymittarit ({hours}h)")
        click.echo("=" * 40)

        click.echo(f"Skannaukset:")
        click.echo(f"  • Yhteensä: {metrics_data['total_scans']}")
        click.echo(f"  • Onnistuneita: {metrics_data['completed_scans']}")
        click.echo(f"  • Epäonnistuneita: {metrics_data['failed_scans']}")
        click.echo(
            f"  • Onnistumisprosentti: {metrics_data['success_rate_percent']:.1f}%"
        )

        click.echo(f"\nSuorituskyky:")
        click.echo(
            f"  • Keskimääräinen kesto: {metrics_data['avg_duration_seconds']:.2f}s"
        )
        click.echo(
            f"  • Rikkomuksia löydetty: {metrics_data['total_violations_found']}"
        )
        click.echo(
            f"  • Keskimäärin per skannaus: {metrics_data['avg_violations_per_scan']:.1f}"
        )

        if metrics_data["error_types"]:
            click.echo(f"\nVirhetyypit:")
            for error_type, count in metrics_data["error_types"].items():
                click.echo(f"  • {error_type}: {count}")


@health.command()
@click.option("--interval", default=30, help="Monitoring interval in seconds")
def start_monitoring(interval: int):
    """Start background health monitoring"""
    click.echo(f"🏥 Käynnistetään terveydenvalvonta (interval: {interval}s)")

    monitor = initialize_health_monitoring(start_background=True, interval=interval)

    click.echo("✅ Terveydenvalvonta käynnistetty")
    click.echo("Käytä 'health status' nähdäksesi tilanne")


@health.command()
def stop_monitoring():
    """Stop background health monitoring"""
    monitor = get_health_monitor()
    monitor.stop_monitoring()
    click.echo("⏹️ Terveydenvalvonta pysäytetty")


@health.command()
@click.option("--hours", default=168, help="Keep metrics for this many hours")
@click.confirmation_option(prompt="Poistetaanko vanhat mittarit?")
def cleanup(hours: int):
    """Clean up old metrics"""
    monitor = get_health_monitor()
    monitor.cleanup_old_metrics(hours)
    click.echo(f"🧹 Vanhat mittarit poistettu ({hours}h+ vanhat)")


def create_health_api_blueprint():
    """Create Flask blueprint for health monitoring API"""
    try:
        from flask import Blueprint, jsonify, request
    except ImportError:
        logger.warning("Flask not available, skipping API blueprint creation")
        return None

    bp = Blueprint("health", __name__, url_prefix="/health")

    @bp.route("/status")
    def api_health_status():
        """Health status API endpoint"""
        monitor = get_health_monitor()
        return jsonify(monitor.get_health_status())

    @bp.route("/metrics")
    def api_metrics():
        """Metrics API endpoint"""
        hours = request.args.get("hours", default=24, type=int)
        monitor = get_health_monitor()
        return jsonify(monitor.get_metrics_summary(hours))

    @bp.route("/monitoring/start", methods=["POST"])
    def api_start_monitoring():
        """Start monitoring API endpoint"""
        interval = request.json.get("interval", 30) if request.json else 30
        monitor = initialize_health_monitoring(start_background=True, interval=interval)
        return jsonify({"status": "started", "interval": interval})

    @bp.route("/monitoring/stop", methods=["POST"])
    def api_stop_monitoring():
        """Stop monitoring API endpoint"""
        monitor = get_health_monitor()
        monitor.stop_monitoring()
        return jsonify({"status": "stopped"})

    return bp


if __name__ == "__main__":
    health()
