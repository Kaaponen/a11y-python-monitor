# tests/test_scanner.py
"""Testit scanner-moduulille"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Lisää src polku
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.scanner.core import run_axe, format_results
from utils import ScannerError


@pytest.mark.asyncio
async def test_run_axe_valid_url():
    """Testi onnistuneelle skannaukselle"""
    mock_result = {
        "violations": [
            {
                "id": "color-contrast",
                "help": "Elements must have sufficient color contrast",
                "helpUrl": "https://example.com/help",
                "nodes": [
                    {
                        "html": "<div>Test</div>",
                        "any": [{"message": "Color contrast issue"}],
                    }
                ],
            }
        ],
        "passes": [],
        "incomplete": [],
        "inapplicable": [],
    }

    with patch("src.scanner.core.async_playwright") as mock_playwright:
        # Mock playwright objektit
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_page.evaluate.return_value = mock_result
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context

        mock_p = AsyncMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__aenter__.return_value = mock_p

        result = await run_axe("https://example.com")

        assert result == mock_result
        assert len(result["violations"]) == 1
        assert result["violations"][0]["id"] == "color-contrast"

        # Varmista että tarvittavat metodit kutsuttiin
        mock_page.goto.assert_called_once_with(
            "https://example.com", wait_until="domcontentloaded"
        )
        mock_page.add_script_tag.assert_called_once()
        mock_page.wait_for_function.assert_called_once_with(
            "typeof axe !== 'undefined'"
        )


@pytest.mark.asyncio
async def test_run_axe_invalid_url():
    """Testi virheelliselle URL:lle"""
    with pytest.raises(ScannerError, match="Virheellinen URL"):
        await run_axe("not-a-valid-url")


@pytest.mark.asyncio
async def test_run_axe_empty_url():
    """Testi tyhjälle URL:lle"""
    with pytest.raises(ScannerError, match="Virheellinen URL"):
        await run_axe("")


@pytest.mark.asyncio
async def test_run_axe_browser_error():
    """Testi selaimen virhetilanteelle"""
    with patch("src.scanner.core.async_playwright") as mock_playwright:
        mock_playwright.return_value.__aenter__.side_effect = Exception(
            "Browser launch failed"
        )

        with pytest.raises(ScannerError, match="Skannaus epäonnistui"):
            await run_axe("https://example.com")


@pytest.mark.asyncio
async def test_run_axe_navigation_error():
    """Testi navigointivirheelle"""
    with patch("src.scanner.core.async_playwright") as mock_playwright:
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Mock navigointivirheen
        mock_page.goto.side_effect = Exception("Navigation failed")
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context

        mock_p = AsyncMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__aenter__.return_value = mock_p

        with pytest.raises(ScannerError, match="Skannaus epäonnistui"):
            await run_axe("https://example.com")


@pytest.mark.asyncio
async def test_run_axe_timeout():
    """Testi timeout-tilanteelle"""
    with patch("src.scanner.core.async_playwright") as mock_playwright:
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Mock timeout
        mock_page.set_default_timeout.assert_called = True
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context

        mock_p = AsyncMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__aenter__.return_value = mock_p

        mock_page.evaluate.return_value = {
            "violations": [],
            "passes": [],
            "incomplete": [],
            "inapplicable": [],
        }

        result = await run_axe("https://example.com", timeout=5000)

        # Varmista että timeout asetettiin
        mock_page.set_default_timeout.assert_called_with(5000)


def test_format_results_with_violations(capsys):
    """Testi tulosten formatoinnille kun on rikkomuksia"""
    results = {
        "violations": [
            {
                "help": "Elements must have sufficient color contrast",
                "id": "color-contrast",
                "helpUrl": "https://example.com/help",
                "nodes": [
                    {
                        "html": "<div>Test content</div>",
                        "any": [
                            {"message": "Element has insufficient color contrast"},
                            {"message": "Background color not readable"},
                        ],
                    }
                ],
            }
        ]
    }

    format_results(results, "https://example.com")

    captured = capsys.readouterr()
    assert "==> https://example.com" in captured.out
    assert "❌ Elements must have sufficient color contrast" in captured.out
    assert "color-contrast" in captured.out
    assert "https://example.com/help" in captured.out
    assert "<div>Test content</div>" in captured.out
    assert "Element has insufficient color contrast" in captured.out


def test_format_results_no_violations(capsys):
    """Testi tulosten formatoinnille kun ei ole rikkomuksia"""
    results = {"violations": []}

    format_results(results, "https://example.com")

    captured = capsys.readouterr()
    assert "==> https://example.com" in captured.out
    # Ei pitäisi olla virheilmoituksia
    assert "❌" not in captured.out
