"""Tests for Application Instructions (MOV, +, -, INC, DEC, CMP, BCD, BIN, etc.)."""

import pytest

from melsec_ladder_mcp.core.compiler import LadderCompiler
from melsec_ladder_mcp.core.instructions import InstructionValidator
from melsec_ladder_mcp.core.ladder import LadderBuilder, RungBuilder
from melsec_ladder_mcp.formats.csv_formatter import instructions_to_csv
from melsec_ladder_mcp.models.instructions import (
    Instruction,
    InstructionSequence,
    InstructionType,
)
from melsec_ladder_mcp.models.ladder import (
    ApplicationElement,
    ContactElement,
    ContactMode,
    CounterElement,
    LadderProgram,
    Rung,
    SeriesConnection,
)


class TestApplicationElement:
    def test_create_mov(self):
        elem = ApplicationElement(instruction="MOV", operands=["K100", "D0"])
        assert elem.type == "application"
        assert elem.instruction == "MOV"
        assert elem.operands == ["K100", "D0"]

    def test_create_add(self):
        elem = ApplicationElement(instruction="+", operands=["D0", "D1", "D2"])
        assert elem.instruction == "+"
        assert len(elem.operands) == 3

    def test_create_inc(self):
        elem = ApplicationElement(instruction="INC", operands=["D0"])
        assert len(elem.operands) == 1


class TestInstructionToText:
    def test_mov_to_text(self):
        inst = Instruction(instruction=InstructionType.MOV, operands=["K100", "D0"])
        assert inst.to_text() == "MOV K100 D0"

    def test_add_to_text(self):
        inst = Instruction(instruction=InstructionType.ADD, operands=["D0", "D1", "D2"])
        assert inst.to_text() == "+ D0 D1 D2"

    def test_sub_to_text(self):
        inst = Instruction(instruction=InstructionType.SUB, operands=["D0", "K1", "D2"])
        assert inst.to_text() == "- D0 K1 D2"

    def test_inc_to_text(self):
        inst = Instruction(instruction=InstructionType.INC, operands=["D0"])
        assert inst.to_text() == "INC D0"

    def test_dec_to_text(self):
        inst = Instruction(instruction=InstructionType.DEC, operands=["D10"])
        assert inst.to_text() == "DEC D10"

    def test_cmp_to_text(self):
        inst = Instruction(instruction=InstructionType.CMP, operands=["D0", "K100", "M0"])
        assert inst.to_text() == "CMP D0 K100 M0"

    def test_bcd_to_text(self):
        inst = Instruction(instruction=InstructionType.BCD, operands=["D0", "D10"])
        assert inst.to_text() == "BCD D0 D10"

    def test_bin_to_text(self):
        inst = Instruction(instruction=InstructionType.BIN_INST, operands=["D0", "D10"])
        assert inst.to_text() == "BIN D0 D10"

    def test_dmov_to_text(self):
        inst = Instruction(instruction=InstructionType.DMOV, operands=["D0", "D10"])
        assert inst.to_text() == "DMOV D0 D10"

    def test_mul_to_text(self):
        inst = Instruction(instruction=InstructionType.MUL, operands=["D0", "D1", "D2"])
        assert inst.to_text() == "* D0 D1 D2"

    def test_div_to_text(self):
        inst = Instruction(instruction=InstructionType.DIV, operands=["D0", "K2", "D2"])
        assert inst.to_text() == "/ D0 K2 D2"


