"""Dependency security scanning and vulnerability checking"""

import subprocess
import json
import requests
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from ..utils.logger import get_logger
from ..utils.exceptions import SecurityError

logger = get_logger(__name__)


@dataclass
class Vulnerability:
    """Vulnerability information"""

    id: str
    package: str
    version: str
    severity: str
    title: str
    description: str
    cve_id: Optional[str] = None
    fixed_versions: Optional[List[str]] = None
    published_date: Optional[str] = None
    reference_urls: Optional[List[str]] = None


@dataclass
class SecurityScanResult:
    """Security scan result"""

    timestamp: float
    total_packages: int
    vulnerable_packages: int
    vulnerabilities: List[Vulnerability]
    scan_duration: float
    scan_success: bool
    error_message: Optional[str] = None


class DependencySecurityScanner:
    """Comprehensive dependency security scanner"""

    def __init__(self):
        self.osv_api_url = "https://api.osv.dev/v1"
        self.safety_db_cache = {}
        logger.info("Dependency security scanner initialized")

    async def scan_dependencies(
        self, requirements_file: str = "requirements.txt"
    ) -> SecurityScanResult:
        """
        Scan dependencies for known vulnerabilities

        Args:
            requirements_file: Path to requirements file

        Returns:
            Security scan result
        """
        start_time = time.time()

        try:
            # Parse requirements file
            packages = self._parse_requirements_file(requirements_file)
            if not packages:
                return SecurityScanResult(
                    timestamp=start_time,
                    total_packages=0,
                    vulnerable_packages=0,
                    vulnerabilities=[],
                    scan_duration=time.time() - start_time,
                    scan_success=False,
                    error_message="No packages found in requirements file",
                )

            logger.info(
                "Starting dependency security scan",
                extra={
                    "total_packages": len(packages),
                    "requirements_file": requirements_file,
                },
            )

            # Scan with multiple sources
            vulnerabilities = []

            # Scan with Safety
            safety_vulns = await self._scan_with_safety(packages)
            vulnerabilities.extend(safety_vulns)

            # Scan with OSV database
            osv_vulns = await self._scan_with_osv(packages)
            vulnerabilities.extend(osv_vulns)

            # Remove duplicates
            unique_vulns = self._deduplicate_vulnerabilities(vulnerabilities)

            vulnerable_packages = len(set(vuln.package for vuln in unique_vulns))
            scan_duration = time.time() - start_time

            logger.info(
                "Dependency security scan completed",
                extra={
                    "total_packages": len(packages),
                    "vulnerable_packages": vulnerable_packages,
                    "total_vulnerabilities": len(unique_vulns),
                    "scan_duration": scan_duration,
                },
            )

            return SecurityScanResult(
                timestamp=start_time,
                total_packages=len(packages),
                vulnerable_packages=vulnerable_packages,
                vulnerabilities=unique_vulns,
                scan_duration=scan_duration,
                scan_success=True,
            )

        except Exception as e:
            logger.error(
                "Dependency security scan failed",
                extra={"requirements_file": requirements_file, "error": str(e)},
                exc_info=True,
            )

            return SecurityScanResult(
                timestamp=start_time,
                total_packages=0,
                vulnerable_packages=0,
                vulnerabilities=[],
                scan_duration=time.time() - start_time,
                scan_success=False,
                error_message=str(e),
            )

    def _parse_requirements_file(self, requirements_file: str) -> List[Tuple[str, str]]:
        """
        Parse requirements file to extract package names and versions

        Args:
            requirements_file: Path to requirements file

        Returns:
            List of (package_name, version) tuples
        """
        packages = []

        try:
            with open(requirements_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Skip URLs and git references
                if line.startswith(("http://", "https://", "git+")):
                    continue

                # Parse package specification
                package_spec = self._parse_package_spec(line)
                if package_spec:
                    packages.append(package_spec)

            logger.debug(
                "Parsed requirements file",
                extra={"file": requirements_file, "packages_found": len(packages)},
            )

            return packages

        except FileNotFoundError:
            logger.error(
                "Requirements file not found", extra={"file": requirements_file}
            )
            raise SecurityError(f"Requirements file not found: {requirements_file}")
        except Exception as e:
            logger.error(
                "Error parsing requirements file",
                extra={"file": requirements_file, "error": str(e)},
                exc_info=True,
            )
            raise SecurityError(f"Error parsing requirements file: {str(e)}")

    def _parse_package_spec(self, spec: str) -> Optional[Tuple[str, str]]:
        """Parse individual package specification"""
        import re

        # Remove extra options and comments
        spec = spec.split("#")[0].strip()
        if not spec:
            return None

        # Match package specifications like:
        # package==1.0.0
        # package>=1.0.0
        # package~=1.0.0
        # package
        match = re.match(r"^([a-zA-Z0-9_.-]+)([><=!~]+)?([0-9a-zA-Z.-]+)?", spec)
        if match:
            package_name = match.group(1).lower()
            version = match.group(3) if match.group(3) else "unknown"
            return (package_name, version)

        return None

    async def _scan_with_safety(
        self, packages: List[Tuple[str, str]]
    ) -> List[Vulnerability]:
        """Scan with Safety database"""
        vulnerabilities = []

        try:
            # Try to run safety CLI if available
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # No vulnerabilities found
                logger.debug("Safety scan completed - no vulnerabilities found")
                return []

            # Parse safety output
            try:
                safety_data = json.loads(result.stdout)
                for vuln_data in safety_data:
                    vulnerability = Vulnerability(
                        id=vuln_data.get("vulnerability_id", ""),
                        package=vuln_data.get("package_name", "").lower(),
                        version=vuln_data.get("analyzed_version", ""),
                        severity=self._map_safety_severity(
                            vuln_data.get("severity", "")
                        ),
                        title=vuln_data.get("advisory", ""),
                        description=vuln_data.get("advisory", ""),
                        fixed_versions=vuln_data.get("specs", []),
                    )
                    vulnerabilities.append(vulnerability)

                logger.info(
                    "Safety scan completed",
                    extra={"vulnerabilities_found": len(vulnerabilities)},
                )

            except json.JSONDecodeError:
                logger.warning(
                    "Failed to parse safety output",
                    extra={"stdout": result.stdout, "stderr": result.stderr},
                )

        except subprocess.TimeoutExpired:
            logger.warning("Safety scan timed out")
        except FileNotFoundError:
            logger.debug("Safety CLI not found, skipping safety scan")
        except Exception as e:
            logger.warning("Safety scan failed", extra={"error": str(e)})

        return vulnerabilities

    async def _scan_with_osv(
        self, packages: List[Tuple[str, str]]
    ) -> List[Vulnerability]:
        """Scan with OSV (Open Source Vulnerabilities) database"""
        vulnerabilities = []

        try:
            # Query OSV API for each package
            for package_name, version in packages:
                osv_vulns = await self._query_osv_api(package_name, version)
                vulnerabilities.extend(osv_vulns)

                # Rate limiting - be nice to the API
                time.sleep(0.1)

            logger.info(
                "OSV scan completed",
                extra={"vulnerabilities_found": len(vulnerabilities)},
            )

        except Exception as e:
            logger.warning("OSV scan failed", extra={"error": str(e)})

        return vulnerabilities

    async def _query_osv_api(
        self, package_name: str, version: str
    ) -> List[Vulnerability]:
        """Query OSV API for specific package"""
        vulnerabilities = []

        try:
            # OSV API query
            query_data = {"package": {"name": package_name, "ecosystem": "PyPI"}}

            if version != "unknown":
                query_data["version"] = version

            response = requests.post(
                f"{self.osv_api_url}/query", json=query_data, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                vulns = data.get("vulns", [])

                for vuln_data in vulns:
                    vulnerability = Vulnerability(
                        id=vuln_data.get("id", ""),
                        package=package_name,
                        version=version,
                        severity=self._extract_osv_severity(vuln_data),
                        title=vuln_data.get("summary", ""),
                        description=vuln_data.get("details", ""),
                        cve_id=self._extract_cve_id(vuln_data),
                        published_date=vuln_data.get("published", ""),
                        reference_urls=self._extract_reference_urls(vuln_data),
                    )
                    vulnerabilities.append(vulnerability)

        except requests.RequestException as e:
            logger.debug(
                "OSV API request failed for package",
                extra={"package": package_name, "error": str(e)},
            )
        except Exception as e:
            logger.warning(
                "OSV query failed for package",
                extra={"package": package_name, "error": str(e)},
            )

        return vulnerabilities

    def _map_safety_severity(self, severity: str) -> str:
        """Map safety severity to standard levels"""
        severity_map = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
        return severity_map.get(severity.lower(), "UNKNOWN")

    def _extract_osv_severity(self, vuln_data: Dict) -> str:
        """Extract severity from OSV vulnerability data"""
        # OSV uses CVSS scores in severity field
        severity_info = vuln_data.get("severity", [])
        if severity_info:
            for sev in severity_info:
                if sev.get("type") == "CVSS_V3":
                    score = sev.get("score")
                    if score:
                        return self._cvss_to_severity(score)

        # Default based on database type
        database_specific = vuln_data.get("database_specific", {})
        severity = database_specific.get("severity", "UNKNOWN")
        return severity.upper()

    def _cvss_to_severity(self, score: float) -> str:
        """Convert CVSS score to severity level"""
        if score >= 9.0:
            return "CRITICAL"
        elif score >= 7.0:
            return "HIGH"
        elif score >= 4.0:
            return "MEDIUM"
        else:
            return "LOW"

    def _extract_cve_id(self, vuln_data: Dict) -> Optional[str]:
        """Extract CVE ID from vulnerability data"""
        aliases = vuln_data.get("aliases", [])
        for alias in aliases:
            if alias.startswith("CVE-"):
                return alias
        return None

    def _extract_reference_urls(self, vuln_data: Dict) -> List[str]:
        """Extract reference URLs from vulnerability data"""
        references = vuln_data.get("references", [])
        urls = []
        for ref in references:
            if "url" in ref:
                urls.append(ref["url"])
        return urls

    def _deduplicate_vulnerabilities(
        self, vulnerabilities: List[Vulnerability]
    ) -> List[Vulnerability]:
        """Remove duplicate vulnerabilities"""
        seen = set()
        unique_vulns = []

        for vuln in vulnerabilities:
            # Create unique key based on package, version, and vulnerability ID
            key = (vuln.package, vuln.version, vuln.id)
            if key not in seen:
                seen.add(key)
                unique_vulns.append(vuln)

        return unique_vulns

    def generate_security_report(self, scan_result: SecurityScanResult) -> str:
        """Generate security report from scan results"""
        if not scan_result.scan_success:
            return f"Security scan failed: {scan_result.error_message}"

        report_lines = [
            "# Dependency Security Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(scan_result.timestamp))}",
            f"Scan Duration: {scan_result.scan_duration:.2f} seconds",
            "",
            "## Summary",
            f"- Total packages scanned: {scan_result.total_packages}",
            f"- Vulnerable packages: {scan_result.vulnerable_packages}",
            f"- Total vulnerabilities: {len(scan_result.vulnerabilities)}",
            "",
        ]

        if not scan_result.vulnerabilities:
            report_lines.append("🎉 **No vulnerabilities found!**")
            return "\n".join(report_lines)

        # Group by severity
        severity_groups = {}
        for vuln in scan_result.vulnerabilities:
            severity = vuln.severity
            if severity not in severity_groups:
                severity_groups[severity] = []
            severity_groups[severity].append(vuln)

        # Sort by severity priority
        severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]

        for severity in severity_order:
            if severity in severity_groups:
                vulns = severity_groups[severity]
                report_lines.extend(
                    [f"## {severity} Severity ({len(vulns)} vulnerabilities)", ""]
                )

                for vuln in vulns:
                    report_lines.extend(
                        [
                            f"### {vuln.package} ({vuln.version})",
                            f"**ID:** {vuln.id}",
                            f"**Title:** {vuln.title}",
                            f"**Description:** {vuln.description}",
                        ]
                    )

                    if vuln.cve_id:
                        report_lines.append(f"**CVE:** {vuln.cve_id}")

                    if vuln.fixed_versions:
                        report_lines.append(
                            f"**Fixed in:** {', '.join(vuln.fixed_versions)}"
                        )

                    if vuln.reference_urls:
                        report_lines.append("**References:**")
                        for url in vuln.reference_urls[:3]:  # Limit to 3 URLs
                            report_lines.append(f"- {url}")

                    report_lines.append("")

        return "\n".join(report_lines)


# Global scanner instance
_dependency_scanner: Optional[DependencySecurityScanner] = None


def get_dependency_scanner() -> DependencySecurityScanner:
    """Get global dependency scanner instance"""
    global _dependency_scanner
    if _dependency_scanner is None:
        _dependency_scanner = DependencySecurityScanner()
    return _dependency_scanner
