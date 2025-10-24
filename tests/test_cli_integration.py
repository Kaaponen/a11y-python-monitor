"""Integraatiotestit CLI:lle"""

import pytest
import sys
import os
import json
from unittest.mock import patch, Mock, MagicMock
from io import StringIO

# Lisää src polku
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import cli

class TestCLIBasicFunctionality:
    """Testit CLI:n perustoiminnallisuudelle"""
    
    def test_cli_help_message(self):
        """Testi help-viestin näyttämiselle"""
        with patch('sys.argv', ['cli.py', '--help']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                try:
                    cli.main()
                except SystemExit:
                    pass  # argparse kutsuu sys.exit() help:in jälkeen
                
                output = mock_stdout.getvalue()
                assert 'usage:' in output.lower()
                assert 'url' in output.lower()

    def test_cli_version_display(self):
        """Testi version näyttämiselle"""
        with patch('sys.argv', ['cli.py', '--version']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                try:
                    cli.main()
                except SystemExit:
                    pass
                
                output = mock_stdout.getvalue()
                assert '1.0' in output  # Oletetaan versio 1.0

class TestCLIArgumentParsing:
    """Testit argumenttien jäsennykselle"""
    
    def test_parse_single_url(self):
        """Testi yksittäisen URL:n jäsennykselle"""
        test_args = ['cli.py', 'https://example.com']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "issues": 0}
                
                cli.main()
                
                mock_scanner.assert_called_once()
                args, kwargs = mock_scanner.call_args
                assert 'https://example.com' in args[0]

    def test_parse_multiple_urls(self):
        """Testi useiden URL:ien jäsennykselle"""
        test_args = ['cli.py', 'https://example.com', 'https://test.com']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 2, "issues": 0}
                
                cli.main()
                
                mock_scanner.assert_called_once()
                args, kwargs = mock_scanner.call_args
                urls = args[0]
                assert 'https://example.com' in urls
                assert 'https://test.com' in urls

    def test_parse_output_format(self):
        """Testi tulostumuodon jäsennykselle"""
        test_args = ['cli.py', 'https://example.com', '--format', 'json']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "issues": 0}
                
                cli.main()
                
                mock_scanner.assert_called_once()
                args, kwargs = mock_scanner.call_args
                assert kwargs.get('output_format') == 'json'

    def test_parse_output_file(self):
        """Testi tulostustiedoston jäsennykselle"""
        test_args = ['cli.py', 'https://example.com', '--output', 'results.html']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "issues": 0}
                
                cli.main()
                
                mock_scanner.assert_called_once()
                args, kwargs = mock_scanner.call_args
                assert kwargs.get('output_file') == 'results.html'

class TestCLIErrorHandling:
    """Testit CLI:n virheiden käsittelylle"""
    
    def test_invalid_url_handling(self):
        """Testi virheellisen URL:n käsittelylle"""
        test_args = ['cli.py', 'invalid-url']
        
        with patch('sys.argv', test_args):
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit):
                    cli.main()
                
                error_output = mock_stderr.getvalue()
                assert 'error' in error_output.lower() or 'invalid' in error_output.lower()

    def test_scanner_exception_handling(self):
        """Testi skannerin poikkeusten käsittelylle"""
        test_args = ['cli.py', 'https://example.com']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.side_effect = Exception("Scanner failed")
                
                with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                    with pytest.raises(SystemExit):
                        cli.main()
                    
                    error_output = mock_stderr.getvalue()
                    assert 'Scanner failed' in error_output

    def test_file_write_error_handling(self):
        """Testi tiedoston kirjoitusvirheen käsittelylle"""
        test_args = ['cli.py', 'https://example.com', '--output', '/invalid/path/file.html']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "issues": 0}
                
                with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                        with pytest.raises(SystemExit):
                            cli.main()

