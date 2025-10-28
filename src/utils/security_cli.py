"""Security CLI commands"""

import asyncio
import json
import click
from typing import Dict, Any
from ..security import (
    get_security_validator,
    get_dependency_scanner,
    get_rate_limiter,
    get_security_headers,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


@click.group()
def security():
    """Security management commands"""
    pass


@security.command()
@click.argument("url")
@click.option("--allow-private", is_flag=True, help="Allow private IP addresses")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["json", "table"]),
    help="Output format",
)
def validate_url(url: str, allow_private: bool, output_format: str):
    """Validate URL for security issues"""
    validator = get_security_validator()

    try:
        result = validator.validate_url(url, allow_private)

        if output_format == "json":
            click.echo(json.dumps(result, indent=2))
        else:
            # Table format
            click.echo(f"\n🔍 URL Security Validation")
            click.echo("=" * 40)
            click.echo(f"URL: {url}")
            click.echo(f"Valid: {'✅ Yes' if result['valid'] else '❌ No'}")

            if result["parsed"]:
                parsed = result["parsed"]
                click.echo(f"Scheme: {parsed.scheme}")
                click.echo(f"Hostname: {parsed.hostname}")
                if parsed.port:
                    click.echo(f"Port: {parsed.port}")

            if result["security_issues"]:
                click.echo(f"\n🚨 Security Issues:")
                for issue in result["security_issues"]:
                    click.echo(f"  • {issue}")

            if result["warnings"]:
                click.echo(f"\n⚠️ Warnings:")
                for warning in result["warnings"]:
                    click.echo(f"  • {warning}")

            if result["valid"] and not result["security_issues"]:
                click.echo(f"\n✅ URL passed all security checks")

    except Exception as e:
        if output_format == "json":
            click.echo(json.dumps({"error": str(e)}, indent=2))
        else:
            click.echo(f"❌ Validation failed: {e}")


@security.command()
@click.option(
    "--requirements", default="requirements.txt", help="Requirements file to scan"
)
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["json", "table", "markdown"]),
    help="Output format",
)
@click.option("--save-report", help="Save report to file")
def scan_dependencies(requirements: str, output_format: str, save_report: str):
    """Scan dependencies for security vulnerabilities"""

    async def run_scan():
        scanner = get_dependency_scanner()

        click.echo(f"🔍 Scanning dependencies in {requirements}...")

        scan_result = await scanner.scan_dependencies(requirements)

        if not scan_result.scan_success:
            click.echo(f"❌ Scan failed: {scan_result.error_message}")
            return

        if output_format == "json":
            # Convert to JSON-serializable format
            result_dict = {
                "timestamp": scan_result.timestamp,
                "total_packages": scan_result.total_packages,
                "vulnerable_packages": scan_result.vulnerable_packages,
                "scan_duration": scan_result.scan_duration,
                "vulnerabilities": [
                    {
                        "id": v.id,
                        "package": v.package,
                        "version": v.version,
                        "severity": v.severity,
                        "title": v.title,
                        "description": v.description,
                        "cve_id": v.cve_id,
                        "fixed_versions": v.fixed_versions,
                    }
                    for v in scan_result.vulnerabilities
                ],
            }
            output = json.dumps(result_dict, indent=2)

        elif output_format == "markdown":
            output = scanner.generate_security_report(scan_result)

        else:  # table format
            output = format_scan_result_table(scan_result)

        if save_report:
            with open(save_report, "w", encoding="utf-8") as f:
                f.write(output)
            click.echo(f"📄 Report saved to: {save_report}")
        else:
            click.echo(output)

    asyncio.run(run_scan())


@security.command()
@click.argument("client_id")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["json", "table"]),
    help="Output format",
)
def rate_limit_status(client_id: str, output_format: str):
    """Check rate limit status for client"""
    rate_limiter = get_rate_limiter()
    status = rate_limiter.get_rate_limit_status(client_id)

    if output_format == "json":
        click.echo(json.dumps(status, indent=2))
    else:
        click.echo(f"\n📊 Rate Limit Status: {client_id}")
        click.echo("=" * 40)
        click.echo(
            f"Requests this minute: {status['requests_this_minute']}/{status['minute_limit']}"
        )
        click.echo(
            f"Requests this hour: {status['requests_this_hour']}/{status['hour_limit']}"
        )
        click.echo(f"Minute remaining: {status['minute_remaining']}")
        click.echo(f"Hour remaining: {status['hour_remaining']}")
        click.echo(
            f"Active scans: {status['active_scans']}/{status['max_concurrent_scans']}"
        )

        if status["is_blocked"]:
            click.echo(
                f"\n🚫 BLOCKED for {status['block_remaining_seconds']:.0f} more seconds"
            )
        else:
            click.echo(f"\n✅ Not blocked")

        click.echo(f"\nTotal requests: {status['total_requests']}")
        click.echo(f"Blocked requests: {status['blocked_requests']}")


