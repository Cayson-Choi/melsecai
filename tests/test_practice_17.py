"""Tests for practice 17 — 순차 점등, 역순 소등."""

from __future__ import annotations

import pytest

from examples.practice_17 import build_practice_17, get_expected_il
from melsec_ladder_mcp.core.compiler import LadderCompiler
from melsec_ladder_mcp.core.instructions import InstructionValidator
from melsec_ladder_mcp.formats.csv_formatter import instructions_to_csv
from melsec_ladder_mcp.models.instructions import InstructionType


@pytest.fixture
def program():
    builder = build_practice_17()
    return builder.build()


@pytest.fixture
def compiled(program):
    compiler = LadderCompiler()
    return compiler.compile(program)


class TestProgramStructure:
    def test_rung_count(self, program):
        assert len(program.rungs) == 9

    def test_instruction_count(self, compiled):
        # 9 rungs: 4+2+2+4+2+2+3+3+3 = 25 instructions + END = 26
        assert len(compiled.instructions) == 26


class TestILOutput:
    def test_exact_il_match(self, compiled):
        actual = compiled.to_text()
        expected = get_expected_il()
        assert actual == expected

    def test_self_hold_m0(self, compiled):
        """M0 자기유지: LD X1 / OR M0 / ANI T3 / OUT M0."""
        il = compiled.to_text()
        lines = il.split("\n")
        idx = lines.index("LD X1")
        assert lines[idx + 1] == "OR M0"
        assert lines[idx + 2] == "ANI T3"
        assert lines[idx + 3] == "OUT M0"

    def test_stop_sequence_m1(self, compiled):
        """M1 정지 시퀀스: LD X2 / OR M1 / ANI T3 / OUT M1."""
        il = compiled.to_text()
        lines = il.split("\n")
        idx = lines.index("LD X2")
        assert lines[idx + 1] == "OR M1"
        assert lines[idx + 2] == "ANI T3"
        assert lines[idx + 3] == "OUT M1"

    def test_on_delay_timers(self, compiled):
        """ON 딜레이: T0 K30 (M0에서), T1 K20 (T0에서 체인)."""
        il = compiled.to_text()
        assert "OUT T0 K30" in il
        assert "OUT T1 K20" in il

    def test_on_timer_chained(self, compiled):
        """T1은 T0에서 체인: LD T0 / OUT T1 K20."""
        il = compiled.to_text()
        lines = il.split("\n")
        idx = lines.index("OUT T1 K20")
        assert lines[idx - 1] == "LD T0"

    def test_off_delay_timers(self, compiled):
        """OFF 딜레이: T2 K20 (M1에서), T3 K30 (T2에서 체인)."""
        il = compiled.to_text()
        assert "OUT T2 K20" in il
        assert "OUT T3 K30" in il

    def test_off_timer_chained(self, compiled):
        """T3은 T2에서 체인: LD T2 / OUT T3 K30."""
        il = compiled.to_text()
        lines = il.split("\n")
        idx = lines.index("OUT T3 K30")
        assert lines[idx - 1] == "LD T2"

    def test_rl_output(self, compiled):
        """RL: LD M0 / ANI T3 / OUT Y20."""
        il = compiled.to_text()
        lines = il.split("\n")
        idx = lines.index("OUT Y20")
        assert lines[idx - 2] == "LD M0"
        assert lines[idx - 1] == "ANI T3"

    def test_gl_output(self, compiled):
        """GL: LD T0 / ANI T2 / OUT Y21."""
        il = compiled.to_text()
        lines = il.split("\n")
        idx = lines.index("OUT Y21")
        assert lines[idx - 2] == "LD T0"
        assert lines[idx - 1] == "ANI T2"

    def test_yl_output(self, compiled):
        """YL: LD T1 / ANI M1 / OUT Y22."""
        il = compiled.to_text()
        lines = il.split("\n")
        idx = lines.index("OUT Y22")
        assert lines[idx - 2] == "LD T1"
        assert lines[idx - 1] == "ANI M1"

    def test_ends_with_end(self, compiled):
        assert compiled.instructions[-1].instruction == InstructionType.END


class TestValidation:
    def test_no_validation_errors(self, compiled):
        validator = InstructionValidator()
        errors = validator.validate(compiled)
        assert errors == []


class TestCSVExport:
    def test_csv_bom(self, compiled):
        csv_bytes = instructions_to_csv(compiled.instructions)
        assert csv_bytes[:2] == b"\xff\xfe"  # UTF-16 LE BOM

    def test_csv_has_header(self, compiled):
        csv_bytes = instructions_to_csv(compiled.instructions)
        text = csv_bytes.decode("utf-16-le").lstrip("\ufeff")
        lines = text.strip().split("\r\n")
        assert '"MAIN"' in lines[0]
        assert '"Step No."' in lines[2]

    def test_csv_line_count(self, compiled):
        """Header 3 + 26 instructions (4 timer rows produce extra K-value row)."""
        csv_bytes = instructions_to_csv(compiled.instructions)
        text = csv_bytes.decode("utf-16-le").lstrip("\ufeff")
        lines = text.strip().split("\r\n")
        # 3 header + 26 instruction rows + 4 extra timer K-value rows = 33
        assert len(lines) == 33

    def test_csv_ends_with_end(self, compiled):
        csv_bytes = instructions_to_csv(compiled.instructions)
        text = csv_bytes.decode("utf-16-le").lstrip("\ufeff")
        lines = text.strip().split("\r\n")
        assert '"END"' in lines[-1]
