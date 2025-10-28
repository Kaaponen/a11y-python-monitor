#!/usr/bin/env python3
"""
A11y Scanner - Entry point for Streamlit UI
"""

import sys
import os

# Lisää src-hakemisto Python pathiin
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

#!/usr/bin/env python3
"""
Simple app launcher for Saavutettavuusskanneri
Käynnistin Streamlit UI:lle
"""
import os
import sys
import subprocess
from pathlib import Path


def main():
    """Käynnistä Streamlit-sovellus"""

    # Varmista että ollaan oikeassa hakemistossa
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Lisää projekti Python pathiin
    sys.path.insert(0, str(project_root))

    print("🚀 Käynnistetään Saavutettavuusskanneri...")
    print("📍 Projektin hakemisto:", project_root)
    print("🐍 Python-versio:", sys.version)

    # Tarkista että Streamlit on asennettu
    try:
        import streamlit

        print("✅ Streamlit löytyi:", streamlit.__version__)
    except ImportError:
        print("❌ Streamlit ei ole asennettu!")
        print("Asenna komennolla: pip install streamlit")
        return 1

    # Tarkista että Playwright on asennettu
    try:
        import playwright

        print("✅ Playwright löytyi")
    except ImportError:
        print("❌ Playwright ei ole asennettu!")
        print("Asenna komennolla: pip install playwright && playwright install")
        return 1

    # Streamlit app path
    app_path = project_root / "src" / "ui" / "streamlit_app.py"

    if not app_path.exists():
        print(f"❌ Streamlit app ei löydy: {app_path}")
        return 1

    print(f"📱 Käynnistetään Streamlit app: {app_path}")
    print("🌐 Avaa selaimessa: http://localhost:8501")
    print("⏹️  Lopeta painamalla Ctrl+C")
    print("-" * 50)

    try:
        # Käynnistä Streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Suljetaan Saavutettavuusskanneri...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Virhe käynnistäessä: {e}")
        return 1
    except Exception as e:
        print(f"❌ Odottamaton virhe: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
