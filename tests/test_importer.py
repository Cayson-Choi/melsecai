"""Tests for import_to_gxworks2 tool and automation module."""

import os
import tempfile

import pytest

from melsec_ladder_mcp.tools.importer import import_to_gxworks2
from melsec_ladder_mcp.automation.config import load_config


class TestConfig:
    def test_load_defaults(self):
        cfg = load_config("/nonexistent/path.yaml")
        assert cfg["language"] == "ko"
        assert cfg["default_cpu"] == "Q03UDE"
        assert "output_dir" in cfg
        assert "timeouts" in cfg

    def test_load_project_config(self):
        cfg = load_config()
        assert cfg["language"] == "ko"
        assert "GPPW2" in cfg["install_path"] or "GX Works2" in cfg["install_path"]


class TestImporterTool:
    def test_file_not_found(self):
        result = import_to_gxworks2(file_path="/nonexistent/file.csv")
        assert result["status"] == "error"
        assert result["error_type"] == "file_not_found"

    def test_auto_open_false_csv(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("data")
        result = import_to_gxworks2(
            file_path=str(csv),
            auto_open=False,
        )
        assert result["status"] == "skipped"
        assert "CSV" in result["message"]
        assert result["file_path"] == str(csv)

    def test_auto_open_false_gxw(self, tmp_path):
        gxw = tmp_path / "test.gxw"
        gxw.write_text("data")
        result = import_to_gxworks2(
            file_path=str(gxw),
            auto_open=False,
        )
        assert result["status"] == "skipped"
        assert result["file_path"] == str(gxw)

    def test_unsupported_format(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("LD X0\nOUT Y0\nEND")
        result = import_to_gxworks2(file_path=str(txt))
        assert result["status"] == "error"
        assert result["error_type"] == "unsupported_format"


class TestExporterFileSave:
    def test_export_saves_csv_file(self, practice_11_input):
        """Test that export_gxworks2 saves CSV file to disk."""
        from melsec_ladder_mcp.tools.generator import generate_ladder
        from melsec_ladder_mcp.tools.exporter import export_gxworks2

        ladder = generate_ladder(**practice_11_input)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test_code.csv")
            result = export_gxworks2(ladder, output_path=out_path, output_format="csv")

            assert result["file_path"] == out_path
            assert os.path.isfile(out_path)
            assert result["output_format"] == "csv"
