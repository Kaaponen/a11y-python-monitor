"""Testit analysis-moduulille"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Lisää src polku
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.analysis.alt_analysis import (
    get_image_base64,
    get_alt_suggestion,
    evaluate_alt,
    run_alt_analysis,
    save_analysis_to_json
)

class TestImageProcessing:
    """Testit kuvan käsittelylle"""
    
    def test_get_image_base64_success(self):
        """Testi onnistuneelle kuvan lataukselle"""
        mock_image_data = b"fake_image_data"
        expected_b64 = base64.b64encode(mock_image_data).decode("utf-8")
        
        with patch('src.analysis.alt_analysis.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = mock_image_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = get_image_base64("https://example.com/image.jpg")
            
            assert result == expected_b64
            mock_get.assert_called_once_with("https://example.com/image.jpg")
            mock_response.raise_for_status.assert_called_once()

    def test_get_image_base64_http_error(self):
        """Testi HTTP-virhetilanteelle"""
        with patch('src.analysis.alt_analysis.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("HTTP 404")
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception, match="HTTP 404"):
                get_image_base64("https://example.com/nonexistent.jpg")

class TestOpenAIIntegration:
    """Testit OpenAI integraatiolle"""
    
    def test_get_alt_suggestion_success(self):
        """Testi onnistuneelle alt-tekstin ehdotukselle"""
        mock_suggestion = "A red car parked in front of a building"
        
        with patch('src.analysis.alt_analysis.get_image_base64') as mock_get_b64:
            mock_get_b64.return_value = "fake_base64_data"
            
            with patch('src.analysis.alt_analysis.OpenAI') as mock_openai:
                # Mock OpenAI client
                mock_client = Mock()
                mock_response = Mock()
                mock_choice = Mock()
                mock_message = Mock()
                
                mock_message.content = mock_suggestion
                mock_choice.message = mock_message
                mock_response.choices = [mock_choice]
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                result = get_alt_suggestion("https://example.com/image.jpg", "fake_api_key")
                
                assert result == mock_suggestion
                mock_client.chat.completions.create.assert_called_once()

    def test_get_alt_suggestion_openai_error(self):
        """Testi OpenAI API virhetilanteelle"""
        with patch('src.analysis.alt_analysis.get_image_base64') as mock_get_b64:
            mock_get_b64.return_value = "fake_base64_data"
            
            with patch('src.analysis.alt_analysis.OpenAI') as mock_openai:
                mock_client = Mock()
                mock_client.chat.completions.create.side_effect = Exception("OpenAI API Error")
                mock_openai.return_value = mock_client
                
                with pytest.raises(Exception, match="OpenAI API Error"):
                    get_alt_suggestion("https://example.com/image.jpg", "fake_api_key")

class TestAltTextEvaluation:
    """Testit alt-tekstin arvioinnille"""
    
    def test_evaluate_alt_missing(self):
        """Testi puuttuvalle alt-tekstille"""
        result = evaluate_alt("", "A red car")
        assert result == "❌ puuttuu"
        
        result = evaluate_alt(None, "A red car")
        assert result == "❌ puuttuu"

    def test_evaluate_alt_perfect_match(self):
        """Testi täydelliselle osumalle"""
        existing_alt = "A red car"
        suggested_alt = "A red car"
        
        result = evaluate_alt(existing_alt, suggested_alt)
        assert result == "✅ ok"

    def test_evaluate_alt_case_insensitive_match(self):
        """Testi case-insensitive osumalle"""
        existing_alt = "A RED CAR"
        suggested_alt = "a red car"
        
        result = evaluate_alt(existing_alt, suggested_alt)
        assert result == "✅ ok"

    def test_evaluate_alt_whitespace_match(self):
        """Testi whitespace-osumalle"""
        existing_alt = "  A red car  "
        suggested_alt = "A red car"
        
        result = evaluate_alt(existing_alt, suggested_alt)
        assert result == "✅ ok"

    def test_evaluate_alt_inaccurate(self):
        """Testi epätarkalle alt-tekstille"""
        existing_alt = "A car"
        suggested_alt = "A red car in front of a building"
        
        result = evaluate_alt(existing_alt, suggested_alt)
        assert result == "⚠️ epätarkka"

class TestAnalysisWorkflow:
    """Testit analyysien työnkululle"""
    
    def test_run_alt_analysis_success(self):
        """Testi onnistuneelle alt-analyysin ajolle"""
        images = [
            {"src": "https://example.com/image1.jpg", "alt": "existing alt"},
            {"src": "https://example.com/image2.jpg", "alt": ""}
        ]
        
        with patch('src.analysis.alt_analysis.get_alt_suggestion') as mock_suggestion:
            mock_suggestion.side_effect = ["suggested alt 1", "suggested alt 2"]
            
            with patch('src.analysis.alt_analysis.evaluate_alt') as mock_evaluate:
                mock_evaluate.side_effect = ["⚠️ epätarkka", "❌ puuttuu"]
                
                results = run_alt_analysis(images, "fake_api_key")
                
                assert len(results) == 2
                assert results[0]["src"] == "https://example.com/image1.jpg"
                assert results[0]["alt_current"] == "existing alt"
                assert results[0]["alt_suggested"] == "suggested alt 1"
                assert results[0]["evaluation"] == "⚠️ epätarkka"

    def test_run_alt_analysis_with_errors(self):
        """Testi alt-analyysin ajolle virheiden kanssa"""
        images = [
            {"src": "https://example.com/broken-image.jpg", "alt": "some alt"},
            {"src": "https://example.com/good-image.jpg", "alt": "good alt"}
        ]
        
        def mock_suggestion_side_effect(url, api_key):
            if "broken-image" in url:
                raise Exception("Image processing failed")
            return "good suggestion"
        
        with patch('src.analysis.alt_analysis.get_alt_suggestion', side_effect=mock_suggestion_side_effect):
            results = run_alt_analysis(images, "fake_api_key")
            
            assert len(results) == 2
            # Ensimmäinen kuva epäonnistui
            assert "Virhe:" in results[0]["alt_suggested"]
            assert results[0]["evaluation"] == "⚠️ ei analysoitu"
            
            # Toinen kuva onnistui
            assert results[1]["alt_suggested"] == "good suggestion"

    def test_run_alt_analysis_empty_list(self):
        """Testi tyhjälle kuvalistalle"""
        results = run_alt_analysis([], "fake_api_key")
        assert results == []

class TestJSONSaving:
    """Testit JSON tallennukselle"""
    
    def test_save_analysis_to_json_default_path(self):
        """Testi JSON tallennukselle oletuspolussa"""
        results = [
            {
                "src": "https://example.com/image.jpg",
                "alt_current": "old alt",
                "alt_suggested": "new alt",
                "evaluation": "⚠️ epätarkka"
            }
        ]
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('src.analysis.alt_analysis.json.dump') as mock_json_dump:
                save_analysis_to_json(results)
                
                mock_open.assert_called_once_with("alt_analysis.json", "w", encoding="utf-8")
                mock_json_dump.assert_called_once_with(
                    results, 
                    mock_open.return_value.__enter__.return_value, 
                    indent=2, 
                    ensure_ascii=False
                )

    def test_save_analysis_to_json_custom_path(self):
        """Testi JSON tallennukselle mukautetulla polulla"""
        results = []
        custom_path = "custom_analysis.json"
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('src.analysis.alt_analysis.json.dump') as mock_json_dump:
                save_analysis_to_json(results, custom_path)
                
                mock_open.assert_called_once_with(custom_path, "w", encoding="utf-8")

class TestImageValidation:
    """Testit kuvan validoinnille"""
    
    def test_run_alt_analysis_missing_src(self):
        """Testi kuvalle ilman src-kenttää"""
        images = [{"alt": "some alt"}]  # Puuttuu src
        
        # Tämä pitäisi aiheuttaa KeyError tai vastaavan
        with pytest.raises(KeyError):
            run_alt_analysis(images, "fake_api_key")

    def test_run_alt_analysis_missing_alt(self):
        """Testi kuvalle ilman alt-kenttää"""
        images = [{"src": "https://example.com/image.jpg"}]  # Puuttuu alt
        
        with patch('src.analysis.alt_analysis.get_alt_suggestion') as mock_suggestion:
            mock_suggestion.return_value = "suggested alt"
            
            results = run_alt_analysis(images, "fake_api_key")
            
            # Pitäisi käsitellä puuttuva alt-kenttä
            assert results[0]["alt_current"] == ""
            assert results[0]["evaluation"] == "❌ puuttuu"