class TestApplicationCompiler:
    @pytest.fixture
    def compiler(self):
        return LadderCompiler()

    def test_compile_mov(self, compiler):
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="M0", mode=ContactMode.NO),
                ]),
                output_section=[ApplicationElement(instruction="MOV", operands=["K100", "D0"])],
            ),
        ])
        seq = compiler.compile(program)
        text = seq.to_text()
        assert "LD M0" in text
        assert "MOV K100 D0" in text

    def test_compile_add(self, compiler):
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="M0", mode=ContactMode.NO),
                ]),
                output_section=[ApplicationElement(instruction="+", operands=["D0", "D1", "D2"])],
            ),
        ])
        seq = compiler.compile(program)
        text = seq.to_text()
        assert "+ D0 D1 D2" in text

    def test_compile_inc(self, compiler):
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="X0", mode=ContactMode.NO),
                ]),
                output_section=[ApplicationElement(instruction="INC", operands=["D0"])],
            ),
        ])
        seq = compiler.compile(program)
        text = seq.to_text()
        assert "INC D0" in text


class TestApplicationValidation:
    @pytest.fixture
    def validator(self):
        return InstructionValidator()

    def test_mov_valid(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.MOV, operands=["K100", "D0"]),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert errors == []

    def test_mov_wrong_operand_count(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.MOV, operands=["K100"]),  # needs 2
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("2 operands" in e for e in errors)

    def test_add_valid(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.ADD, operands=["D0", "D1", "D2"]),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert errors == []

    def test_add_wrong_operand_count(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.ADD, operands=["D0", "D1"]),  # needs 3
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("3 operands" in e for e in errors)

    def test_inc_valid(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="X0"),
            Instruction(instruction=InstructionType.INC, operands=["D0"]),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert errors == []

    def test_inc_wrong_operand_count(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="X0"),
            Instruction(instruction=InstructionType.INC, operands=["D0", "D1"]),  # needs 1
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("1 operands" in e for e in errors)

    def test_application_no_operands(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.MOV),  # no operands
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("requires operands" in e for e in errors)


class TestApplicationCSV:
    def test_mov_csv_two_rows(self):
        """MOV K100 D0 → 2 CSV rows (instruction+first operand, then second operand)."""
        instructions = [
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.MOV, operands=["K100", "D0"]),
            Instruction(instruction=InstructionType.END),
        ]
        csv_bytes = instructions_to_csv(instructions)
        text = csv_bytes.decode("utf-16-le").lstrip("\ufeff")
        lines = text.strip().split("\r\n")
        # Header: 3, LD=1, MOV=1, D0=1, END=1 → 7 total
        assert len(lines) == 7
        # MOV row
        assert '"MOV"' in lines[4]
        assert '"K100"' in lines[4]
        # D0 continuation row
        assert '"D0"' in lines[5]

    def test_add_csv_three_rows(self):
        """+ D0 D1 D2 → 3 CSV rows."""
        instructions = [
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.ADD, operands=["D0", "D1", "D2"]),
            Instruction(instruction=InstructionType.END),
        ]
        csv_bytes = instructions_to_csv(instructions)
        text = csv_bytes.decode("utf-16-le").lstrip("\ufeff")
        lines = text.strip().split("\r\n")
        # Header: 3, LD=1, +=1, D1=1, D2=1, END=1 → 8 total
        assert len(lines) == 8
        assert '"+"' in lines[4]
        assert '"D0"' in lines[4]
        assert '"D1"' in lines[5]
        assert '"D2"' in lines[6]

    def test_inc_csv_one_row(self):
        """INC D0 → 1 CSV row (instruction + operand)."""
        instructions = [
            Instruction(instruction=InstructionType.LD, device="X0"),
            Instruction(instruction=InstructionType.INC, operands=["D0"]),
            Instruction(instruction=InstructionType.END),
        ]
        csv_bytes = instructions_to_csv(instructions)
        text = csv_bytes.decode("utf-16-le").lstrip("\ufeff")
        lines = text.strip().split("\r\n")
        # Header: 3, LD=1, INC=1, END=1 → 6 total
        assert len(lines) == 6
        assert '"INC"' in lines[4]
        assert '"D0"' in lines[4]

    def test_mov_step_size(self):
        """MOV takes 3 steps (2 operands + 1)."""
        instructions = [
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.MOV, operands=["K100", "D0"]),
            Instruction(instruction=InstructionType.END),
        ]
        csv_bytes = instructions_to_csv(instructions)
        text = csv_bytes.decode("utf-16-le").lstrip("\ufeff")
        lines = text.strip().split("\r\n")
        # LD at step 0, MOV at step 1, END at step 1+3=4
        assert '"4"' in lines[6]  # END at step 4

    def test_add_step_size(self):
        """+ takes 4 steps (3 operands + 1)."""
        instructions = [
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.ADD, operands=["D0", "D1", "D2"]),
            Instruction(instruction=InstructionType.END),
        ]
        csv_bytes = instructions_to_csv(instructions)
        text = csv_bytes.decode("utf-16-le").lstrip("\ufeff")
        lines = text.strip().split("\r\n")
        # LD at step 0, + at step 1, END at step 1+4=5
        assert '"5"' in lines[7]  # END at step 5


