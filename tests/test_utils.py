"""Testit utils-moduulille"""

import pytest
import os
import sys
from unittest.mock import patch, Mock

# Lisää src polku
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils import (
    is_valid_url,
    sanitize_filename,
    ensure_directory_exists,
    get_timestamp,
    ScannerError,
    ReportError
)

class TestURLValidation:
    """Testit URL validoinnille"""
    
    def test_is_valid_url_valid_http(self):
        """Testi valideille HTTP URL:eille"""
        assert is_valid_url("http://example.com") is True
        assert is_valid_url("http://www.google.com") is True
        assert is_valid_url("http://subdomain.example.org/path?param=value") is True

    def test_is_valid_url_valid_https(self):
        """Testi valideille HTTPS URL:eille"""
        assert is_valid_url("https://example.com") is True
        assert is_valid_url("https://www.google.com") is True
        assert is_valid_url("https://api.example.com/v1/endpoint") is True

    def test_is_valid_url_invalid_scheme(self):
        """Testi virheellisille skeemoille"""
        assert is_valid_url("ftp://example.com") is False
        assert is_valid_url("file:///path/to/file") is False
        assert is_valid_url("mailto:test@example.com") is False

    def test_is_valid_url_no_scheme(self):
        """Testi URL:eille ilman skeemaa"""
        assert is_valid_url("example.com") is False
        assert is_valid_url("www.google.com") is False

    def test_is_valid_url_malformed(self):
        """Testi virheellisille URL:eille"""
        assert is_valid_url("not-a-url") is False
        assert is_valid_url("http://") is False
        assert is_valid_url("") is False
        assert is_valid_url(None) is False

    def test_is_valid_url_special_characters(self):
        """Testi erikoismerkeille URL:eissa"""
        assert is_valid_url("https://example.com/path with spaces") is True
        assert is_valid_url("https://example.com/path?query=värme") is True
        assert is_valid_url("https://example.com/path#fragment") is True

class TestFilenameTools:
    """Testit tiedostonimen työkaluille"""
    
    def test_sanitize_filename_basic(self):
        """Testi perustiedostonimen puhdistukselle"""
        assert sanitize_filename("test.txt") == "test.txt"
        assert sanitize_filename("simple_name") == "simple_name"

    def test_sanitize_filename_special_characters(self):
        """Testi erikoismerkkien puhdistukselle"""
        assert sanitize_filename("test/file.txt") == "test_file.txt"
        assert sanitize_filename("test\\file.txt") == "test_file.txt"
        assert sanitize_filename("test:file.txt") == "test_file.txt"
        assert sanitize_filename("test*file.txt") == "test_file.txt"
        assert sanitize_filename("test?file.txt") == "test_file.txt"
        assert sanitize_filename("test\"file\".txt") == "test_file_.txt"
        assert sanitize_filename("test<file>.txt") == "test_file_.txt"
        assert sanitize_filename("test|file.txt") == "test_file.txt"

    def test_sanitize_filename_spaces(self):
        """Testi välilyöntien käsittelylle"""
        assert sanitize_filename("test file.txt") == "test_file.txt"
        assert sanitize_filename("  test  file  .txt  ") == "test_file_.txt"

    def test_sanitize_filename_unicode(self):
        """Testi Unicode-merkkien käsittelylle"""
        assert sanitize_filename("testi_ää_öö.txt") == "testi_ää_öö.txt"
        assert sanitize_filename("测试文件.txt") == "测试文件.txt"

    def test_sanitize_filename_empty(self):
        """Testi tyhjälle tiedostonimelle"""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"

    def test_sanitize_filename_reserved_names(self):
        """Testi varatuille Windows-nimille"""
        assert sanitize_filename("CON.txt") == "CON_.txt"
        assert sanitize_filename("PRN.txt") == "PRN_.txt"
        assert sanitize_filename("AUX.txt") == "AUX_.txt"
        assert sanitize_filename("NUL.txt") == "NUL_.txt"

class TestDirectoryTools:
    """Testit hakemiston työkaluille"""
    
    def test_ensure_directory_exists_new_directory(self):
        """Testi uuden hakemiston luomiselle"""
        test_path = "/test/new/directory"
        
        with patch('src.utils.os.path.exists') as mock_exists:
            with patch('src.utils.os.makedirs') as mock_makedirs:
                mock_exists.return_value = False
                
                ensure_directory_exists(test_path)
                
                mock_exists.assert_called_once_with(test_path)
                mock_makedirs.assert_called_once_with(test_path, exist_ok=True)

    def test_ensure_directory_exists_existing_directory(self):
        """Testi olemassa olevalle hakemistolle"""
        test_path = "/existing/directory"
        
        with patch('src.utils.os.path.exists') as mock_exists:
            with patch('src.utils.os.makedirs') as mock_makedirs:
                mock_exists.return_value = True
                
                ensure_directory_exists(test_path)
                
                mock_exists.assert_called_once_with(test_path)
                mock_makedirs.assert_not_called()

    def test_ensure_directory_exists_permission_error(self):
        """Testi käyttöoikeusvirheelle"""
        test_path = "/restricted/directory"
        
        with patch('src.utils.os.path.exists') as mock_exists:
            with patch('src.utils.os.makedirs') as mock_makedirs:
                mock_exists.return_value = False
                mock_makedirs.side_effect = PermissionError("Permission denied")
                
                with pytest.raises(PermissionError):
                    ensure_directory_exists(test_path)