class TestCLIIntegrationScenarios:
    """Testit CLI:n integraatioskenaarioille"""
    
    def test_full_scan_workflow_html(self):
        """Testi täydelle skannaus-työnkululle HTML-tulosteella"""
        test_args = ['cli.py', 'https://example.com', '--format', 'html', '--output', 'test_report.html']
        
        mock_results = {
            "url": "https://example.com",
            "timestamp": "2024-01-15T10:30:00",
            "violations": [
                {
                    "id": "color-contrast",
                    "impact": "serious",
                    "description": "Elements must have sufficient color contrast"
                }
            ],
            "passes": 15,
            "violations_count": 1
        }
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = mock_results
                
                with patch('builtins.open', create=True) as mock_open:
                    cli.main()
                    
                    # Tarkista että tiedosto avattiin kirjoitusta varten
                    mock_open.assert_called_with('test_report.html', 'w', encoding='utf-8')

    def test_full_scan_workflow_json(self):
        """Testi täydelle skannaus-työnkululle JSON-tulosteella"""
        test_args = ['cli.py', 'https://example.com', '--format', 'json']
        
        mock_results = {
            "url": "https://example.com",
            "violations": [],
            "passes": 20
        }
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = mock_results
                
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    cli.main()
                    
                    output = mock_stdout.getvalue()
                    # Tarkista että tulostus on validia JSONia
                    try:
                        json.loads(output)
                    except json.JSONDecodeError:
                        pytest.fail("Output is not valid JSON")

    def test_multiple_urls_scan(self):
        """Testi useiden URL:ien skannaukselle"""
        test_args = ['cli.py', 'https://example.com', 'https://test.com', '--format', 'json']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"total_pages": 2, "total_issues": 3}
                
                cli.main()
                
                # Tarkista että skanneri kutsuttiin molemmilla URL:eilla
                mock_scanner.assert_called_once()
                args, kwargs = mock_scanner.call_args
                urls = args[0]
                assert len(urls) == 2

class TestCLIConfiguration:
    """Testit CLI:n konfiguraatiolle"""
    
    def test_verbose_mode(self):
        """Testi verbose-tilan käyttöönotolle"""
        test_args = ['cli.py', 'https://example.com', '--verbose']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "issues": 0}
                
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    cli.main()
                    
                    output = mock_stdout.getvalue()
                    # Verbose-tilassa pitäisi olla enemmän tulostusta
                    assert len(output) > 0

    def test_timeout_configuration(self):
        """Testi timeout-konfiguraatiolle"""
        test_args = ['cli.py', 'https://example.com', '--timeout', '60']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "issues": 0}
                
                cli.main()
                
                mock_scanner.assert_called_once()
                args, kwargs = mock_scanner.call_args
                assert kwargs.get('timeout') == 60

    def test_user_agent_configuration(self):
        """Testi user agent -konfiguraatiolle"""
        test_args = ['cli.py', 'https://example.com', '--user-agent', 'TestBot/1.0']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "issues": 0}
                
                cli.main()
                
                mock_scanner.assert_called_once()
                args, kwargs = mock_scanner.call_args
                assert kwargs.get('user_agent') == 'TestBot/1.0'

class TestCLIOutputFormats:
    """Testit CLI:n tulostumuodoille"""
    
    def test_csv_output_format(self):
        """Testi CSV-tulostumuodolle"""
        test_args = ['cli.py', 'https://example.com', '--format', 'csv']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "violations": []}
                
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    cli.main()
                    
                    output = mock_stdout.getvalue()
                    # CSV pitäisi sisältää otsikot
                    assert 'url' in output.lower() or 'page' in output.lower()

    def test_markdown_output_format(self):
        """Testi Markdown-tulostumuodolle"""
        test_args = ['cli.py', 'https://example.com', '--format', 'markdown']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "violations": []}
                
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    cli.main()
                    
                    output = mock_stdout.getvalue()
                    # Markdown pitäisi sisältää otsikkoja
                    assert '#' in output

class TestCLIEdgeCases:
    """Testit CLI:n rajatapauksille"""
    
    def test_no_arguments(self):
        """Testi CLI:lle ilman argumentteja"""
        with patch('sys.argv', ['cli.py']):
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit):
                    cli.main()
                
                error_output = mock_stderr.getvalue()
                assert 'required' in error_output.lower() or 'usage' in error_output.lower()

    def test_conflicting_arguments(self):
        """Testi ristiriitaisille argumenteille"""
        # Esim. sekä --quiet että --verbose
        test_args = ['cli.py', 'https://example.com', '--quiet', '--verbose']
        
        with patch('sys.argv', test_args):
            # Riippuu toteutuksesta, mutta yksi pitäisi voittaa tai antaa virhe
            try:
                with patch('cli.run_scanner') as mock_scanner:
                    mock_scanner.return_value = {"pages": 1, "issues": 0}
                    cli.main()
            except SystemExit:
                pass  # Hyväksytään jos argumentit ovat ristiriitaisia

    def test_unicode_url_handling(self):
        """Testi Unicode-URL:ien käsittelylle"""
        test_args = ['cli.py', 'https://ööö.example.com']
        
        with patch('sys.argv', test_args):
            with patch('cli.run_scanner') as mock_scanner:
                mock_scanner.return_value = {"pages": 1, "issues": 0}
                
                # Pitäisi käsitellä Unicode-URL:it ilman kaatumista
                cli.main()
                
                mock_scanner.assert_called_once()