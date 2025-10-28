"""Security-focused input validation and sanitization"""

import re
import urllib.parse
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
import ipaddress
from ..utils.logger import get_logger
from ..utils.exceptions import SecurityError

logger = get_logger(__name__)

# Security constants
MAX_URL_LENGTH = 2000
MAX_FILENAME_LENGTH = 255
ALLOWED_PROTOCOLS = {"http", "https"}
BLOCKED_DOMAINS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",  # GCP metadata
    "169.254.169.254",  # AWS/Azure metadata
    "100.100.100.200",  # Alibaba metadata
}
PRIVATE_IP_RANGES = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",  # Link-local
    "fc00::/7",  # IPv6 private
    "fe80::/10",  # IPv6 link-local
]

# Dangerous file extensions and patterns
DANGEROUS_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".com",
    ".pif",
    ".scr",
    ".vbs",
    ".js",
    ".jar",
    ".app",
    ".deb",
    ".pkg",
    ".dmg",
    ".sh",
    ".ps1",
    ".psm1",
}

SUSPICIOUS_PATTERNS = [
    r"\.\./",  # Directory traversal
    r"\\\.\\\.\\",  # Windows directory traversal
    r"%2e%2e%2f",  # URL encoded directory traversal
    r"%252e%252e%252f",  # Double URL encoded
    r"<script",  # XSS attempts
    r"javascript:",  # JavaScript protocol
    r"data:",  # Data URLs
    r"vbscript:",  # VBScript protocol
    r"file://",  # File protocol
    r"ftp://",  # FTP protocol
]