@security.command()
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["json", "table"]),
    help="Output format",
)
def headers(output_format: str):
    """Show security headers configuration"""
    security_headers = get_security_headers()
    headers_dict = security_headers.get_security_headers(request_is_https=True)

    if output_format == "json":
        click.echo(json.dumps(headers_dict, indent=2))
    else:
        click.echo(f"\n🔒 Security Headers Configuration")
        click.echo("=" * 50)

        for header_name, header_value in headers_dict.items():
            click.echo(f"{header_name}:")
            click.echo(f"  {header_value}")
            click.echo()


@security.command()
@click.argument("filename")
def sanitize_filename(filename: str):
    """Sanitize filename for security"""
    validator = get_security_validator()

    try:
        sanitized = validator.sanitize_filename(filename)
        click.echo(f"Original:  {filename}")
        click.echo(f"Sanitized: {sanitized}")

        if filename != sanitized:
            click.echo(f"⚠️ Filename was modified for security")
        else:
            click.echo(f"✅ Filename is already safe")
    except Exception as e:
        click.echo(f"❌ Sanitization failed: {e}")


@security.command()
def security_audit():
    """Run comprehensive security audit"""
    click.echo("🔍 Running comprehensive security audit...")
    click.echo()

    # Check 1: Dependencies
    click.echo("1. Dependency Security Scan")
    click.echo("-" * 30)

    async def audit_dependencies():
        scanner = get_dependency_scanner()
        scan_result = await scanner.scan_dependencies()

        if scan_result.scan_success:
            if scan_result.vulnerabilities:
                click.echo(
                    f"❌ Found {len(scan_result.vulnerabilities)} vulnerabilities in {scan_result.vulnerable_packages} packages"
                )

                # Show critical/high severity count
                critical_high = [
                    v
                    for v in scan_result.vulnerabilities
                    if v.severity in ["CRITICAL", "HIGH"]
                ]
                if critical_high:
                    click.echo(
                        f"🚨 {len(critical_high)} critical/high severity vulnerabilities"
                    )
            else:
                click.echo("✅ No vulnerabilities found in dependencies")
        else:
            click.echo(f"❌ Dependency scan failed: {scan_result.error_message}")

    asyncio.run(audit_dependencies())

    # Check 2: Security Configuration
    click.echo(f"\n2. Security Configuration")
    click.echo("-" * 30)

    security_headers = get_security_headers()
    headers_dict = security_headers.get_security_headers()

    required_headers = [
        "Strict-Transport-Security",
        "X-Frame-Options",
        "X-Content-Type-Options",
        "Content-Security-Policy",
    ]

    missing_headers = [h for h in required_headers if h not in headers_dict]

    if missing_headers:
        click.echo(f"⚠️ Missing security headers: {', '.join(missing_headers)}")
    else:
        click.echo("✅ All critical security headers configured")

    # Check 3: Rate Limiting
    click.echo(f"\n3. Rate Limiting")
    click.echo("-" * 30)
    rate_limiter = get_rate_limiter()
    click.echo("✅ Rate limiting enabled")
    click.echo(f"  • Requests per minute: {rate_limiter.config.requests_per_minute}")
    click.echo(f"  • Requests per hour: {rate_limiter.config.requests_per_hour}")
    click.echo(f"  • Max concurrent scans: {rate_limiter.config.max_concurrent_scans}")

    click.echo(f"\n🔒 Security audit completed")


def format_scan_result_table(scan_result) -> str:
    """Format scan result as table"""
    lines = []
    lines.append(f"\n🔍 Dependency Security Scan Results")
    lines.append("=" * 50)
    lines.append(f"Scan duration: {scan_result.scan_duration:.2f} seconds")
    lines.append(f"Total packages: {scan_result.total_packages}")
    lines.append(f"Vulnerable packages: {scan_result.vulnerable_packages}")
    lines.append(f"Total vulnerabilities: {len(scan_result.vulnerabilities)}")

    if not scan_result.vulnerabilities:
        lines.append(f"\n🎉 No vulnerabilities found!")
        return "\n".join(lines)

    # Group by severity
    severity_counts = {}
    for vuln in scan_result.vulnerabilities:
        severity = vuln.severity
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    lines.append(f"\nVulnerabilities by severity:")
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]:
        if severity in severity_counts:
            count = severity_counts[severity]
            emoji = {
                "CRITICAL": "🚨",
                "HIGH": "❌",
                "MEDIUM": "⚠️",
                "LOW": "💛",
                "UNKNOWN": "❓",
            }
            lines.append(f"  {emoji.get(severity, '•')} {severity}: {count}")

    # Show top vulnerabilities
    lines.append(f"\nTop vulnerabilities:")
    for i, vuln in enumerate(scan_result.vulnerabilities[:5], 1):
        lines.append(f"{i}. {vuln.package} ({vuln.version}) - {vuln.severity}")
        lines.append(f"   {vuln.title}")
        if vuln.cve_id:
            lines.append(f"   CVE: {vuln.cve_id}")

    if len(scan_result.vulnerabilities) > 5:
        lines.append(f"   ... and {len(scan_result.vulnerabilities) - 5} more")

    return "\n".join(lines)


if __name__ == "__main__":
    security()
