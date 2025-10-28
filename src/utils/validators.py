"""Validointi- ja sanitointi-funktiot"""

import re
import os
from urllib.parse import urlparse
from typing import Optional


def is_valid_url(url: Optional[str]) -> bool:
    """
    Tarkista onko URL validi HTTP/HTTPS osoite

    Args:
        url: Tarkistettava URL

    Returns:
        True jos URL on validi, muuten False
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Puhdista tiedostonimi poistamalla virheelliset merkit

    Args:
        filename: Alkuperäinen tiedostonimi

    Returns:
        Puhdistettu tiedostonimi
    """
    if not filename or not filename.strip():
        return "unnamed"

    # Poista/korvaa virheelliset merkit
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename.strip())

    # Korvaa välilyönnit allaviivoilla
    sanitized = re.sub(r"\s+", "_", sanitized)

    # Poista peräkkäiset alaviivat
    sanitized = re.sub(r"_+", "_", sanitized)

    # Poista alaviivat alusta ja lopusta
    sanitized = sanitized.strip("_")

    # Tarkista varatut Windows-nimet
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

    name_without_ext = os.path.splitext(sanitized)[0].upper()
    if name_without_ext in reserved_names:
        sanitized = sanitized + "_"

    # Rajoita pituus
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        max_name_len = 255 - len(ext)
        sanitized = name[:max_name_len] + ext

    return sanitized or "unnamed"


def validate_report_format(format_type: str) -> bool:
    """
    Tarkista onko raporttiformaatti tuettu

    Args:
        format_type: Raportin muoto

    Returns:
        True jos tuettu, muuten False
    """
    supported_formats = {"html", "json", "csv", "markdown"}
    return format_type.lower() in supported_formats


def validate_scan_timeout(timeout: int) -> bool:
    """
    Tarkista onko skannauksen timeout-arvo järkevä

    Args:
        timeout: Timeout sekunteina

    Returns:
        True jos validi, muuten False
    """
    return isinstance(timeout, int) and 1 <= timeout <= 300  # 1s - 5min


def validate_concurrent_limit(limit: int) -> bool:
    """
    Tarkista onko samanaikaisten skannauksien määrä järkevä

    Args:
        limit: Samanaikaisten skannauksien maksimimäärä

    Returns:
        True jos validi, muuten False
    """
    return isinstance(limit, int) and 1 <= limit <= 50


def sanitize_url(url: str) -> str:
    """
    Puhdista ja normalisoi URL

    Args:
        url: Alkuperäinen URL

    Returns:
        Puhdistettu URL
    """
    if not url:
        return ""

    url = url.strip()

    # Lisää protokolla jos puuttuu
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Poista turhat parametrit
    try:
        parsed = urlparse(url)
        # Normalisoi path (poista tupla-slashit yms)
        normalized_path = re.sub(r"/+", "/", parsed.path)

        return f"{parsed.scheme}://{parsed.netloc}{normalized_path}"
    except Exception:
        return url


def validate_email(email: str) -> bool:
    """
    Tarkista onko sähköpostiosoite validi (yksinkertainen validointi)

    Args:
        email: Sähköpostiosoite

    Returns:
        True jos validi, muuten False
    """
    if not email or not isinstance(email, str):
        return False

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))