class TestRungBuilderApplication:
    def test_rung_builder_application(self):
        builder = LadderBuilder()
        rung = (
            builder.rung("MOV test")
            .no_contact("M0")
            .application("MOV", ["K100", "D0"])
            .build()
        )
        assert len(rung.output_section) == 1
        out = rung.output_section[0]
        assert isinstance(out, ApplicationElement)
        assert out.instruction == "MOV"
        assert out.operands == ["K100", "D0"]

    def test_add_application_rung_helper(self):
        builder = LadderBuilder()
        builder.add_application_rung("M0", "MOV", ["K100", "D0"], comment="데이터 전송")
        program = builder.build()
        rung = program.rungs[0]
        assert isinstance(rung.output_section[0], ApplicationElement)


class TestApplicationE2E:
    def test_mov_program_e2e(self):
        """E2E: LD M0 / MOV K100 D0."""
        builder = LadderBuilder()
        builder.add_application_rung("M0", "MOV", ["K100", "D0"])
        program = builder.build()

        compiler = LadderCompiler()
        seq = compiler.compile(program)
        text = seq.to_text()

        expected_lines = [
            "LD M0",
            "MOV K100 D0",
            "END",
        ]
        assert text == "\n".join(expected_lines)

        validator = InstructionValidator()
        errors = validator.validate(seq)
        assert errors == []

    def test_counter_with_mov_e2e(self):
        """E2E: Counter + MOV combination program."""
        builder = LadderBuilder()
        builder.add_counter_rung("X0", "C0", 10, comment="10회 카운트")
        builder.add_application_rung("C0", "MOV", ["K100", "D0"], comment="카운트 완료시 D0에 100 전송")
        program = builder.build()

        compiler = LadderCompiler()
        seq = compiler.compile(program)
        text = seq.to_text()

        expected_lines = [
            "LD X0",
            "OUT C0 K10",
            "LD C0",
            "MOV K100 D0",
            "END",
        ]
        assert text == "\n".join(expected_lines)

        validator = InstructionValidator()
        errors = validator.validate(seq)
        assert errors == []

    def test_arithmetic_program_e2e(self):
        """E2E: Arithmetic operations program."""
        builder = LadderBuilder()
        builder.add_application_rung("M0", "+", ["D0", "D1", "D2"], comment="D0+D1→D2")
        builder.add_application_rung("M1", "-", ["D10", "D11", "D12"], comment="D10-D11→D12")
        builder.add_application_rung("M2", "INC", ["D20"], comment="D20 증가")
        program = builder.build()

        compiler = LadderCompiler()
        seq = compiler.compile(program)
        text = seq.to_text()

        expected_lines = [
            "LD M0",
            "+ D0 D1 D2",
            "LD M1",
            "- D10 D11 D12",
            "LD M2",
            "INC D20",
            "END",
        ]
        assert text == "\n".join(expected_lines)

        validator = InstructionValidator()
        errors = validator.validate(seq)
        assert errors == []
