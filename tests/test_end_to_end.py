"""End-to-end pipeline tests."""

import json
from pathlib import Path

import pytest

from melsec_ladder_mcp.tools.analyzer import analyze_timing_diagram
from melsec_ladder_mcp.tools.generator import generate_ladder
from melsec_ladder_mcp.tools.exporter import export_gxworks2
from melsec_ladder_mcp.tools.renderer import render_ladder_diagram

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestPractice11Pipeline:
    """Full pipeline test for Practice 11."""

    def test_full_pipeline(self, practice_11_input, practice_11_expected_il):
        # Step 1: Analyze
        analysis = analyze_timing_diagram(**practice_11_input)
        assert analysis["has_sequential"] is True

        # Step 2: Generate ladder
        ladder = generate_ladder(**practice_11_input)
        assert len(ladder["rungs"]) >= 4

        # Step 3: Export to GX Works2
        export = export_gxworks2(ladder)
        program_text = export["program_text"].strip()

        # Step 4: Verify IL output matches expected
        expected_lines = practice_11_expected_il.strip().split("\n")
        actual_lines = program_text.split("\n")

        # Must end with END
        assert actual_lines[-1] == "END"

        # Verify key instructions are present
        assert any("LD X0" in line for line in actual_lines)
        assert any("OUT M0" in line for line in actual_lines)
        assert any("OUT Y0" in line for line in actual_lines)
        assert any("K50" in line for line in actual_lines)  # 5s timer
        assert any("K100" in line for line in actual_lines)  # 10s timer
        assert any("OUT Y1" in line for line in actual_lines)
        assert any("OUT Y2" in line for line in actual_lines)

    def test_exact_il_match(self, practice_11_input, practice_11_expected_il):
        """Test that generated IL exactly matches expected output."""
        ladder = generate_ladder(**practice_11_input)
        export = export_gxworks2(ladder)
        program_text = export["program_text"].strip()
        expected = practice_11_expected_il.strip()

        # Compare line by line for better error messages
        actual_lines = program_text.split("\n")
        expected_lines = expected.split("\n")

        assert actual_lines == expected_lines, (
            f"IL mismatch:\n"
            f"Expected:\n{expected}\n\n"
            f"Actual:\n{program_text}"
        )

    def test_csv_export_format(self, practice_11_input):
        import tempfile, os
        ladder = generate_ladder(**practice_11_input)
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.csv")
            export = export_gxworks2(ladder, output_path=out_path, output_format="csv")
            assert export["output_format"] == "csv"
            assert os.path.isfile(out_path)

    def test_render_text(self, practice_11_input):
        ladder = generate_ladder(**practice_11_input)
        result = render_ladder_diagram(ladder, format="text")
        assert result["rung_count"] >= 4

    def test_no_validation_errors(self, practice_11_input):
        ladder = generate_ladder(**practice_11_input)
        export = export_gxworks2(ladder)
        # Should have no validation warnings (or only minor ones)
        critical_warnings = [
            w for w in export["warnings"]
            if "END" in w or "imbalance" in w
        ]
        assert len(critical_warnings) == 0
