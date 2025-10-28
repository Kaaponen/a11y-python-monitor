#!/usr/bin/env python3
"""
Migration script: Siirtyy vanhasta rakenteesta uuteen
Poistaa vanhat tiedostot ja päivittää viittaukset
"""

import os
import shutil
import sys
from pathlib import Path


def main():
    """Pääfunktio migration-skriptille"""

    print("🔄 Aloitetaan projektin migration...")

    # Varmista että olemme oikeassa hakemistossa
    if not os.path.exists("src"):
        print(
            "❌ Virhe: src/ hakemistoa ei löydy. Varmista että olet projektin juurihakemistossa."
        )
        sys.exit(1)

    # Vanhat tiedostot jotka voidaan poistaa turvallisesti
    old_files_to_remove = [
        "scanner.py",
        "sitemap.py",
        "reporter.py",
        "csv_export.py",
        "json_export.py",
        "ui.py",
    ]

    old_dirs_to_remove = ["backend", "components"]

    print("\n📂 Poistetaan vanhat tiedostot...")

    # Poista vanhat tiedostot
    for file_path in old_files_to_remove:
        if os.path.exists(file_path):
            print(f"  🗑️  Poistetaan: {file_path}")
            os.remove(file_path)
        else:
            print(f"  ✅ Ei löydy: {file_path}")

    # Poista vanhat hakemistot
    for dir_path in old_dirs_to_remove:
        if os.path.exists(dir_path):
            print(f"  🗑️  Poistetaan hakemisto: {dir_path}")
            shutil.rmtree(dir_path)
        else:
            print(f"  ✅ Ei löydy: {dir_path}")

    print("\n✅ Migration valmis!")
    print("\n📋 Seuraavat vaiheet:")
    print("  1. Testaa sovellus: python app.py")
    print("  2. Testaa CLI: python cli.py https://example.com")
    print("  3. Aja testit: make test")
    print("  4. Päivitä riippuvuudet: pip install -r requirements.txt")

    # Tarkista että tärkeimmät tiedostot löytyvät
    critical_files = [
        "src/scanner/core.py",
        "src/scanner/sitemap.py",
        "src/reports/reporter.py",
        "src/ui/streamlit_app.py",
        "app.py",
        "cli.py",
    ]

    print("\n🔍 Tarkistetaan kriittiset tiedostot:")
    all_good = True
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ PUUTTUU: {file_path}")
            all_good = False

    if all_good:
        print("\n🎉 Kaikki tiedostot löytyvät! Projekti on valmis käytettäväksi.")
    else:
        print("\n⚠️  Jotkut tiedostot puuttuvat. Tarkista migration.")


if __name__ == "__main__":
    main()
