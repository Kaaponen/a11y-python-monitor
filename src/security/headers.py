"""Security headers and Content Security Policy implementation"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SecurityHeadersConfig:
    """Configuration for security headers"""
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year
    enable_csp: bool = True
    enable_xframe_options: bool = True
    enable_xss_protection: bool = True
    enable_content_type_options: bool = True
    enable_referrer_policy: bool = True
    enable_permissions_policy: bool = True


class SecurityHeaders:
    """Security headers management"""
    
    def __init__(self, config: Optional[SecurityHeadersConfig] = None):
        self.config = config or SecurityHeadersConfig()
        logger.info("Security headers initialized", extra={
            "hsts_enabled": self.config.enable_hsts,
            "csp_enabled": self.config.enable_csp
        })
    
    def get_security_headers(self, request_is_https: bool = True) -> Dict[str, str]:
        """
        Generate security headers for HTTP responses
        
        Args:
            request_is_https: Whether the request was made over HTTPS
            
        Returns:
            Dictionary of security headers
        """
        headers = {}
        
        # HTTP Strict Transport Security (HSTS)
        if self.config.enable_hsts and request_is_https:
            headers['Strict-Transport-Security'] = f'max-age={self.config.hsts_max_age}; includeSubDomains; preload'
        
        # X-Frame-Options (Clickjacking protection)
        if self.config.enable_xframe_options:
            headers['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection
        if self.config.enable_xss_protection:
            headers['X-XSS-Protection'] = '1; mode=block'
        
        # X-Content-Type-Options (MIME sniffing protection)
        if self.config.enable_content_type_options:
            headers['X-Content-Type-Options'] = 'nosniff'
        
        # Referrer Policy
        if self.config.enable_referrer_policy:
            headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        if self.config.enable_permissions_policy:
            headers['Permissions-Policy'] = self._build_permissions_policy()
        
        # Content Security Policy
        if self.config.enable_csp:
            headers['Content-Security-Policy'] = self._build_csp()
        
        # Additional security headers
        headers.update({
            'X-Permitted-Cross-Domain-Policies': 'none',
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Resource-Policy': 'same-origin'
        })
        
        logger.debug("Security headers generated", extra={
            "header_count": len(headers),
            "headers": list(headers.keys())
        })
        
        return headers
    
    def _build_csp(self) -> str:
        """Build Content Security Policy header"""
        # Restrictive CSP for accessibility scanner
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com",  # For axe-core
            "style-src 'self' 'unsafe-inline'",  # For inline styles in reports
            "img-src 'self' data: https:",  # Allow images from secure sources
            "font-src 'self' https:",
            "connect-src 'self' https:",  # For API calls
            "media-src 'none'",
            "object-src 'none'",
            "frame-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests"
        ]
        
        return '; '.join(csp_directives)
    
    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy header"""
        # Disable unnecessary browser features
        policies = [
            'camera=()',
            'microphone=()',
            'geolocation=()',
            'interest-cohort=()',
            'payment=()',
            'usb=()',
            'bluetooth=()',
            'magnetometer=()',
            'gyroscope=()',
            'accelerometer=()',
            'ambient-light-sensor=()',
            'autoplay=()',
            'encrypted-media=()',
            'fullscreen=()',
            'picture-in-picture=()'
        ]
        
        return ', '.join(policies)
    
    def validate_csp_compliance(self, html_content: str) -> List[str]:
        """
        Validate HTML content for CSP compliance
        
        Args:
            html_content: HTML content to validate
            
        Returns:
            List of CSP violations found
        """
        violations = []
        
        # Check for inline event handlers
        import re
        
        # Dangerous inline event patterns
        inline_events = re.findall(r'on\w+\s*=\s*["\'][^"\']*["\']', html_content, re.IGNORECASE)
        if inline_events:
            violations.append(f"Inline event handlers found: {len(inline_events)}")
        
        # Check for inline JavaScript
        inline_scripts = re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', html_content, re.DOTALL | re.IGNORECASE)
        if inline_scripts:
            violations.append(f"Inline scripts found: {len(inline_scripts)}")
        
        # Check for javascript: URLs
        js_urls = re.findall(r'javascript:', html_content, re.IGNORECASE)
        if js_urls:
            violations.append(f"JavaScript URLs found: {len(js_urls)}")
        
        # Check for data: URLs in scripts
        data_urls = re.findall(r'src\s*=\s*["\']data:', html_content, re.IGNORECASE)
        if data_urls:
            violations.append(f"Data URLs in src attributes: {len(data_urls)}")
        
        if violations:
            logger.warning("CSP violations found in content", extra={
                "violations": violations,
                "content_length": len(html_content)
            })
        
        return violations