class SecurityValidator:
    """Comprehensive security validator for user inputs"""

    def __init__(self):
        self.suspicious_pattern = re.compile(
            "|".join(SUSPICIOUS_PATTERNS), re.IGNORECASE
        )

    def validate_url(self, url: str, allow_private: bool = False) -> Dict[str, Any]:
        """
        Comprehensive URL validation with security checks

        Args:
            url: URL to validate
            allow_private: Whether to allow private/local IPs

        Returns:
            Validation result with details

        Raises:
            SecurityError: If URL fails security validation
        """
        result = {
            "valid": False,
            "url": url,
            "parsed": None,
            "security_issues": [],
            "warnings": [],
        }

        try:
            # Basic length check
            if len(url) > MAX_URL_LENGTH:
                result["security_issues"].append(
                    f"URL too long: {len(url)} > {MAX_URL_LENGTH}"
                )
                logger.warning(
                    "URL length validation failed",
                    extra={"url_length": len(url), "max_allowed": MAX_URL_LENGTH},
                )
                raise SecurityError(f"URL too long: {len(url)} characters")

            # Suspicious pattern check
            if self.suspicious_pattern.search(url):
                result["security_issues"].append("Suspicious patterns detected in URL")
                logger.warning(
                    "Suspicious patterns in URL",
                    extra={
                        "url": url,
                        "patterns_found": self.suspicious_pattern.findall(url),
                    },
                )
                raise SecurityError("Suspicious patterns detected in URL")

            # Parse URL
            parsed = urlparse(url)
            result["parsed"] = parsed

            # Protocol validation
            if parsed.scheme.lower() not in ALLOWED_PROTOCOLS:
                result["security_issues"].append(f"Invalid protocol: {parsed.scheme}")
                logger.warning(
                    "Invalid protocol detected",
                    extra={
                        "protocol": parsed.scheme,
                        "allowed_protocols": list(ALLOWED_PROTOCOLS),
                    },
                )
                raise SecurityError(f"Protocol '{parsed.scheme}' not allowed")

            # Hostname validation
            if not parsed.hostname:
                result["security_issues"].append("No hostname in URL")
                raise SecurityError("URL missing hostname")

            hostname = parsed.hostname.lower()

            # Check blocked domains
            if hostname in BLOCKED_DOMAINS:
                result["security_issues"].append(f"Blocked domain: {hostname}")
                logger.warning(
                    "Blocked domain access attempt",
                    extra={
                        "hostname": hostname,
                        "blocked_domains": list(BLOCKED_DOMAINS),
                    },
                )
                raise SecurityError(f"Domain '{hostname}' is blocked")

            # IP address validation
            try:
                ip = ipaddress.ip_address(hostname)
                if not allow_private and self._is_private_ip(ip):
                    result["security_issues"].append(
                        f"Private IP address not allowed: {hostname}"
                    )
                    logger.warning(
                        "Private IP access attempt",
                        extra={"ip": str(ip), "allow_private": allow_private},
                    )
                    raise SecurityError(f"Private IP address not allowed: {hostname}")
            except ValueError:
                # Not an IP address, which is fine
                pass

            # Port validation
            if parsed.port:
                if parsed.port < 1 or parsed.port > 65535:
                    result["security_issues"].append(f"Invalid port: {parsed.port}")
                    raise SecurityError(f"Invalid port: {parsed.port}")

                # Check for dangerous ports
                dangerous_ports = {22, 23, 25, 53, 110, 143, 993, 995}
                if parsed.port in dangerous_ports:
                    result["warnings"].append(
                        f"Potentially dangerous port: {parsed.port}"
                    )
                    logger.info(
                        "Potentially dangerous port",
                        extra={"port": parsed.port, "url": url},
                    )

            result["valid"] = True
            logger.debug(
                "URL validation successful",
                extra={"url": url, "hostname": hostname, "scheme": parsed.scheme},
            )

            return result

        except SecurityError:
            raise
        except Exception as e:
            result["security_issues"].append(f"URL parsing error: {str(e)}")
            logger.error(
                "URL validation error",
                extra={"url": url, "error": str(e)},
                exc_info=True,
            )
            raise SecurityError(f"Invalid URL format: {str(e)}")

    def _is_private_ip(self, ip: ipaddress.ip_address) -> bool:
        """Check if IP address is in private ranges"""
        for range_str in PRIVATE_IP_RANGES:
            try:
                network = ipaddress.ip_network(range_str, strict=False)
                if ip in network:
                    return True
            except ValueError:
                continue
        return False

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for security

        Args:
            filename: Original filename

        Returns:
            Sanitized filename

        Raises:
            SecurityError: If filename is unsafe
        """
        if not filename:
            raise SecurityError("Empty filename")

        if len(filename) > MAX_FILENAME_LENGTH:
            raise SecurityError(
                f"Filename too long: {len(filename)} > {MAX_FILENAME_LENGTH}"
            )

        # Check for dangerous extensions
        lower_filename = filename.lower()
        for ext in DANGEROUS_EXTENSIONS:
            if lower_filename.endswith(ext):
                logger.warning(
                    "Dangerous file extension detected",
                    extra={"original_filename": filename, "extension": ext},
                )
                raise SecurityError(f"Dangerous file extension: {ext}")

        # Check for suspicious patterns
        if self.suspicious_pattern.search(filename):
            logger.warning(
                "Suspicious patterns in filename",
                extra={
                    "original_filename": filename,
                    "patterns_found": self.suspicious_pattern.findall(filename),
                },
            )
            raise SecurityError("Suspicious patterns in filename")

        # Remove dangerous characters
        dangerous_chars = '<>:"/\\|?*\x00'
        sanitized = "".join(c for c in filename if c not in dangerous_chars)

        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(" .")

        # Ensure it's not empty after sanitization
        if not sanitized:
            raise SecurityError("Filename becomes empty after sanitization")

        # Check for reserved names (Windows)
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }

        name_without_ext = sanitized.split(".")[0].upper()
        if name_without_ext in reserved_names:
            sanitized = f"file_{sanitized}"
            logger.info(
                "Reserved filename sanitized",
                extra={"original_name": filename, "sanitized_name": sanitized},
            )

        logger.debug(
            "Filename sanitized",
            extra={"original_name": filename, "sanitized_name": sanitized},
        )

        return sanitized

    def validate_report_format(self, format_name: str) -> bool:
        """
        Validate report format parameter

        Args:
            format_name: Format to validate

        Returns:
            True if valid

        Raises:
            SecurityError: If format is invalid
        """
        allowed_formats = {"html", "json", "csv", "markdown", "md"}

        if not format_name or not isinstance(format_name, str):
            raise SecurityError("Invalid format type")

        if format_name.lower() not in allowed_formats:
            logger.warning(
                "Invalid report format requested",
                extra={"format": format_name, "allowed_formats": list(allowed_formats)},
            )
            raise SecurityError(f"Invalid report format: {format_name}")

        return True

    def validate_sitemap_urls(self, urls: List[str], max_urls: int = 1000) -> List[str]:
        """
        Validate list of URLs from sitemap with security checks

        Args:
            urls: List of URLs to validate
            max_urls: Maximum number of URLs allowed

        Returns:
            List of validated URLs

        Raises:
            SecurityError: If validation fails
        """
        if len(urls) > max_urls:
            logger.warning(
                "Too many URLs in sitemap",
                extra={"url_count": len(urls), "max_allowed": max_urls},
            )
            raise SecurityError(f"Too many URLs: {len(urls)} > {max_urls}")

        validated_urls = []

        for url in urls:
            try:
                result = self.validate_url(url)
                if result["valid"]:
                    validated_urls.append(url)
            except SecurityError as e:
                logger.warning(
                    "URL failed validation in sitemap",
                    extra={"url": url, "error": str(e)},
                )
                # Skip invalid URLs but don't fail the entire operation
                continue

        if not validated_urls:
            raise SecurityError("No valid URLs found in sitemap")

        logger.info(
            "Sitemap URLs validated",
            extra={
                "total_urls": len(urls),
                "valid_urls": len(validated_urls),
                "rejected_urls": len(urls) - len(validated_urls),
            },
        )

        return validated_urls


# Global validator instance
_security_validator: Optional[SecurityValidator] = None


def get_security_validator() -> SecurityValidator:
    """Get global security validator instance"""
    global _security_validator
    if _security_validator is None:
        _security_validator = SecurityValidator()
    return _security_validator


def validate_url_secure(url: str, allow_private: bool = False) -> Dict[str, Any]:
    """Convenience function for secure URL validation"""
    validator = get_security_validator()
    return validator.validate_url(url, allow_private)


def sanitize_filename_secure(filename: str) -> str:
    """Convenience function for secure filename sanitization"""
    validator = get_security_validator()
    return validator.sanitize_filename(filename)
