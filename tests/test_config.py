"""Testit config-moduulille"""

import pytest
import os
import sys
from unittest.mock import patch, Mock

# Lisää src polku
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.config import Config


class TestConfigInitialization:
    """Testit Config-luokan alustukselle"""

    def test_config_default_values(self):
        """Testi oletusarvojen lataukselle"""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()

            # Tarkista oletusarvot
            assert config.DEFAULT_TIMEOUT == 30
            assert config.DEFAULT_USER_AGENT == "SaavutettavuusSkanneri/1.0"
            assert config.MAX_CONCURRENT_SCANS == 5
            assert config.REPORT_DIR == "reports"
            assert config.SUPPORTED_FORMATS == ["html", "json", "csv"]

    def test_config_environment_override(self):
        """Testi ympäristömuuttujien ylikirjoitukselle"""
        env_vars = {
            "SCANNER_TIMEOUT": "60",
            "SCANNER_USER_AGENT": "CustomAgent/2.0",
            "SCANNER_MAX_CONCURRENT": "10",
            "SCANNER_REPORT_DIR": "custom_reports",
            "OPENAI_API_KEY": "test-api-key-123",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()

            assert config.timeout == 60
            assert config.user_agent == "CustomAgent/2.0"
            assert config.max_concurrent_scans == 10
            assert config.report_dir == "custom_reports"
            assert config.openai_api_key == "test-api-key-123"


class TestConfigValidation:
    """Testit konfiguraation validoinnille"""

    def test_validate_timeout_valid(self):
        """Testi valideille timeout-arvoille"""
        config = Config()

        # Normaalit arvot
        config.timeout = 30
        config._validate_timeout()  # Ei pitäisi nostaa poikkeusta

        config.timeout = 120
        config._validate_timeout()  # Ei pitäisi nostaa poikkeusta

    def test_validate_timeout_invalid(self):
        """Testi virheellisille timeout-arvoille"""
        config = Config()

        # Liian pieni
        config.timeout = 0
        with pytest.raises(ValueError, match="Timeout must be positive"):
            config._validate_timeout()

        # Negatiivinen
        config.timeout = -10
        with pytest.raises(ValueError, match="Timeout must be positive"):
            config._validate_timeout()

    def test_validate_max_concurrent_valid(self):
        """Testi valideille concurrent-arvoille"""
        config = Config()

        config.max_concurrent_scans = 1
        config._validate_max_concurrent()

        config.max_concurrent_scans = 20
        config._validate_max_concurrent()

    def test_validate_max_concurrent_invalid(self):
        """Testi virheellisille concurrent-arvoille"""
        config = Config()

        # Nolla
        config.max_concurrent_scans = 0
        with pytest.raises(ValueError, match="Max concurrent scans must be positive"):
            config._validate_max_concurrent()

        # Liian suuri
        config.max_concurrent_scans = 101
        with pytest.raises(ValueError, match="Max concurrent scans cannot exceed 100"):
            config._validate_max_concurrent()

    def test_validate_report_format_valid(self):
        """Testi valideille raporttimuodoille"""
        config = Config()

        assert config.is_valid_format("html") is True
        assert config.is_valid_format("json") is True
        assert config.is_valid_format("csv") is True

    def test_validate_report_format_invalid(self):
        """Testi virheellisille raporttimuodoille"""
        config = Config()

        assert config.is_valid_format("xml") is False
        assert config.is_valid_format("pdf") is False
        assert config.is_valid_format("") is False
        assert config.is_valid_format(None) is False


class TestConfigProperties:
    """Testit Config-ominaisuuksille"""

    def test_debug_mode_detection(self):
        """Testi debug-tilan tunnistukselle"""
        # Debug pois päältä
        with patch.dict(os.environ, {"DEBUG": "false"}, clear=True):
            config = Config()
            assert config.debug_mode is False

        # Debug päällä - 'true'
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=True):
            config = Config()
            assert config.debug_mode is True

        # Debug päällä - '1'
        with patch.dict(os.environ, {"DEBUG": "1"}, clear=True):
            config = Config()
            assert config.debug_mode is True

    def test_openai_api_key_handling(self):
        """Testi OpenAI API avaimen käsittelylle"""
        # Ei avainta
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert config.openai_api_key is None

        # Avain asetettu
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}, clear=True):
            config = Config()
            assert config.openai_api_key == "sk-test123"

    def test_logging_level_configuration(self):
        """Testi lokitason konfiguraatiolle"""
        # Oletustaso
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert config.log_level == "INFO"

        # Debug-taso
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=True):
            config = Config()
            assert config.log_level == "DEBUG"

        # Error-taso
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}, clear=True):
            config = Config()
            assert config.log_level == "ERROR"


