"""Tests for CSV formatter (GX Works2 CSV import/export format)."""

import pytest

from melsec_ladder_mcp.formats.csv_formatter import (
    instructions_to_csv,
    sequence_to_csv,
    _is_timer_or_counter_out,
    _step_size,
)
from melsec_ladder_mcp.models.instructions import (
    Instruction,
    InstructionSequence,
    InstructionType,
)


# --- Helpers ---

def _make_inst(mnemonic: str, device: str | None = None, k_value: int | None = None):
    return Instruction(instruction=InstructionType(mnemonic), device=device, k_value=k_value)


def _decode_csv(data: bytes) -> list[str]:
    """Decode CSV bytes to list of lines."""
    text = data.decode("utf-16-le")
    if text and text[0] == "\ufeff":
        text = text[1:]
    return [line for line in text.strip().split("\r\n") if line]


# --- Unit tests ---

class TestIsTimerOrCounterOut:
    def test_timer_out(self):
        inst = _make_inst("OUT", "T0", 50)
        assert _is_timer_or_counter_out(inst) is True

    def test_counter_out(self):
        inst = _make_inst("OUT", "C0", 10)
        assert _is_timer_or_counter_out(inst) is True

    def test_normal_out(self):
        inst = _make_inst("OUT", "Y0")
        assert _is_timer_or_counter_out(inst) is False

    def test_ld_not_out(self):
        inst = _make_inst("LD", "T0")
        assert _is_timer_or_counter_out(inst) is False

    def test_out_relay(self):
        inst = _make_inst("OUT", "M0")
        assert _is_timer_or_counter_out(inst) is False


class TestStepSize:
    def test_normal_instructions(self):
        for mnemonic in ["LD", "LDI", "AND", "ANI", "OR", "ORI", "MPS", "MRD", "MPP"]:
            assert _step_size(_make_inst(mnemonic, "X0")) == 1

    def test_end(self):
        assert _step_size(_make_inst("END")) == 2

    def test_timer_out(self):
        assert _step_size(_make_inst("OUT", "T0", 50)) == 4

    def test_counter_out(self):
        assert _step_size(_make_inst("OUT", "C0", 10)) == 4

    def test_normal_out(self):
        assert _step_size(_make_inst("OUT", "Y0")) == 1


# --- CSV format tests ---

class TestInstructionsToCsv:
    def test_utf16le_bom(self):
        """CSV must start with UTF-16 LE BOM."""
        data = instructions_to_csv([_make_inst("END")])
        assert data[:2] == b"\xff\xfe"

    def test_header_lines(self):
        """CSV must have 3 header lines."""
        data = instructions_to_csv([_make_inst("END")], program_name="test_prog")
        lines = _decode_csv(data)
        assert lines[0] == '"test_prog"'
        assert '"PLC Information:"' in lines[1]
        assert '"Step No."' in lines[2]
        assert '"Instruction"' in lines[2]

    def test_simple_program(self):
        """Simple LD X0 / OUT Y0 / END."""
        insts = [
            _make_inst("LD", "X0"),
            _make_inst("OUT", "Y0"),
            _make_inst("END"),
        ]
        lines = _decode_csv(instructions_to_csv(insts))
        # Skip 3 header lines
        data_lines = lines[3:]
        assert len(data_lines) == 3
        assert data_lines[0] == '"0"\t""\t"LD"\t"X0"\t""\t""\t""'
        assert data_lines[1] == '"1"\t""\t"OUT"\t"Y0"\t""\t""\t""'
        assert data_lines[2] == '"2"\t""\t"END"\t""\t""\t""\t""'

    def test_timer_two_rows(self):
        """Timer OUT must produce two CSV rows."""
        insts = [
            _make_inst("LD", "M0"),
            _make_inst("OUT", "T0", 50),
            _make_inst("END"),
        ]
        lines = _decode_csv(instructions_to_csv(insts))
        data_lines = lines[3:]
        assert len(data_lines) == 4  # LD + OUT + K-value + END
        assert '"OUT"\t"T0"' in data_lines[1]
        assert '"K50"' in data_lines[2]
        # Timer OUT takes 4 steps, so END should be at step 5
        assert data_lines[3].startswith('"5"')

    def test_step_numbering(self):
        """Step numbers must be correct with timer gap."""
        insts = [
            _make_inst("LD", "X0"),       # step 0
            _make_inst("OR", "M0"),       # step 1
            _make_inst("ANI", "X1"),      # step 2
            _make_inst("OUT", "M0"),      # step 3
            _make_inst("LD", "M0"),       # step 4
            _make_inst("OUT", "T0", 50),  # step 5 (takes 4 steps)
            _make_inst("LD", "T0"),       # step 9
            _make_inst("OUT", "Y20"),     # step 10
            _make_inst("END"),            # step 11
        ]
        lines = _decode_csv(instructions_to_csv(insts))
        data_lines = lines[3:]

        # Check step numbers
        steps = []
        for line in data_lines:
            step_field = line.split("\t")[0].strip('"')
            if step_field:
                steps.append(int(step_field))
        assert steps == [0, 1, 2, 3, 4, 5, 9, 10, 11]

    def test_timer_test_exact_match(self):
        """Generated CSV must match the GX Works2 export for timer_test."""
        insts = [
            _make_inst("LD", "X0"),
            _make_inst("OR", "M0"),
            _make_inst("ANI", "X1"),
            _make_inst("OUT", "M0"),
            _make_inst("LD", "M0"),
            _make_inst("OUT", "T0", 50),
            _make_inst("LD", "T0"),
            _make_inst("OUT", "Y20"),
            _make_inst("END"),
        ]
        data = instructions_to_csv(insts, program_name="timer_test")
        assert len(data) == 838  # exact byte count from GX Works2 export

    def test_stack_ops_no_device(self):
        """ORB, ANB, MPS, MRD, MPP should have no device in CSV."""
        for mnemonic in ["ORB", "ANB", "MPS", "MRD", "MPP"]:
            insts = [_make_inst(mnemonic), _make_inst("END")]
            lines = _decode_csv(instructions_to_csv(insts))
            data_lines = lines[3:]
            assert f'"{mnemonic}"\t""' in data_lines[0]

    def test_custom_cpu_type(self):
        """CPU type should appear in the header."""
        data = instructions_to_csv(
            [_make_inst("END")],
            cpu_type="QCPU (Q mode) Q06UDH",
        )
        lines = _decode_csv(data)
        assert "Q06UDH" in lines[1]

    def test_counter_two_rows(self):
        """Counter OUT must also produce two CSV rows."""
        insts = [
            _make_inst("LD", "X0"),
            _make_inst("OUT", "C0", 10),
            _make_inst("END"),
        ]
        lines = _decode_csv(instructions_to_csv(insts))
        data_lines = lines[3:]
        assert len(data_lines) == 4  # LD + OUT + K-value + END
        assert '"OUT"\t"C0"' in data_lines[1]
        assert '"K10"' in data_lines[2]


class TestSequenceToCsv:
    def test_sequence_wrapper(self):
        """sequence_to_csv should delegate to instructions_to_csv."""
        seq = InstructionSequence(instructions=[
            _make_inst("LD", "X0"),
            _make_inst("OUT", "Y0"),
            _make_inst("END"),
        ])
        data = sequence_to_csv(seq, program_name="test")
        lines = _decode_csv(data)
        assert lines[0] == '"test"'
        assert len(lines) == 6  # 3 headers + 3 data lines
