# config.py
"""Projektin konfiguraatiotiedosto"""

import os
from typing import Optional

# Versio
VERSION = "1.0.0"

# Oletusarvot
DEFAULT_OUTPUT_DIR = "reports"
DEFAULT_TIMEOUT = 30000  # ms
DEFAULT_HEADLESS = True

# Axe-core versio
AXE_JS_VERSION = "4.8.2"
AXE_JS_URL = f"https://cdnjs.cloudflare.com/ajax/libs/axe-core/{AXE_JS_VERSION}/axe.min.js"

# OpenAI konfiguraatio
OPENAI_MODEL = "gpt-4o"
OPENAI_MAX_TOKENS = 150

# Streamlit konfiguraatio
STREAMLIT_PORT = 8501
STREAMLIT_HOST = "0.0.0.0"

# Lokitusasetukset
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def get_openai_api_key() -> Optional[str]:
    """Hakee OpenAI API-avaimen ympäristömuuttujista"""
    return os.getenv("OPENAI_API_KEY")

def get_output_dir() -> str:
    """Hakee tulosteen hakemiston"""
    return os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)