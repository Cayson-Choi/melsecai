"""Tests for MCP tool functions."""

import pytest

from melsec_ladder_mcp.tools.analyzer import analyze_timing_diagram
from melsec_ladder_mcp.tools.generator import generate_ladder
from melsec_ladder_mcp.tools.exporter import export_gxworks2
from melsec_ladder_mcp.tools.renderer import render_ladder_diagram


class TestAnalyzer:
    def test_practice_11(self, practice_11_input):
        result = analyze_timing_diagram(**practice_11_input)
        assert result["has_self_hold"] is True
        assert result["has_timer"] is True
        assert result["has_sequential"] is True
        assert result["has_full_reset"] is True

    def test_detects_patterns(self, practice_11_input):
        result = analyze_timing_diagram(**practice_11_input)
        pattern_types = [p["pattern_type"] for p in result["detected_patterns"]]
        assert "self_hold" in pattern_types
        assert "timer_delay" in pattern_types
        assert "sequential" in pattern_types

    def test_empty_warnings(self, practice_11_input):
        result = analyze_timing_diagram(**practice_11_input)
        assert len(result["warnings"]) == 0

    def test_missing_inputs_warns(self):
        result = analyze_timing_diagram(
            description="test",
            inputs=[],
            outputs=[{"name": "RL", "type": "lamp"}],
            sequences=[],
        )
        assert any("입력" in w for w in result["warnings"])


class TestGenerator:
    def test_practice_11(self, practice_11_input):
        result = generate_ladder(**practice_11_input)
        assert "rungs" in result
        assert "device_map" in result
        assert len(result["rungs"]) >= 4
        assert "sequential" in result["detected_patterns"]

    def test_device_map_populated(self, practice_11_input):
        result = generate_ladder(**practice_11_input)
        dm = result["device_map"]
        assert len(dm["allocations"]) >= 5  # PB1, PB2, RL, + timers/outputs


class TestExporter:
    def test_practice_11_export(self, practice_11_input):
        ladder = generate_ladder(**practice_11_input)
        result = export_gxworks2(ladder)
        assert "program_text" in result
        text = result["program_text"]
        assert text.strip().endswith("END")
        assert "LD" in text
        assert "OUT" in text

    def test_has_device_comments(self, practice_11_input):
        ladder = generate_ladder(**practice_11_input)
        result = export_gxworks2(ladder)
        assert result["device_comments_csv"] != ""


class TestRenderer:
    def test_text_render(self, practice_11_input):
        ladder = generate_ladder(**practice_11_input)
        result = render_ladder_diagram(ladder, format="text")
        assert result["format"] == "text"
        assert result["rung_count"] >= 4
        assert "Rung" in result["content"] or "|" in result["content"]

    def test_svg_render(self, practice_11_input):
        ladder = generate_ladder(**practice_11_input)
        result = render_ladder_diagram(ladder, format="svg")
        assert result["format"] == "svg"
        assert "<svg" in result["content"]
