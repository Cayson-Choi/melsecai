"""Tests for Counter (C) device support."""

import pytest

from melsec_ladder_mcp.core.compiler import LadderCompiler
from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.instructions import InstructionValidator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.formats.csv_formatter import instructions_to_csv
from melsec_ladder_mcp.models.devices import CounterConfig, DeviceType
from melsec_ladder_mcp.models.instructions import Instruction, InstructionType
from melsec_ladder_mcp.models.ladder import (
    ContactElement,
    ContactMode,
    CounterElement,
    LadderProgram,
    Rung,
    SeriesConnection,
    SetResetElement,
)


class TestCounterConfig:
    def test_counter_config_creation(self):
        config = CounterConfig(k_value=10, comment="10회 카운트")
        assert config.k_value == 10
        assert config.comment == "10회 카운트"

    def test_counter_config_default_comment(self):
        config = CounterConfig(k_value=5)
        assert config.k_value == 5
        assert config.comment == ""

    def test_counter_config_k_value_must_be_positive(self):
        with pytest.raises(Exception):
            CounterConfig(k_value=0)


class TestDeviceAllocatorCounter:
    def test_allocate_counter(self):
        alloc = DeviceAllocator()
        result = alloc.allocate_counter("CNT1", count=10, comment="10회 카운트")
        assert result.address.device_type == DeviceType.C
        assert result.address.address == 0
        assert result.counter_config is not None
        assert result.counter_config.k_value == 10
        assert result.logical_name == "CNT1"

    def test_allocate_multiple_counters(self):
        alloc = DeviceAllocator()
        c0 = alloc.allocate_counter("CNT1", count=10)
        c1 = alloc.allocate_counter("CNT2", count=20)
        assert c0.address.to_string() == "C0"
        assert c1.address.to_string() == "C1"

    def test_counter_in_device_map(self):
        alloc = DeviceAllocator()
        alloc.allocate_counter("CNT1", count=10)
        dm = alloc.build_device_map()
        assert dm.get_address_string("CNT1") == "C0"


class TestCounterRungBuilder:
    def test_counter_rung(self):
        builder = LadderBuilder()
        rung = builder.rung("카운터").no_contact("X0").counter("C0", 10).build()
        assert len(rung.output_section) == 1
        out = rung.output_section[0]
        assert isinstance(out, CounterElement)
        assert out.device == "C0"
        assert out.k_value == 10

    def test_add_counter_rung_helper(self):
        builder = LadderBuilder()
        builder.add_counter_rung("X0", "C0", 10, comment="10회 카운트")
        program = builder.build()
        assert len(program.rungs) == 1
        rung = program.rungs[0]
        assert isinstance(rung.output_section[0], CounterElement)

    def test_add_counter_reset_rung_helper(self):
        builder = LadderBuilder()
        builder.add_counter_reset_rung("X1", "C0", comment="카운터 리셋")
        program = builder.build()
        rung = program.rungs[0]
        assert isinstance(rung.output_section[0], SetResetElement)
        assert rung.output_section[0].type == "reset"
        assert rung.output_section[0].device == "C0"


class TestCounterCompiler:
    @pytest.fixture
    def compiler(self):
        return LadderCompiler()

    def test_counter_out_compile(self, compiler):
        """LD X0 / OUT C0 K10"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="X0", mode=ContactMode.NO),
                ]),
                output_section=[CounterElement(device="C0", k_value=10)],
            ),
        ])
        seq = compiler.compile(program)
        text = seq.to_text()
        assert "LD X0" in text
        assert "OUT C0 K10" in text

    def test_counter_rst_compile(self, compiler):
        """LD X1 / RST C0"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="X1", mode=ContactMode.NO),
                ]),
                output_section=[SetResetElement(type="reset", device="C0")],
            ),
        ])
        seq = compiler.compile(program)
        text = seq.to_text()
        assert "LD X1" in text
        assert "RST C0" in text

    def test_counter_contact_compile(self, compiler):
        """LD C0 / OUT Y0 — counter contact as input"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="C0", mode=ContactMode.NO),
                ]),
                output_section=[
                    __import__("melsec_ladder_mcp.models.ladder", fromlist=["CoilElement"]).CoilElement(device="Y0"),
                ],
            ),
        ])
        seq = compiler.compile(program)
        text = seq.to_text()
        assert "LD C0" in text
        assert "OUT Y0" in text


class TestCounterValidation:
    def test_counter_out_requires_k_value(self):
        validator = InstructionValidator()
        from melsec_ladder_mcp.models.instructions import InstructionSequence

        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="X0"),
            Instruction(instruction=InstructionType.OUT, device="C0"),  # missing K
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("K value" in e for e in errors)


class TestCounterCSV:
    def test_counter_out_csv_two_rows(self):
        """OUT C0 K10 should produce 2 CSV rows and 4 steps."""
        instructions = [
            Instruction(instruction=InstructionType.LD, device="X0"),
            Instruction(instruction=InstructionType.OUT, device="C0", k_value=10),
            Instruction(instruction=InstructionType.END),
        ]
        csv_bytes = instructions_to_csv(instructions)
        text = csv_bytes.decode("utf-16-le").lstrip("\ufeff")
        lines = text.strip().split("\r\n")
        # Header: 3 lines, LD X0: 1 line, OUT C0: 1 line, K10: 1 line, END: 1 line = 7 total
        assert len(lines) == 7
        # Check step numbers: LD=0, OUT C0=1, END=5 (1+4=5)
        assert '"0"' in lines[3]  # LD X0 at step 0
        assert '"1"' in lines[4]  # OUT C0 at step 1
        assert '"5"' in lines[6]  # END at step 5


class TestCounterE2E:
    def test_counter_program_e2e(self):
        """E2E: X0 counts → C0 K10 → C0 contact → Y0 → X1 resets C0."""
        builder = LadderBuilder()
        builder.add_counter_rung("X0", "C0", 10, comment="X0 카운트")
        builder.add_output_rung("C0", "Y0", comment="카운트 완료 → Y0")
        builder.add_counter_reset_rung("X1", "C0", comment="카운터 리셋")
        program = builder.build()

        compiler = LadderCompiler()
        seq = compiler.compile(program)
        text = seq.to_text()

        expected_lines = [
            "LD X0",
            "OUT C0 K10",
            "LD C0",
            "OUT Y0",
            "LD X1",
            "RST C0",
            "END",
        ]
        assert text == "\n".join(expected_lines)

        # Validate
        validator = InstructionValidator()
        errors = validator.validate(seq)
        assert errors == []
