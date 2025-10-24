"""Testit sitemap-moduulille"""

import pytest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET
import sys
import os

# Lisää src polku
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.scanner.sitemap import get_urls_from_sitemap

def test_get_urls_from_sitemap_simple():
    """Testi yksinkertaiselle sitemap XML:lle"""
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1</loc>
    </url>
    <url>
        <loc>https://example.com/page2</loc>
    </url>
    <url>
        <loc>https://example.com/fi/page3</loc>
    </url>
</urlset>"""
    
    with patch('src.scanner.sitemap.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_xml.encode('utf-8')
        mock_get.return_value = mock_response
        
        urls = get_urls_from_sitemap("https://example.com/sitemap.xml")
        
        assert len(urls) == 3
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
        assert "https://example.com/fi/page3" in urls

def test_get_urls_from_sitemap_with_filter():
    """Testi sitemap XML:lle prefix-filtterillä"""
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/en/page1</loc>
    </url>
    <url>
        <loc>https://example.com/fi/page2</loc>
    </url>
    <url>
        <loc>https://example.com/fi/page3</loc>
    </url>
</urlset>"""
    
    with patch('src.scanner.sitemap.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_xml.encode('utf-8')
        mock_get.return_value = mock_response
        
        urls = get_urls_from_sitemap("https://example.com/sitemap.xml", "https://example.com/fi/")
        
        assert len(urls) == 2
        assert "https://example.com/fi/page2" in urls
        assert "https://example.com/fi/page3" in urls
        assert "https://example.com/en/page1" not in urls

def test_get_urls_from_sitemap_index():
    """Testi sitemap index XML:lle"""
    # Mock sitemap index
    mock_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>https://example.com/sitemap1.xml</loc>
    </sitemap>
    <sitemap>
        <loc>https://example.com/sitemap2.xml</loc>
    </sitemap>
</sitemapindex>"""
    
    # Mock individual sitemaps
    mock_sitemap1_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1</loc>
    </url>
</urlset>"""
    
    mock_sitemap2_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page2</loc>
    </url>
</urlset>"""
    
    def mock_get_side_effect(url):
        mock_response = Mock()
        mock_response.status_code = 200
        
        if url == "https://example.com/sitemap.xml":
            mock_response.content = mock_index_xml.encode('utf-8')
        elif url == "https://example.com/sitemap1.xml":
            mock_response.content = mock_sitemap1_xml.encode('utf-8')
        elif url == "https://example.com/sitemap2.xml":
            mock_response.content = mock_sitemap2_xml.encode('utf-8')
        
        return mock_response
    
    with patch('src.scanner.sitemap.requests.get', side_effect=mock_get_side_effect):
        urls = get_urls_from_sitemap("https://example.com/sitemap.xml")
        
        assert len(urls) == 2
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls

def test_get_urls_from_sitemap_http_error():
    """Testi HTTP-virhetilanteelle"""
    with patch('src.scanner.sitemap.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        urls = get_urls_from_sitemap("https://example.com/sitemap.xml")
        
        assert urls == []

def test_get_urls_from_sitemap_invalid_xml():
    """Testi virheelliselle XML:lle"""
    invalid_xml = "This is not valid XML"
    
    with patch('src.scanner.sitemap.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = invalid_xml.encode('utf-8')
        mock_get.return_value = mock_response
        
        # XML-parsinta epäonnistuu, pitäisi palauttaa tyhjä lista
        with pytest.raises(ET.ParseError):
            get_urls_from_sitemap("https://example.com/sitemap.xml")

def test_get_urls_from_sitemap_empty_xml():
    """Testi tyhjälle XML:lle"""
    empty_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
</urlset>"""
    
    with patch('src.scanner.sitemap.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = empty_xml.encode('utf-8')
        mock_get.return_value = mock_response
        
        urls = get_urls_from_sitemap("https://example.com/sitemap.xml")
        
        assert urls == []

def test_get_urls_from_sitemap_no_namespace():
    """Testi XML:lle ilman namespacea"""
    mock_xml_no_ns = """<?xml version="1.0" encoding="UTF-8"?>
<urlset>
    <url>
        <loc>https://example.com/page1</loc>
    </url>
</urlset>"""
    
    with patch('src.scanner.sitemap.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_xml_no_ns.encode('utf-8')
        mock_get.return_value = mock_response
        
        # Tämä pitäisi palauttaa tyhjä lista koska namespace ei täsmää
        urls = get_urls_from_sitemap("https://example.com/sitemap.xml")
        
        assert urls == []

def test_get_urls_from_sitemap_requests_exception():
    """Testi requests-poikkeukselle"""
    with patch('src.scanner.sitemap.requests.get') as mock_get:
        mock_get.side_effect = Exception("Network error")
        
        # Funktio ei käsittele poikkeuksia, joten se nostaa poikkeuksen
        with pytest.raises(Exception, match="Network error"):
            get_urls_from_sitemap("https://example.com/sitemap.xml")