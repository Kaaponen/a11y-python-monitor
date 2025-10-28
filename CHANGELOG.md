# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GitHub Actions CI/CD pipeline
- Automated testing for multiple Python versions (3.8-3.11)
- Code quality checks (flake8, black, mypy)
- Security scanning (bandit, safety)
- Docker image building and publishing
- Automated releases with PyPI publishing
- SonarCloud integration for code quality analysis

### Changed

- Project structure reorganized into logical modules
- All imports updated for new structure
- Entry points updated (app.py for UI, cli.py for CLI)

### Fixed

- Import dependencies and circular imports resolved
- Better error handling and logging

## [1.0.0] - 2025-10-24

### Added

- Initial release of A11y Scanner
- Web-based UI with Streamlit
- Command-line interface
- Support for single page and sitemap-based scanning
- Multiple export formats (HTML, Markdown, CSV, JSON)
- AI-powered alt text analysis with GPT-4o
- Docker support
- Comprehensive documentation

### Features

- Playwright + axe-core integration for accessibility testing
- Sitemap.xml parsing for bulk scanning
- Detailed accessibility reports with impact levels
- OpenAI integration for alt text suggestions
- Modern Python project structure with type hints