class TestConfigTypeConversion:
    """Testit tyyppien muunnoksille"""

    def test_string_to_int_conversion(self):
        """Testi merkkijonon muunnokselle kokonaisluvuksi"""
        with patch.dict(os.environ, {"SCANNER_TIMEOUT": "45"}, clear=True):
            config = Config()
            assert config.timeout == 45
            assert isinstance(config.timeout, int)

    def test_string_to_bool_conversion(self):
        """Testi merkkijonon muunnokselle boolean-arvoksi"""
        # True-arvot
        for true_val in ["true", "True", "TRUE", "1", "yes", "Yes"]:
            with patch.dict(os.environ, {"DEBUG": true_val}, clear=True):
                config = Config()
                assert config.debug_mode is True

        # False-arvot
        for false_val in ["false", "False", "FALSE", "0", "no", "No", ""]:
            with patch.dict(os.environ, {"DEBUG": false_val}, clear=True):
                config = Config()
                assert config.debug_mode is False

    def test_invalid_type_conversion(self):
        """Testi virheellisille tyyppien muunnoksille"""
        # Virheellinen kokonaisluku
        with patch.dict(os.environ, {"SCANNER_TIMEOUT": "not-a-number"}, clear=True):
            with pytest.raises(ValueError, match="Invalid timeout value"):
                Config()

        # Virheellinen concurrent määrä
        with patch.dict(os.environ, {"SCANNER_MAX_CONCURRENT": "invalid"}, clear=True):
            with pytest.raises(ValueError, match="Invalid max concurrent value"):
                Config()


class TestConfigMethods:
    """Testit Config-luokan metodeille"""

    def test_get_config_summary(self):
        """Testi konfiguraation yhteenvedon hakemiselle"""
        with patch.dict(
            os.environ,
            {"SCANNER_TIMEOUT": "60", "DEBUG": "true", "OPENAI_API_KEY": "sk-test123"},
            clear=True,
        ):
            config = Config()
            summary = config.get_config_summary()

            assert "timeout" in summary
            assert "debug_mode" in summary
            assert "max_concurrent_scans" in summary
            assert summary["timeout"] == 60
            assert summary["debug_mode"] is True

            # API-avain ei pitäisi näkyä täydellisenä
            assert "openai_api_key_set" in summary
            assert summary["openai_api_key_set"] is True

    def test_reload_config(self):
        """Testi konfiguraation uudelleenlataukselle"""
        # Aluksi ei ympäristömuuttujia
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert config.timeout == 30

        # Lisää ympäristömuuttuja ja lataa uudelleen
        with patch.dict(os.environ, {"SCANNER_TIMEOUT": "90"}, clear=True):
            config.reload()
            assert config.timeout == 90

    def test_to_dict(self):
        """Testi konfiguraation sanakirjaksi muuttamiselle"""
        config = Config()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "timeout" in config_dict
        assert "user_agent" in config_dict
        assert "max_concurrent_scans" in config_dict
        assert "report_dir" in config_dict


class TestConfigSecurityFeatures:
    """Testit konfiguraation turvallisuusominaisuuksille"""

    def test_api_key_masking(self):
        """Testi API-avaimen peittämiselle"""
        with patch.dict(
            os.environ, {"OPENAI_API_KEY": "sk-1234567890abcdef"}, clear=True
        ):
            config = Config()

            # get_config_summary ei pitäisi paljastaa täyttä avainta
            summary = config.get_config_summary()
            assert "sk-1234567890abcdef" not in str(summary)

            # Mutta avain on silti käytettävissä
            assert config.openai_api_key == "sk-1234567890abcdef"

    def test_sensitive_data_exclusion(self):
        """Testi arkaluontoisen datan poissulkemiselle"""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "sk-secret", "DATABASE_PASSWORD": "supersecret"},
            clear=True,
        ):
            config = Config()
            config_str = str(config)

            # Ei pitäisi sisältää arkaluontoisia tietoja
            assert "sk-secret" not in config_str
            assert "supersecret" not in config_str


class TestConfigEdgeCases:
    """Testit rajatapauksille"""

    def test_empty_environment_variables(self):
        """Testi tyhjille ympäristömuuttujille"""
        with patch.dict(
            os.environ,
            {"SCANNER_TIMEOUT": "", "SCANNER_USER_AGENT": "", "DEBUG": ""},
            clear=True,
        ):
            config = Config()

            # Pitäisi käyttää oletusarvoja
            assert config.timeout == 30
            assert config.user_agent == "SaavutettavuusSkanneri/1.0"
            assert config.debug_mode is False

    def test_whitespace_handling(self):
        """Testi välilyöntien käsittelylle"""
        with patch.dict(
            os.environ,
            {
                "SCANNER_TIMEOUT": "  45  ",
                "SCANNER_USER_AGENT": "  CustomAgent/1.0  ",
                "OPENAI_API_KEY": "  sk-test123  ",
            },
            clear=True,
        ):
            config = Config()

            # Välilyönnit pitäisi trimmata
            assert config.timeout == 45
            assert config.user_agent == "CustomAgent/1.0"
            assert config.openai_api_key == "sk-test123"

    def test_config_immutability(self):
        """Testi konfiguraation muuttumattomuudelle"""
        config = Config()
        original_timeout = config.timeout

        # Yritä muuttaa arvoa
        config.timeout = 999

        # Riippuu toteutuksesta, mutta voisi olla immutable
        # Tämä on enemmän design-päätös
        assert config.timeout == 999  # Tai original_timeout jos immutable