class SecureReportGenerator:
    """Secure report generation with CSP compliance"""
    
    def __init__(self):
        self.security_headers = SecurityHeaders()
    
    def generate_secure_html_report(self, report_data: Dict, title: str = "Accessibility Report") -> str:
        """
        Generate CSP-compliant HTML report
        
        Args:
            report_data: Report data dictionary
            title: Report title
            
        Returns:
            Secure HTML content
        """
        # Sanitize title
        title = self._sanitize_text(title)
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {self._get_secure_css()}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <div class="metadata">
            Generated on: {report_data.get('timestamp', 'Unknown')}
        </div>
    </header>
    
    <main>
        {self._generate_report_content(report_data)}
    </main>
    
    <footer>
        <p>Generated by Saavutettavuusskanneri - Accessibility Scanner</p>
    </footer>
</body>
</html>"""
        
        # Validate CSP compliance
        violations = self.security_headers.validate_csp_compliance(html_template)
        if violations:
            logger.warning("Generated HTML has CSP violations", extra={
                "violations": violations
            })
        
        return html_template
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text content for HTML output"""
        if not text:
            return ""
        
        # HTML entity encoding
        import html
        return html.escape(text)
    
    def _get_secure_css(self) -> str:
        """Get secure CSS styles (no external dependencies)"""
        return """
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            color: #333;
        }
        
        header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        h1 {
            margin: 0 0 10px 0;
            color: #2c3e50;
        }
        
        .metadata {
            color: #666;
            font-size: 0.9em;
        }
        
        main {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .violation {
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin: 10px 0;
            background: #fdf2f2;
        }
        
        .violation h3 {
            margin: 0 0 10px 0;
            color: #c0392b;
        }
        
        .pass {
            color: #27ae60;
        }
        
        .fail {
            color: #e74c3c;
        }
        
        footer {
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 0.9em;
        }
        
        code {
            background: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
        }
        """
    
    def _generate_report_content(self, report_data: Dict) -> str:
        """Generate secure report content"""
        content_parts = []
        
        # Summary section
        if 'summary' in report_data:
            summary = report_data['summary']
            content_parts.append(f"""
            <section class="summary">
                <h2>Summary</h2>
                <p>Total URLs scanned: <strong>{self._sanitize_text(str(summary.get('total_urls', 0)))}</strong></p>
                <p>Total violations: <strong class="fail">{self._sanitize_text(str(summary.get('total_violations', 0)))}</strong></p>
                <p>Total passes: <strong class="pass">{self._sanitize_text(str(summary.get('total_passes', 0)))}</strong></p>
            </section>
            """)
        
        # Results section
        if 'results' in report_data:
            content_parts.append("<section class='results'><h2>Detailed Results</h2>")
            
            for url, result in report_data['results'].items():
                url_safe = self._sanitize_text(url)
                content_parts.append(f"<h3>URL: {url_safe}</h3>")
                
                # Violations
                violations = result.get('violations', [])
                if violations:
                    for violation in violations:
                        violation_html = self._generate_violation_html(violation)
                        content_parts.append(violation_html)
                else:
                    content_parts.append("<p class='pass'>No accessibility violations found!</p>")
            
            content_parts.append("</section>")
        
        return '\n'.join(content_parts)
    
    def _generate_violation_html(self, violation: Dict) -> str:
        """Generate secure HTML for a violation"""
        violation_id = self._sanitize_text(violation.get('id', ''))
        help_text = self._sanitize_text(violation.get('help', ''))
        description = self._sanitize_text(violation.get('description', ''))
        impact = self._sanitize_text(violation.get('impact', 'unknown'))
        
        return f"""
        <div class="violation">
            <h3>{help_text} ({violation_id})</h3>
            <p><strong>Impact:</strong> {impact}</p>
            <p>{description}</p>
            <p><strong>Nodes affected:</strong> {len(violation.get('nodes', []))}</p>
        </div>
        """


# Global instances
_security_headers: Optional[SecurityHeaders] = None
_secure_report_generator: Optional[SecureReportGenerator] = None


def get_security_headers() -> SecurityHeaders:
    """Get global security headers instance"""
    global _security_headers
    if _security_headers is None:
        _security_headers = SecurityHeaders()
    return _security_headers


def get_secure_report_generator() -> SecureReportGenerator:
    """Get global secure report generator instance"""
    global _secure_report_generator
    if _secure_report_generator is None:
        _secure_report_generator = SecureReportGenerator()
    return _secure_report_generator