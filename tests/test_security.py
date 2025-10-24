"""Testit turvallisuusmoduulille"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.security.input_validation import SecurityValidator, validate_url_secure, sanitize_filename_secure
from src.security.rate_limiting import RateLimiter, RequestSecurityMiddleware
from src.security.headers import SecurityHeaders, SecureReportGenerator
from src.security.dependency_scanner import DependencySecurityScanner
from src.utils.exceptions import SecurityError


class TestSecurityValidator:
    """Testit SecurityValidator-luokalle"""
    
    def setup_method(self):
        """Alustetaan testit"""
        self.validator = SecurityValidator()
    
    def test_validate_url_valid_https(self):
        """Testi: HTTPS URL:n validointi"""
        result = self.validator.validate_url("https://example.com")
        assert result['valid'] is True
        assert result['scheme'] == 'https'
        assert result['hostname'] == 'example.com'
    
    def test_validate_url_valid_http(self):
        """Testi: HTTP URL:n validointi"""
        result = self.validator.validate_url("http://example.com")
        assert result['valid'] is True
        assert result['scheme'] == 'http'
        assert result['hostname'] == 'example.com'
    
    def test_validate_url_invalid_protocol(self):
        """Testi: Virheellinen protokolla"""
        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_url("ftp://example.com")
        assert "Protocol 'ftp' not allowed" in str(exc_info.value)
    
    def test_validate_url_blocked_domain(self):
        """Testi: Estetty domain"""
        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_url("https://localhost")
        assert "Domain 'localhost' is blocked" in str(exc_info.value)
    
    def test_validate_url_private_ip(self):
        """Testi: Yksityinen IP-osoite"""
        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_url("https://192.168.1.1")
        assert "Private IP address not allowed" in str(exc_info.value)
    
    def test_validate_url_allow_private_ip(self):
        """Testi: Yksityinen IP sallittu"""
        result = self.validator.validate_url("https://192.168.1.1", allow_private=True)
        assert result['valid'] is True
    
    def test_sanitize_filename_valid(self):
        """Testi: Turvallinen tiedostonimi"""
        result = self.validator.sanitize_filename("valid_file.txt")
        assert result == "valid_file.txt"
    
    def test_sanitize_filename_dangerous_extension(self):
        """Testi: Vaarallinen tiedostopääte"""
        with pytest.raises(SecurityError) as exc_info:
            self.validator.sanitize_filename("malware.exe")
        assert "Dangerous file extension: .exe" in str(exc_info.value)
    
    def test_sanitize_filename_path_traversal(self):
        """Testi: Path traversal -hyökkäys"""
        with pytest.raises(SecurityError) as exc_info:
            self.validator.sanitize_filename("../../etc/passwd")
        assert "Suspicious patterns in filename" in str(exc_info.value)
    
    def test_sanitize_filename_dangerous_chars(self):
        """Testi: Vaaralliset merkit"""
        result = self.validator.sanitize_filename("file<>name.txt")
        assert result == "filename.txt"
    
    def test_sanitize_filename_reserved_name(self):
        """Testi: Varattu nimi (Windows)"""
        result = self.validator.sanitize_filename("CON.txt")
        assert result == "file_CON.txt"
    
    def test_sanitize_filename_empty(self):
        """Testi: Tyhjä tiedostonimi"""
        with pytest.raises(SecurityError) as exc_info:
            self.validator.sanitize_filename("")
        assert "Empty filename" in str(exc_info.value)
    
    def test_sanitize_filename_too_long(self):
        """Testi: Liian pitkä tiedostonimi"""
        long_name = "a" * 300
        with pytest.raises(SecurityError) as exc_info:
            self.validator.sanitize_filename(long_name)
        assert "Filename too long" in str(exc_info.value)
    
    def test_validate_report_format_valid(self):
        """Testi: Kelvollinen raporttiformaatti"""
        assert self.validator.validate_report_format("html") is True
        assert self.validator.validate_report_format("json") is True
        assert self.validator.validate_report_format("csv") is True
    
    def test_validate_report_format_invalid(self):
        """Testi: Virheellinen raporttiformaatti"""
        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_report_format("exe")
        assert "Invalid report format" in str(exc_info.value)


class TestRateLimiter:
    """Testit RateLimiter-luokalle"""
    
    def setup_method(self):
        """Alustetaan testit"""
        self.rate_limiter = RateLimiter()
    
    def test_check_rate_limit_new_client(self):
        """Testi: Uusi asiakas"""
        result = self.rate_limiter.check_rate_limit("127.0.0.1")
        assert result['allowed'] is True
        assert result['remaining_requests'] == 59  # 60 - 1
    
    def test_check_rate_limit_within_limits(self):
        """Testi: Rajojen sisällä"""
        client_ip = "127.0.0.1"
        
        # Tee 5 pyyntöä
        for i in range(5):
            result = self.rate_limiter.check_rate_limit(client_ip)
            assert result['allowed'] is True
        
        # Tarkista että määrä on oikea
        assert result['remaining_requests'] == 55  # 60 - 5
    
    def test_check_rate_limit_exceeded(self):
        """Testi: Rajat ylitetty"""
        client_ip = "127.0.0.2"
        
        # Ylitä minuuttiraja
        for i in range(61):
            result = self.rate_limiter.check_rate_limit(client_ip)
        
        # Viimeinen pyyntö pitäisi hylätä
        assert result['allowed'] is False
        assert 'rate limit exceeded' in result['message'].lower()
    
    def test_concurrent_scan_limit(self):
        """Testi: Samanaikaisten skannausten raja"""
        # Aloita maksimimäärä skannauksia
        for i in range(5):
            self.rate_limiter.start_scan(f"scan_{i}")
        
        # Kuudes skannaus pitäisi hylätä
        with pytest.raises(SecurityError) as exc_info:
            self.rate_limiter.start_scan("scan_6")
        assert "Too many concurrent scans" in str(exc_info.value)
        
        # Lopeta yksi skannaus ja yritä uudelleen
        self.rate_limiter.end_scan("scan_0")
        self.rate_limiter.start_scan("scan_6")  # Tämän pitäisi onnistua
    
    def test_burst_attack_detection(self):
        """Testi: Burst-hyökkäyksen tunnistus"""
        client_ip = "127.0.0.3"
        
        # Simuloi burst-hyökkäys (20 pyyntöä 10 sekunnissa)
        import time
        start_time = time.time()
        
        for i in range(20):
            result = self.rate_limiter.check_rate_limit(client_ip)
            if not result['allowed']:
                break
        
        # Pitäisi tunnistaa burst-hyökkäys
        assert not result['allowed']
        assert 'burst attack detected' in result['message'].lower()


class TestSecurityHeaders:
    """Testit SecurityHeaders-luokalle"""
    
    def setup_method(self):
        """Alustetaan testit"""
        self.security_headers = SecurityHeaders()
    
    def test_get_headers_default(self):
        """Testi: Oletusturvallisuusotsikot"""
        headers = self.security_headers.get_headers()
        
        assert 'Strict-Transport-Security' in headers
        assert 'X-Frame-Options' in headers
        assert 'X-XSS-Protection' in headers
        assert 'X-Content-Type-Options' in headers
        assert 'Content-Security-Policy' in headers
        assert 'Referrer-Policy' in headers
    
    def test_get_headers_custom_csp(self):
        """Testi: Mukautettu CSP"""
        custom_csp = "default-src 'self'"
        headers = self.security_headers.get_headers(custom_csp=custom_csp)
        
        assert headers['Content-Security-Policy'] == custom_csp
    
    def test_validate_csp_policy_valid(self):
        """Testi: Kelvollinen CSP-käytäntö"""
        valid_csp = "default-src 'self'; script-src 'self' 'unsafe-inline'"
        assert self.security_headers.validate_csp_policy(valid_csp) is True
    
    def test_validate_csp_policy_invalid(self):
        """Testi: Virheellinen CSP-käytäntö"""
        invalid_csp = "invalid-directive 'self'"
        assert self.security_headers.validate_csp_policy(invalid_csp) is False


class TestSecureReportGenerator:
    """Testit SecureReportGenerator-luokalle"""
    
    def setup_method(self):
        """Alustetaan testit"""
        self.generator = SecureReportGenerator()
    
    def test_sanitize_html_basic(self):
        """Testi: HTML:n sanitointi"""
        dirty_html = "<script>alert('xss')</script><p>Clean content</p>"
        clean_html = self.generator.sanitize_html(dirty_html)
        
        assert "<script>" not in clean_html
        assert "<p>Clean content</p>" in clean_html
    
    def test_sanitize_html_dangerous_attributes(self):
        """Testi: Vaarallisten attribuuttien poisto"""
        dirty_html = '<img src="image.jpg" onload="alert(\'xss\')" alt="test">'
        clean_html = self.generator.sanitize_html(dirty_html)
        
        assert "onload" not in clean_html
        assert 'src="image.jpg"' in clean_html
        assert 'alt="test"' in clean_html
    
    def test_generate_secure_css_default(self):
        """Testi: Turvallisen CSS:n generointi"""
        css = self.generator.generate_secure_css()
        
        assert "body {" in css
        assert "font-family:" in css
        # Ei pitäisi sisältää vaarallisia CSS-ominaisuuksia
        assert "javascript:" not in css
        assert "expression(" not in css


@pytest.mark.asyncio
class TestDependencySecurityScanner:
    """Testit DependencySecurityScanner-luokalle"""
    
    def setup_method(self):
        """Alustetaan testit"""
        self.scanner = DependencySecurityScanner()
    
    @patch('subprocess.run')
    async def test_scan_with_safety_success(self, mock_run):
        """Testi: Onnistunut Safety-skannaus"""
        # Simuloi Safety-tulosta
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        result = await self.scanner.scan_dependencies("requirements.txt")
        
        assert result['scan_duration'] > 0
        assert 'packages_scanned' in result
        assert 'vulnerabilities' in result
    
    @patch('subprocess.run')
    async def test_scan_with_safety_vulnerabilities(self, mock_run):
        """Testi: Haavoittuvuuksien löytyminen"""
        # Simuloi Safety-tulosta haavoittuvuuksilla
        mock_run.return_value.returncode = 64  # Safety:n koodi haavoittuvuuksille
        mock_run.return_value.stdout = "requests==2.25.1\nCVE-2021-33503"
        mock_run.return_value.stderr = ""
        
        result = await self.scanner.scan_dependencies("requirements.txt")
        
        assert len(result['vulnerabilities']) > 0
        assert result['vulnerable_packages'] > 0
    
    def test_parse_safety_output_with_vulnerabilities(self):
        """Testi: Safety-tulosteen parsinta"""
        safety_output = """
        requests==2.25.1
        CVE-2021-33503: Vulnerability description
        """
        
        vulnerabilities = self.scanner._parse_safety_output(safety_output)
        
        assert len(vulnerabilities) > 0
        assert vulnerabilities[0]['package'] == 'requests'
        assert vulnerabilities[0]['version'] == '2.25.1'
        assert 'CVE-2021-33503' in vulnerabilities[0]['cve']
    
    def test_parse_safety_output_no_vulnerabilities(self):
        """Testi: Ei haavoittuvuuksia"""
        safety_output = ""
        
        vulnerabilities = self.scanner._parse_safety_output(safety_output)
        
        assert len(vulnerabilities) == 0


class TestSecurityIntegration:
    """Integraatiotestit turvallisuusmoduulille"""
    
    def test_validate_url_secure_function(self):
        """Testi: validate_url_secure-apufunktio"""
        # Kelvollinen URL
        assert validate_url_secure("https://example.com") is True
        
        # Virheellinen URL
        with pytest.raises(SecurityError):
            validate_url_secure("ftp://example.com")
    
    def test_sanitize_filename_secure_function(self):
        """Testi: sanitize_filename_secure-apufunktio"""
        # Turvallinen tiedostonimi
        result = sanitize_filename_secure("safe_file.txt")
        assert result == "safe_file.txt"
        
        # Vaarallinen tiedostonimi
        with pytest.raises(SecurityError):
            sanitize_filename_secure("../../etc/passwd")
    
    def test_request_security_middleware(self):
        """Testi: RequestSecurityMiddleware"""
        middleware = RequestSecurityMiddleware()
        
        # Simuloi Flask-pyyntö
        mock_request = Mock()
        mock_request.remote_addr = "127.0.0.1"
        mock_request.method = "GET"
        mock_request.endpoint = "test"
        
        with patch('flask.request', mock_request):
            # Ensimmäinen pyyntö pitäisi hyväksyä
            result = middleware.check_request_security()
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__])