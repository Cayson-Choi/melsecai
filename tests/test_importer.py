"""Tests for import_to_gxworks2 tool and automation module."""

import os
import tempfile

import pytest

from melsec_ladder_mcp.tools.importer import import_to_gxworks2
from melsec_ladder_mcp.automation.config import load_config
from melsec_ladder_mcp.automation.menu_paths import MENU_PATHS, DEFAULT_INSTALL_PATHS


class TestMenuPaths:
    def test_ko_paths_defined(self):
        assert "ko" in MENU_PATHS
        ko = MENU_PATHS["ko"]
        assert "new_project" in ko
        assert "read_text" in ko
        assert "dialog_open_title" in ko

    def test_en_paths_defined(self):
        assert "en" in MENU_PATHS

    def test_ja_paths_defined(self):
        assert "ja" in MENU_PATHS

    def test_all_languages_have_same_keys(self):
        keys = set(MENU_PATHS["ko"].keys())
        assert set(MENU_PATHS["en"].keys()) == keys
        assert set(MENU_PATHS["ja"].keys()) == keys

    def test_default_install_paths(self):
        assert len(DEFAULT_INSTALL_PATHS) >= 2
        assert any("GPPW2" in p for p in DEFAULT_INSTALL_PATHS)


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
        result = import_to_gxworks2(file_path="/nonexistent/file.txt")
        assert result["status"] == "error"
        assert result["error_type"] == "file_not_found"

    def test_auto_open_false(self, tmp_path):
        # Create a temp file
        txt = tmp_path / "test.txt"
        txt.write_text("LD X0\nOUT Y0\nEND")
        result = import_to_gxworks2(
            file_path=str(txt),
            auto_open=False,
        )
        assert result["status"] == "skipped"
        assert "수동" in result["message"]
        assert result["file_path"] == str(txt)

    def test_auto_open_with_missing_gxworks2(self, tmp_path):
        """When GX Works2 exe doesn't exist, should return error with fallback."""
        txt = tmp_path / "test.txt"
        txt.write_text("LD X0\nOUT Y0\nEND")
        result = import_to_gxworks2(
            file_path=str(txt),
            auto_open=True,
            gxworks2_path="/nonexistent/gxw2.exe",
        )
        assert result["status"] == "error"
        assert "fallback" in result
        assert "수동" in result["fallback"]


class TestExporterFileSave:
    def test_export_saves_file(self, practice_11_input):
        """Test that export_gxworks2 saves file to disk."""
        from melsec_ladder_mcp.tools.generator import generate_ladder
        from melsec_ladder_mcp.tools.exporter import export_gxworks2

        ladder = generate_ladder(**practice_11_input)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test_code.txt")
            result = export_gxworks2(ladder, output_path=out_path, output_format="text")

            assert result["file_path"] == out_path
            assert os.path.isfile(out_path)

            with open(out_path, encoding="shift_jis") as f:
                content = f.read()
            assert content.strip().endswith("END")
            assert "LD X0" in content

    def test_export_saves_comments_csv(self, practice_11_input):
        from melsec_ladder_mcp.tools.generator import generate_ladder
        from melsec_ladder_mcp.tools.exporter import export_gxworks2

        ladder = generate_ladder(**practice_11_input)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test_code.txt")
            result = export_gxworks2(ladder, output_path=out_path, output_format="text")

            comments_path = result["comments_file_path"]
            assert comments_path is not None
            assert os.path.isfile(comments_path)
