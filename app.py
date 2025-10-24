#!/usr/bin/env python3
"""
A11y Scanner - Entry point for Streamlit UI
"""

import sys
import os

# Lisää src-hakemisto Python pathiin
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Käynnistä Streamlit sovellus
if __name__ == "__main__":
    import subprocess
    streamlit_app_path = os.path.join(os.path.dirname(__file__), 'src', 'ui', 'streamlit_app.py')
    subprocess.run([sys.executable, '-m', 'streamlit', 'run', streamlit_app_path] + sys.argv[1:])