"""Mukautetut poikkeusluokat saavutettavuusskannerille"""


class ScannerError(Exception):
    """Yleiset skannerin virheet"""

    def __init__(self, message: str, cause: Exception = None, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.error_code = error_code

    def __str__(self):
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class ReportError(Exception):
    """Raportin generoinnin virheet"""

    def __init__(self, message: str, report_type: str = None, cause: Exception = None):
        super().__init__(message)
        self.message = message
        self.report_type = report_type
        self.cause = cause

    def __str__(self):
        if self.report_type:
            return f"Report error ({self.report_type}): {self.message}"
        return f"Report error: {self.message}"


class ValidationError(ScannerError):
    """Validoinnin virheet"""

    def __init__(self, message: str, field: str = None, value: str = None):
        super().__init__(message)
        self.field = field
        self.value = value

    def __str__(self):
        if self.field:
            return f"Validation error for '{self.field}': {self.message}"
        return f"Validation error: {self.message}"


class NetworkError(ScannerError):
    """Verkkoliikenneen virheet"""

    def __init__(self, message: str, url: str = None, status_code: int = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code

    def __str__(self):
        parts = ["Network error"]
        if self.url:
            parts.append(f"for {self.url}")
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        parts.append(f": {self.message}")
        return " ".join(parts)


class BrowserError(ScannerError):
    """Selainauomaation virheet"""

    def __init__(self, message: str, browser_type: str = None, page_url: str = None):
        super().__init__(message)
        self.browser_type = browser_type
        self.page_url = page_url

    def __str__(self):
        parts = ["Browser error"]
        if self.browser_type:
            parts.append(f"({self.browser_type})")
        if self.page_url:
            parts.append(f"on {self.page_url}")
        parts.append(f": {self.message}")
        return " ".join(parts)


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


class AnalysisError(ScannerError):
    """Alt-teksti analyysin virheet"""

    def __init__(self, message: str, image_url: str = None, api_error: str = None):
        super().__init__(message)
        self.image_url = image_url
        self.api_error = api_error

    def __str__(self):
        parts = ["Analysis error"]
        if self.image_url:
            parts.append(f"for {self.image_url}")
        parts.append(f": {self.message}")
        if self.api_error:
            parts.append(f" (API error: {self.api_error})")
        return " ".join(parts)


class TimeoutError(ScannerError):
    """Aikakatkaisun virheet"""

    def __init__(
        self, message: str, timeout_seconds: int = None, operation: str = None
    ):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
        self.operation = operation

    def __str__(self):
        parts = ["Timeout error"]
        if self.operation:
            parts.append(f"in {self.operation}")
        if self.timeout_seconds:
            parts.append(f"after {self.timeout_seconds}s")
        parts.append(f": {self.message}")
        return " ".join(parts)


class FileError(Exception):
    """Tiedosto-operaatioiden virheet"""

    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message)
        self.message = message
        self.file_path = file_path
        self.operation = operation

    def __str__(self):
        parts = ["File error"]
        if self.operation:
            parts.append(f"({self.operation})")
        if self.file_path:
            parts.append(f"for {self.file_path}")
        parts.append(f": {self.message}")
        return " ".join(parts)


class SecurityError(ScannerError):
    """Turvallisuusvirheet"""

    def __init__(self, message: str, error_type: str = None, source: str = None):
        super().__init__(message)
        self.error_type = error_type
        self.source = source

    def __str__(self):
        parts = ["Security error"]
        if self.error_type:
            parts.append(f"({self.error_type})")
        if self.source:
            parts.append(f"from {self.source}")
        parts.append(f": {self.message}")
        return " ".join(parts)
