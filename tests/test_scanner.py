# tests/test_scanner.py
"""Testit scanner-moduulille"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from scanner import run_axe
from utils import ScannerError

@pytest.mark.asyncio
async def test_run_axe_valid_url():
    """Testi onnistuneelle skannaukselle"""
    mock_result = {
        "violations": [],
        "passes": [],
        "incomplete": [],
        "inapplicable": []
    }
    
    with patch('scanner.async_playwright') as mock_playwright:
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
        mock_page.goto.assert_called_once()
        mock_page.add_script_tag.assert_called_once()

@pytest.mark.asyncio
async def test_run_axe_invalid_url():
    """Testi virheelliselle URL:lle"""
    with pytest.raises(ScannerError):
        await run_axe("not-a-valid-url")

@pytest.mark.asyncio
async def test_run_axe_browser_error():
    """Testi selaimen virhetilanteelle"""
    with patch('scanner.async_playwright') as mock_playwright:
        mock_playwright.return_value.__aenter__.side_effect = Exception("Browser error")
        
        with pytest.raises(ScannerError, match="Skannaus epäonnistui"):
            await run_axe("https://example.com")

def test_validate_url():
    """Testi URL-validoinnille"""
    from utils import validate_url
    
    assert validate_url("https://example.com") == True
    assert validate_url("http://example.com") == True
    assert validate_url("ftp://example.com") == False
    assert validate_url("not-a-url") == False
    assert validate_url("") == False