# utils.py
"""Yleiset apufunktiot"""

import logging
import validators
from urllib.parse import urlparse
from typing import Optional, List
from config import LOG_LEVEL, LOG_FORMAT

def setup_logging() -> logging.Logger:
    """Konfiguroi lokituksen"""
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
    return logging.getLogger(__name__)

logger = setup_logging()

def validate_url(url: str) -> bool:
    """Validoi URL:n muodon ja turvallisuuden"""
    if not url:
        return False
    
    # Tarkista URL:n muoto
    if not validators.url(url):
        return False
    
    # Tarkista protokolla (vain HTTP/HTTPS sallittu)
    parsed = urlparse(url)
    if parsed.scheme not in ['http', 'https']:
        logger.warning(f"Epäturvallinen protokolla: {parsed.scheme}")
        return False
    
    # Estä localhost/private IP:t tuotannossa (valinnainen)
    if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
        logger.info(f"Localhost URL havaittu: {url}")
    
    return True

def validate_urls(urls: List[str]) -> List[str]:
    """Validoi URL-listan ja palauttaa vain kelvot"""
    valid_urls = []
    for url in urls:
        if validate_url(url):
            valid_urls.append(url)
        else:
            logger.warning(f"Virheellinen URL ohitettu: {url}")
    return valid_urls

def sanitize_filename(filename: str) -> str:
    """Puhdistaa tiedostonimen vaarallisista merkeistä"""
    import re
    # Poista/korvaa vaaralliset merkit
    sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
    # Varmista että tiedostonimi ei ole liian pitkä
    return sanitized[:100]

class CustomException(Exception):
    """Mukautettu poikkeusluokka projektille"""
    pass

class ScannerError(CustomException):
    """Skannaustapahtuman virhe"""
    pass

class ValidationError(CustomException):
    """Validointivirhe"""
    pass