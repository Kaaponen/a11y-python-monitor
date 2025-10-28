"""Testit reports-moduulille"""

import pytest
import json
import csv
import os
import tempfile
from unittest.mock import patch, mock_open
from datetime import datetime
import sys

# Lisää src polku
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.reports.reporter import save_report
from src.reports.csv_export import save_csv
from src.reports.json_export import save_json


class TestReporter:
    """Testit reporter.py tiedostolle"""

    def test_save_report_no_violations(self, tmp_path):
        """Testi raportin tallennukselle ilman rikkomuksia"""
        results_by_url = {
            "https://example.com": {
                "violations": [],
                "passes": [],
                "incomplete": [],
                "inapplicable": [],
            }
        }

        with patch("src.reports.reporter.os.makedirs"):
            with patch("src.reports.reporter.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20231024_120000"

                with patch("builtins.open", mock_open()) as mock_file:
                    md_path, html_path = save_report(results_by_url, str(tmp_path))

                    # Tarkista että tiedostot luotiin
                    assert mock_file.call_count == 2  # MD ja HTML

                    # Tarkista MD sisältö
                    md_calls = [
                        call
                        for call in mock_file().write.call_args_list
                        if "Accessibility Report" in str(call)
                    ]
                    assert len(md_calls) > 0

    def test_save_report_with_violations(self, tmp_path):
        """Testi raportin tallennukselle rikkomuksilla"""
        results_by_url = {
            "https://example.com": {
                "violations": [
                    {
                        "id": "color-contrast",
                        "help": "Elements must have sufficient color contrast",
                        "helpUrl": "https://example.com/help",
                        "impact": "serious",
                        "nodes": [
                            {
                                "html": "<div>Test content</div>",
                                "any": [
                                    {
                                        "message": "Element has insufficient color contrast"
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }

        with patch("src.reports.reporter.os.makedirs"):
            with patch("src.reports.reporter.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20231024_120000"

                with patch("builtins.open", mock_open()) as mock_file:
                    md_path, html_path = save_report(results_by_url, str(tmp_path))

                    # Tarkista että kirjoitettiin violations
                    written_content = "".join(
                        [str(call[0][0]) for call in mock_file().write.call_args_list]
                    )
                    assert "color-contrast" in written_content
                    assert (
                        "Elements must have sufficient color contrast"
                        in written_content
                    )


class TestCSVExport:
    """Testit csv_export.py tiedostolle"""

    def test_save_csv_no_violations(self, tmp_path):
        """Testi CSV tallennukselle ilman rikkomuksia"""
        results_by_url = {"https://example.com": {"violations": []}}

        with patch("src.reports.csv_export.os.makedirs"):
            with patch("src.reports.csv_export.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20231024_120000"

                with patch("builtins.open", mock_open()) as mock_file:
                    csv_path = save_csv(results_by_url, str(tmp_path))

                    # Tarkista että CSV writer kutsuttiin
                    assert mock_file.called

                    # Tarkista polku
                    expected_path = os.path.join(
                        str(tmp_path), "report_20231024_120000.csv"
                    )
                    assert csv_path == expected_path

    def test_save_csv_with_violations(self, tmp_path):
        """Testi CSV tallennukselle rikkomuksilla"""
        results_by_url = {
            "https://example.com": {
                "violations": [
                    {
                        "id": "color-contrast",
                        "help": "Elements must have sufficient color contrast",
                        "helpUrl": "https://example.com/help",
                        "impact": "serious",
                        "nodes": [
                            {
                                "html": "<div>Test</div>",
                                "any": [{"message": "Color contrast issue"}],
                            }
                        ],
                    }
                ]
            }
        }

        # Testaa todellinen CSV-kirjoitus
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = save_csv(results_by_url, temp_dir)

            # Lue CSV ja tarkista sisältö
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "https://example.com" in content
                assert "color-contrast" in content
                assert "Elements must have sufficient color contrast" in content


class TestJSONExport:
    """Testit json_export.py tiedostolle"""

    def test_save_json_basic(self, tmp_path):
        """Testi JSON tallennuksen perusominaisuuksille"""
        results_by_url = {
            "https://example.com": {
                "violations": [
                    {"id": "test-rule", "help": "Test rule description", "nodes": []}
                ]
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = save_json(results_by_url, temp_dir)

            # Lue JSON ja tarkista sisältö
            with open(json_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            assert loaded_data == results_by_url
            assert "https://example.com" in loaded_data
            assert (
                loaded_data["https://example.com"]["violations"][0]["id"] == "test-rule"
            )

    def test_save_json_unicode(self, tmp_path):
        """Testi JSON tallennukselle unicode-merkeillä"""
        results_by_url = {
            "https://example.fi": {
                "violations": [
                    {
                        "id": "finnish-content",
                        "help": "Sisältöä ääkköset: äöå",
                        "nodes": [],
                    }
                ]
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = save_json(results_by_url, temp_dir)

            # Lue JSON ja tarkista unicode-merkiet
            with open(json_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "ääkköset" in content
            assert "äöå" in content

    def test_save_json_empty_results(self, tmp_path):
        """Testi JSON tallennukselle tyhjillä tuloksilla"""
        results_by_url = {}

        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = save_json(results_by_url, temp_dir)

            # Lue JSON ja tarkista että se on tyhjä
            with open(json_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            assert loaded_data == {}

    def test_save_json_file_path_generation(self):
        """Testi JSON tiedostopolun generoimiselle"""
        with patch("src.reports.json_export.os.makedirs"):
            with patch("src.reports.json_export.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20231024_120000"

                with patch("builtins.open", mock_open()):
                    json_path = save_json({}, "test_output")

                    expected_path = os.path.join(
                        "test_output", "report_20231024_120000.json"
                    )
                    assert json_path == expected_path
