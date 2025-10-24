"""Strukturoitu logging-järjestelmä saavutettavuusskannerille"""

import logging
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """JSON-muotoinen log formatter strukturoidulle lokitukselle"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Muotoile log-merkintä JSON-muotoon"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Lisää kontekstitietoja jos saatavilla
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'url'):
            log_entry["url"] = record.url
        if hasattr(record, 'duration'):
            log_entry["duration_ms"] = record.duration
        if hasattr(record, 'scan_id'):
            log_entry["scan_id"] = record.scan_id
        if hasattr(record, 'violation_count'):
            log_entry["violation_count"] = record.violation_count
        if hasattr(record, 'error_code'):
            log_entry["error_code"] = record.error_code
            
        # Lisää exception-tiedot jos virhe
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        return json.dumps(log_entry, ensure_ascii=False)


class ScannerLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter skannerin kontekstitietojen lisäämiseen"""
    
    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Lisää kontekstitiedot log-merkintään"""
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs
    
    def scan_started(self, url: str, scan_id: str) -> None:
        """Lokita skannauksen aloitus"""
        self.info("Scan started", extra={
            "event": "scan_started",
            "url": url,
            "scan_id": scan_id
        })
    
    def scan_completed(self, url: str, scan_id: str, duration: float, violation_count: int) -> None:
        """Lokita skannauksen valmistuminen"""
        self.info("Scan completed", extra={
            "event": "scan_completed", 
            "url": url,
            "scan_id": scan_id,
            "duration": duration,
            "violation_count": violation_count
        })
    
    def scan_failed(self, url: str, scan_id: str, error: Exception, duration: float) -> None:
        """Lokita skannauksen epäonnistuminen"""
        self.error("Scan failed", extra={
            "event": "scan_failed",
            "url": url, 
            "scan_id": scan_id,
            "duration": duration,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }, exc_info=True)
    
    def report_generated(self, report_type: str, file_path: str, size_bytes: int) -> None:
        """Lokita raportin generointi"""
        self.info("Report generated", extra={
            "event": "report_generated",
            "report_type": report_type,
            "file_path": file_path,
            "size_bytes": size_bytes
        })


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    structured: bool = True,
    include_console: bool = True
) -> None:
    """
    Konfiguroi logging-järjestelmä
    
    Args:
        level: Log-taso (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Tiedostopolku lokitukselle (vapaaehtoinen)
        structured: Käytä JSON-muotoista lokitusta
        include_console: Sisällytä console-output
    """
    
    # Poista aiemmat handlerit
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Aseta log-taso
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Valitse formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Varmista että log-hakemisto on olemassa
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str, **context) -> ScannerLoggerAdapter:
    """
    Hae logger kontekstitiedoilla
    
    Args:
        name: Logger-nimi (yleensä __name__)
        **context: Kontekstitiedot (esim. user_id, request_id)
    
    Returns:
        ScannerLoggerAdapter jossa kontekstitiedot
    """
    logger = logging.getLogger(name)
    return ScannerLoggerAdapter(logger, context)


def log_performance(func):
    """Decorator suorituskyvyn mittaamiseen ja lokitukseen"""
    import functools
    import time
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000  # millisekuntia
            
            logger.info("Function completed", extra={
                "event": "function_completed",
                "function": func.__name__,
                "duration": duration
            })
            
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            logger.error("Function failed", extra={
                "event": "function_failed", 
                "function": func.__name__,
                "duration": duration,
                "error_type": type(e).__name__
            }, exc_info=True)
            
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            
            logger.info("Function completed", extra={
                "event": "function_completed",
                "function": func.__name__,
                "duration": duration
            })
            
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            logger.error("Function failed", extra={
                "event": "function_failed",
                "function": func.__name__,
                "duration": duration, 
                "error_type": type(e).__name__
            }, exc_info=True)
            
            raise
    
    # Tunnista async vs sync funktio
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Yleiset logger-instanssit
scanner_logger = get_logger("scanner")
reports_logger = get_logger("reports") 
analysis_logger = get_logger("analysis")
ui_logger = get_logger("ui")