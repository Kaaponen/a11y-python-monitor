"""Konfiguraationhallinta ympäristömuuttujien ja asetusten kanssa"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


class ConfigurationError(Exception):
    """Konfiguraation virheet"""
    
    def __init__(self, message: str, config_key: str = None, config_value: str = None):
        super().__init__(message)
        self.message = message
        self.config_key = config_key
        self.config_value = config_value
    
    def __str__(self):
        if self.config_key:
            return f"Configuration error for '{self.config_key}': {self.message}"
        return f"Configuration error: {self.message}"


@dataclass
class LoggingConfig:
    """Lokituksen konfiguraatio"""
    level: str = "INFO"
    structured: bool = True
    file_path: Optional[str] = None
    include_console: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 5


@dataclass
class ScannerConfig:
    """Skannerin konfiguraatio"""
    timeout: int = 30
    user_agent: str = "SaavutettavuusSkanneri/1.0"
    max_concurrent_scans: int = 5
    browser_type: str = "chromium"  # chromium, firefox, webkit
    headless: bool = True
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class ReportsConfig:
    """Raporttien konfiguraatio"""
    output_dir: str = "reports"
    default_format: str = "html"
    supported_formats: List[str] = field(default_factory=lambda: ["html", "json", "csv", "markdown"])
    include_screenshots: bool = False
    compress_reports: bool = False


@dataclass
class AnalysisConfig:
    """Alt-teksti analyysin konfiguraatio"""
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-vision-preview"
    max_image_size_mb: int = 20
    analysis_timeout: int = 30
    enable_caching: bool = True
    cache_ttl_hours: int = 24


@dataclass
class PerformanceConfig:
    """Suorituskyvyn konfiguraatio"""
    max_memory_mb: int = 500
    max_disk_usage_mb: int = 1000
    cleanup_interval_hours: int = 24
    metrics_enabled: bool = True
    profiling_enabled: bool = False


class Config:
    """Pääkonfiguraatioluokka joka yhdistää kaikki asetukset"""
    
    def __init__(self):
        self.logging = LoggingConfig()
        self.scanner = ScannerConfig()
        self.reports = ReportsConfig()
        self.analysis = AnalysisConfig()
        self.performance = PerformanceConfig()
        
        # Lataa asetukset ympäristömuuttujista
        self._load_from_environment()
        
        # Validoi konfiguraatio
        self._validate()
    
    def _load_from_environment(self):
        """Lataa asetukset ympäristömuuttujista"""
        
        # Logging
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level)
        self.logging.structured = self._get_bool_env("LOG_STRUCTURED", self.logging.structured)
        self.logging.file_path = os.getenv("LOG_FILE_PATH", self.logging.file_path)
        self.logging.include_console = self._get_bool_env("LOG_INCLUDE_CONSOLE", self.logging.include_console)
        
        # Scanner
        self.scanner.timeout = self._get_int_env("SCANNER_TIMEOUT", self.scanner.timeout)
        self.scanner.user_agent = os.getenv("SCANNER_USER_AGENT", self.scanner.user_agent)
        self.scanner.max_concurrent_scans = self._get_int_env("SCANNER_MAX_CONCURRENT", self.scanner.max_concurrent_scans)
        self.scanner.browser_type = os.getenv("SCANNER_BROWSER_TYPE", self.scanner.browser_type)
        self.scanner.headless = self._get_bool_env("SCANNER_HEADLESS", self.scanner.headless)
        
        # Reports
        self.reports.output_dir = os.getenv("REPORTS_OUTPUT_DIR", self.reports.output_dir)
        self.reports.default_format = os.getenv("REPORTS_DEFAULT_FORMAT", self.reports.default_format)
        self.reports.include_screenshots = self._get_bool_env("REPORTS_INCLUDE_SCREENSHOTS", self.reports.include_screenshots)
        
        # Analysis
        self.analysis.openai_api_key = os.getenv("OPENAI_API_KEY", self.analysis.openai_api_key)
        self.analysis.openai_model = os.getenv("OPENAI_MODEL", self.analysis.openai_model)
        self.analysis.max_image_size_mb = self._get_int_env("ANALYSIS_MAX_IMAGE_SIZE_MB", self.analysis.max_image_size_mb)
        
        # Performance
        self.performance.max_memory_mb = self._get_int_env("PERFORMANCE_MAX_MEMORY_MB", self.performance.max_memory_mb)
        self.performance.metrics_enabled = self._get_bool_env("PERFORMANCE_METRICS_ENABLED", self.performance.metrics_enabled)
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Hae boolean-arvo ympäristömuuttujasta"""
        value = os.getenv(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off"):
            return False
        else:
            return default
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Hae kokonaisluku-arvo ympäristömuuttujasta"""
        try:
            value = os.getenv(key)
            return int(value) if value else default
        except ValueError:
            raise ConfigurationError(f"Invalid integer value for {key}: {os.getenv(key)}", key)
    
    def _get_float_env(self, key: str, default: float) -> float:
        """Hae liukuluku-arvo ympäristömuuttujasta"""
        try:
            value = os.getenv(key)
            return float(value) if value else default
        except ValueError:
            raise ConfigurationError(f"Invalid float value for {key}: {os.getenv(key)}", key)
    
    def _validate(self):
        """Validoi konfiguraatio"""
        
        # Validoi log-taso
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level.upper() not in valid_log_levels:
            raise ConfigurationError(f"Invalid log level: {self.logging.level}", "LOG_LEVEL")
        
        # Validoi timeout
        if self.scanner.timeout <= 0:
            raise ConfigurationError("Scanner timeout must be positive", "SCANNER_TIMEOUT")
        
        if self.scanner.timeout > 300:  # 5 minuuttia maksimi
            raise ConfigurationError("Scanner timeout cannot exceed 300 seconds", "SCANNER_TIMEOUT")
        
        # Validoi samanaikaisten skannauksien määrä
        if self.scanner.max_concurrent_scans <= 0:
            raise ConfigurationError("Max concurrent scans must be positive", "SCANNER_MAX_CONCURRENT")
        
        if self.scanner.max_concurrent_scans > 100:
            raise ConfigurationError("Max concurrent scans cannot exceed 100", "SCANNER_MAX_CONCURRENT")
        
        # Validoi selaintyyppi
        valid_browsers = ["chromium", "firefox", "webkit"]
        if self.scanner.browser_type not in valid_browsers:
            raise ConfigurationError(f"Invalid browser type: {self.scanner.browser_type}", "SCANNER_BROWSER_TYPE")
        
        # Validoi raporttiformaatti
        if self.reports.default_format not in self.reports.supported_formats:
            raise ConfigurationError(f"Default format not in supported formats", "REPORTS_DEFAULT_FORMAT")
        
        # Validoi muistiraja
        if self.performance.max_memory_mb <= 0:
            raise ConfigurationError("Max memory must be positive", "PERFORMANCE_MAX_MEMORY_MB")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Hae konfiguraation yhteenveto (ilman arkaluontoisia tietoja)"""
        return {
            "logging": {
                "level": self.logging.level,
                "structured": self.logging.structured,
                "file_enabled": bool(self.logging.file_path),
                "console_enabled": self.logging.include_console
            },
            "scanner": {
                "timeout": self.scanner.timeout,
                "max_concurrent": self.scanner.max_concurrent_scans,
                "browser_type": self.scanner.browser_type,
                "headless": self.scanner.headless
            },
            "reports": {
                "output_dir": self.reports.output_dir,
                "default_format": self.reports.default_format,
                "supported_formats": self.reports.supported_formats
            },
            "analysis": {
                "openai_configured": bool(self.analysis.openai_api_key),
                "model": self.analysis.openai_model,
                "max_image_size_mb": self.analysis.max_image_size_mb
            },
            "performance": {
                "max_memory_mb": self.performance.max_memory_mb,
                "metrics_enabled": self.performance.metrics_enabled
            }
        }
    
    def is_development_mode(self) -> bool:
        """Tarkista onko kehitystila päällä"""
        return os.getenv("ENVIRONMENT", "production").lower() in ("development", "dev", "debug")
    
    def is_production_mode(self) -> bool:
        """Tarkista onko tuotantotila päällä"""
        return not self.is_development_mode()
    
    def reload(self):
        """Lataa konfiguraatio uudelleen"""
        self._load_from_environment()
        self._validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """Muunna konfiguraatio sanakirjaksi"""
        return {
            "logging": self.logging.__dict__,
            "scanner": self.scanner.__dict__,
            "reports": self.reports.__dict__,
            "analysis": {
                **self.analysis.__dict__,
                "openai_api_key": "***masked***" if self.analysis.openai_api_key else None
            },
            "performance": self.performance.__dict__
        }


# Globaali konfiguraatio-instanssi
config = Config()