"""Setup script for A11y Scanner"""

from setuptools import setup, find_packages
import os


# Määritä src-paketti löydökseen
def find_packages_in_src():
    """Löydä paketit src/ hakemistosta"""
    packages = []
    for dirpath, dirnames, filenames in os.walk("src"):
        if "__init__.py" in filenames:
            # Muunna polku paketin nimeksi (src/scanner -> src.scanner)
            package = dirpath.replace(os.path.sep, ".")
            packages.append(package)
    return packages


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="a11y-scanner",
    version="1.0.0",
    author="Saavutettavuusskanneri Team",
    description="Python-pohjainen saavutettavuustyökalu",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages_in_src(),
    package_dir={"": "."},  # Paketit löytyvät juurihakemistosta
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": ["pytest", "pytest-asyncio", "black", "flake8", "mypy"],
    },
    entry_points={
        "console_scripts": [
            "a11y-scan=cli:main",
            "a11y-ui=app:main",
        ],
    },
)