class TestTimestampTools:
    """Testit aikaleiman työkaluille"""
    
    def test_get_timestamp_format(self):
        """Testi aikaleiman muotoilun oikeellisuudelle"""
        with patch('src.utils.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "2024-01-15_14-30-45"
            mock_datetime.now.return_value = mock_now
            
            timestamp = get_timestamp()
            
            assert timestamp == "2024-01-15_14-30-45"
            mock_datetime.now.assert_called_once()
            mock_now.strftime.assert_called_once_with("%Y-%m-%d_%H-%M-%S")

    def test_get_timestamp_uniqueness(self):
        """Testi aikaisten leimaojen ainutlaatuisuudelle"""
        # Tämä on hieman teoreettinen testi, mutta tarkistaa että funktio toimii
        with patch('src.utils.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.side_effect = ["2024-01-15_14-30-45", "2024-01-15_14-30-46"]
            mock_datetime.now.return_value = mock_now
            
            timestamp1 = get_timestamp()
            timestamp2 = get_timestamp()
            
            # Ei välttämättä ole eri, mutta funktio toimii
            assert timestamp1 == "2024-01-15_14-30-45"
            assert timestamp2 == "2024-01-15_14-30-46"

class TestCustomExceptions:
    """Testit mukautetuille poikkeuksille"""
    
    def test_scanner_error_creation(self):
        """Testi ScannerError luomiselle"""
        error_msg = "Scanner failed to process URL"
        error = ScannerError(error_msg)
        
        assert str(error) == error_msg
        assert isinstance(error, Exception)

    def test_scanner_error_with_cause(self):
        """Testi ScannerError luomiselle syyn kanssa"""
        original_error = ValueError("Invalid URL format")
        scanner_error = ScannerError("Failed to validate URL", original_error)
        
        assert "Failed to validate URL" in str(scanner_error)

    def test_report_error_creation(self):
        """Testi ReportError luomiselle"""
        error_msg = "Failed to generate report"
        error = ReportError(error_msg)
        
        assert str(error) == error_msg
        assert isinstance(error, Exception)

    def test_report_error_inheritance(self):
        """Testi ReportError perinnälle"""
        error = ReportError("Test error")
        
        # Tarkista että se on oikean tyyppinen poikkeus
        assert isinstance(error, Exception)
        
        # Voidaan kiinnittää try-except lohkossa
        try:
            raise error
        except ReportError as e:
            assert str(e) == "Test error"
        except Exception:
            pytest.fail("ReportError should be caught as ReportError")

class TestUtilsIntegration:
    """Integraatiotestit utils-funktioille"""
    
    def test_file_workflow(self):
        """Testi täydelle tiedosto-työnkululle"""
        url = "https://example.com/test file.html"
        
        # Validoi URL
        assert is_valid_url(url) is True
        
        # Sanitoi tiedostonimi
        filename = sanitize_filename("test file.html")
        assert filename == "test_file.html"
        
        # Luo aikaleima
        with patch('src.utils.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "2024-01-15_14-30-45"
            mock_datetime.now.return_value = mock_now
            
            timestamp = get_timestamp()
            assert timestamp == "2024-01-15_14-30-45"

    def test_error_handling_workflow(self):
        """Testi virheiden käsittelyn työnkululle"""
        invalid_url = "not-a-valid-url"
        
        # URL validointi epäonnistuu
        assert is_valid_url(invalid_url) is False
        
        # Voi nostaa ScannerError
        with pytest.raises(ScannerError):
            if not is_valid_url(invalid_url):
                raise ScannerError(f"Invalid URL: {invalid_url}")

    def test_edge_cases(self):
        """Testi rajatapauksille"""
        # Tyhjät syötteet
        assert is_valid_url("") is False
        assert sanitize_filename("") == "unnamed"
        
        # None-arvot
        assert is_valid_url(None) is False
        
        # Hyvin pitkät syötteet
        long_url = "https://example.com/" + "a" * 1000
        assert is_valid_url(long_url) is True
        
        long_filename = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_filename)
        assert len(sanitized) <= 255  # Tyypillinen tiedostoniimi maksimi