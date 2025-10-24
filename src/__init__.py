# src/__init__.py
"""A11y Scanner - Python-pohjainen saavutettavuustyökalu"""

__version__ = "1.0.0"
__author__ = "Saavutettavuusskanneri Team"
__description__ = "Python-pohjainen saavutettavuustyökalu, joka käyttää Playwright-selainta ja axe-core-kirjastoa"

# Viedään tärkeimmät funktiot käytön helpottamiseksi
from .scanner.core import run_axe
from .scanner.sitemap import get_urls_from_sitemap
from .reports.reporter import save_report

__all__ = [
    "run_axe",
    "get_urls_from_sitemap", 
    "save_report",
]