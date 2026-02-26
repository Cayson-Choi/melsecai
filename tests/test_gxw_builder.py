"""Tests for GXW binary encoder and builder."""

from __future__ import annotations

import io
import struct

import olefile
import pytest

from melsec_ladder_mcp.formats.gxw_builder import (
    DEVICE_CODES,
    GXWBuilder,
    ILBinaryEncoder,
    _encode_device,
    _encode_k_value,
    _parse_device,
)
from melsec_ladder_mcp.models.instructions import Instruction, InstructionType


# ── Helper ───────────────────────────────────────────────────────────────


def _inst(itype: str, device: str | None = None, k: int | None = None) -> Instruction:
    return Instruction(instruction=InstructionType(itype), device=device, k_value=k)


# ── Device parsing ───────────────────────────────────────────────────────


class TestParseDevice:
    def test_x0(self):
        assert _parse_device("X0") == (0x9C, 0)

    def test_x1(self):
        assert _parse_device("X1") == (0x9C, 1)

    def test_x10_hex(self):
        """X10 is hex address 0x10 = 16."""
        assert _parse_device("X10") == (0x9C, 0x10)

    def test_y20(self):
        assert _parse_device("Y20") == (0x9D, 0x20)

    def test_m0(self):
        assert _parse_device("M0") == (0x90, 0)

    def test_m100_decimal(self):
        """M100 is decimal address 100."""
        assert _parse_device("M100") == (0x90, 100)

    def test_t0(self):
        assert _parse_device("T0") == (0xC2, 0)

    def test_c0(self):
        assert _parse_device("C0") == (0xC5, 0)

    def test_d0(self):
        assert _parse_device("D0") == (0xA8, 0)

    def test_unknown_device_raises(self):
        with pytest.raises(ValueError, match="Unknown device prefix"):
            _parse_device("Z99")


# ── Device encoding ──────────────────────────────────────────────────────


class TestEncodeDevice:
    def test_1byte_address(self):
        assert _encode_device(0x9C, 0) == bytes([0x03, 0x04, 0x9C, 0x00, 0x04])

    def test_1byte_address_x1(self):
        assert _encode_device(0x9C, 1) == bytes([0x03, 0x04, 0x9C, 0x01, 0x04])

    def test_2byte_address(self):
        # M1000 = 0x03E8
        result = _encode_device(0x90, 1000)
        assert result == bytes([0x03, 0x05, 0x90, 0xE8, 0x03, 0x05])


# ── K-value encoding ────────────────────────────────────────────────────


class TestEncodeKValue:
    def test_k50(self):
        assert _encode_k_value(50) == bytes([0x04, 0xE8, 0x32, 0x04])

    def test_k100(self):
        assert _encode_k_value(100) == bytes([0x04, 0xE8, 0x64, 0x04])

    def test_k255(self):
        assert _encode_k_value(255) == bytes([0x04, 0xE8, 0xFF, 0x04])


# ── ILBinaryEncoder single-instruction tests ────────────────────────────


class TestILBinaryEncoderSingle:
    def setup_method(self):
        self.encoder = ILBinaryEncoder()

    def test_ld_x0(self):
        result = self.encoder.encode([_inst("LD", "X0")])
        assert result == bytes([0x03, 0x00, 0x03, 0x04, 0x9C, 0x00, 0x04])

    def test_or_m0(self):
        result = self.encoder.encode([_inst("OR", "M0")])
        assert result == bytes([0x03, 0x06, 0x03, 0x04, 0x90, 0x00, 0x04])

    def test_ani_x1(self):
        result = self.encoder.encode([_inst("ANI", "X1")])
        assert result == bytes([0x03, 0x0D, 0x03, 0x04, 0x9C, 0x01, 0x04])

    def test_and_x3(self):
        result = self.encoder.encode([_inst("AND", "X3")])
        assert result == bytes([0x03, 0x0C, 0x03, 0x04, 0x9C, 0x03, 0x04])

    def test_out_m0(self):
        result = self.encoder.encode([_inst("OUT", "M0")])
        assert result == bytes([0x03, 0x20, 0x03, 0x04, 0x90, 0x00, 0x04])

    def test_out_y20(self):
        result = self.encoder.encode([_inst("OUT", "Y20")])
        assert result == bytes([0x03, 0x20, 0x03, 0x04, 0x9D, 0x20, 0x04])

    def test_out_timer_t0_k50(self):
        result = self.encoder.encode([_inst("OUT", "T0", 50)])
        expected = (
            bytes([0x04, 0x21, 0x04, 0x04])  # OUT T header
            + bytes([0x04, 0xC2, 0x00, 0x04])  # T0
            + bytes([0x04, 0xE8, 0x32, 0x04])  # K50
        )
        assert result == expected

    def test_end(self):
        result = self.encoder.encode([_inst("END")])
        assert result == bytes([0x04, 0x34, 0x02, 0x04])


# ── ILBinaryEncoder: verified programs from GXW analysis ─────────────────


class TestILBinaryEncoderPrograms:
    """Test complete programs against known-good binary from GXW files."""

    def setup_method(self):
        self.encoder = ILBinaryEncoder()

    def test_selfhold_program(self):
        """selfhold.gxw: LD X1 / OR Y20 / AND X3 / OUT Y20 / END"""
        instructions = [
            _inst("LD", "X1"),
            _inst("OR", "Y20"),
            _inst("AND", "X3"),
            _inst("OUT", "Y20"),
            _inst("END"),
        ]
        result = self.encoder.encode(instructions)
        expected = bytes([
            0x03, 0x00, 0x03, 0x04, 0x9C, 0x01, 0x04,  # LD X1
            0x03, 0x06, 0x03, 0x04, 0x9D, 0x20, 0x04,  # OR Y20
            0x03, 0x0C, 0x03, 0x04, 0x9C, 0x03, 0x04,  # AND X3
            0x03, 0x20, 0x03, 0x04, 0x9D, 0x20, 0x04,  # OUT Y20
            0x04, 0x34, 0x02, 0x04,                      # END
        ])
        assert result == expected

    def test_timer_test_program(self):
        """timer_test.gxw: self-hold + timer + output"""
        instructions = [
            _inst("LD", "X0"),
            _inst("OR", "M0"),
            _inst("ANI", "X1"),
            _inst("OUT", "M0"),
            _inst("LD", "M0"),
            _inst("OUT", "T0", 50),
            _inst("LD", "T0"),
            _inst("OUT", "Y20"),
            _inst("END"),
        ]
        result = self.encoder.encode(instructions)
        expected = bytes([
            0x03, 0x00, 0x03, 0x04, 0x9C, 0x00, 0x04,  # LD X0
            0x03, 0x06, 0x03, 0x04, 0x90, 0x00, 0x04,  # OR M0
            0x03, 0x0D, 0x03, 0x04, 0x9C, 0x01, 0x04,  # ANI X1
            0x03, 0x20, 0x03, 0x04, 0x90, 0x00, 0x04,  # OUT M0
            0x03, 0x00, 0x03, 0x04, 0x90, 0x00, 0x04,  # LD M0
            0x04, 0x21, 0x04, 0x04,                      # OUT T header
            0x04, 0xC2, 0x00, 0x04,                      # T0
            0x04, 0xE8, 0x32, 0x04,                      # K50
            0x03, 0x00, 0x03, 0x04, 0xC2, 0x00, 0x04,  # LD T0
            0x03, 0x20, 0x03, 0x04, 0x9D, 0x20, 0x04,  # OUT Y20
            0x04, 0x34, 0x02, 0x04,                      # END
        ])
        assert result == expected
        assert len(result) == 65  # matches timer_test.gxw block_size


# ── GXWBuilder integration tests ────────────────────────────────────────


class TestGXWBuilder:
    """Test GXW file generation and OLE2 structure."""

    def _build_timer_test(self) -> bytes:
        """Build a .gxw from the timer_test program."""
        instructions = [
            _inst("LD", "X0"),
            _inst("OR", "M0"),
            _inst("ANI", "X1"),
            _inst("OUT", "M0"),
            _inst("LD", "M0"),
            _inst("OUT", "T0", 50),
            _inst("LD", "T0"),
            _inst("OUT", "Y20"),
            _inst("END"),
        ]
        builder = GXWBuilder()
        return builder.build(instructions, project_name="timer_test")

    def test_produces_valid_ole2(self):
        """Output must be a valid OLE2 compound file."""
        data = self._build_timer_test()
        assert data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        ole = olefile.OleFileIO(io.BytesIO(data))
        ole.close()

    def test_contains_hdb_stream(self):
        data = self._build_timer_test()
        ole = olefile.OleFileIO(io.BytesIO(data))
        assert ole.exists("_hdb")
        ole.close()

    def test_hdb_is_valid_ole2(self):
        data = self._build_timer_test()
        ole = olefile.OleFileIO(io.BytesIO(data))
        hdb = ole.openstream("_hdb").read()
        ole.close()
        inner = olefile.OleFileIO(io.BytesIO(hdb))
        assert inner.exists("12")
        assert inner.exists("16")
        inner.close()

    def test_stream12_contains_program(self):
        """Stream 12 must contain the encoded program bytes."""
        data = self._build_timer_test()
        ole = olefile.OleFileIO(io.BytesIO(data))
        hdb = ole.openstream("_hdb").read()
        ole.close()
        inner = olefile.OleFileIO(io.BytesIO(hdb))
        s12 = inner.openstream("12").read()
        inner.close()

        # Header is 54 bytes, then 4-byte block_size, then program
        block_size = struct.unpack_from("<I", s12, 54)[0]
        assert block_size == 65  # timer_test program is 65 bytes

        program = s12[58 : 58 + block_size]

        # Verify LD X0 at start
        assert program[:7] == bytes([0x03, 0x00, 0x03, 0x04, 0x9C, 0x00, 0x04])
        # Verify END at end
        assert program[-4:] == bytes([0x04, 0x34, 0x02, 0x04])

    def test_stream12_has_main_trailer(self):
        """Stream 12 must end with MAIN trailer."""
        data = self._build_timer_test()
        ole = olefile.OleFileIO(io.BytesIO(data))
        hdb = ole.openstream("_hdb").read()
        ole.close()
        inner = olefile.OleFileIO(io.BytesIO(hdb))
        s12 = inner.openstream("12").read()
        inner.close()

        # Find "MAIN" in UTF-16LE
        main_bytes = "MAIN".encode("utf-16-le")
        assert main_bytes in s12

    def test_stream16_contains_program(self):
        """Stream 16 must contain the encoded program bytes."""
        data = self._build_timer_test()
        ole = olefile.OleFileIO(io.BytesIO(data))
        hdb = ole.openstream("_hdb").read()
        ole.close()
        inner = olefile.OleFileIO(io.BytesIO(hdb))
        s16 = inner.openstream("16").read()
        inner.close()

        # Header is 79 bytes, then program starts
        program_start = 79
        # Verify LD X0 at start of program
        assert s16[program_start : program_start + 7] == bytes(
            [0x03, 0x00, 0x03, 0x04, 0x9C, 0x00, 0x04]
        )

    def test_stream16_size_fields(self):
        """Stream 16 header size fields must be program_size + 20."""
        data = self._build_timer_test()
        ole = olefile.OleFileIO(io.BytesIO(data))
        hdb = ole.openstream("_hdb").read()
        ole.close()
        inner = olefile.OleFileIO(io.BytesIO(hdb))
        s16 = inner.openstream("16").read()
        inner.close()

        size_a = struct.unpack_from("<I", s16, 0x37)[0]
        size_b = struct.unpack_from("<I", s16, 0x3B)[0]
        assert size_a == 65 + 20  # program_size + 20
        assert size_b == 65 + 20

    def test_projectlist_has_name(self):
        """projectlist.xml must contain the project name."""
        data = self._build_timer_test()
        ole = olefile.OleFileIO(io.BytesIO(data))
        xml = ole.openstream("projectlist.xml").read().decode("utf-8", errors="replace")
        ole.close()
        assert "<szName>timer_test</szName>" in xml

    def test_practice_11_program(self):
        """Build Practice 11 IL → .gxw and verify structure."""
        instructions = [
            _inst("LD", "X0"),
            _inst("OR", "M0"),
            _inst("ANI", "X1"),
            _inst("OUT", "M0"),
            _inst("LD", "M0"),
            _inst("OUT", "Y0"),
            _inst("LD", "M0"),
            _inst("OUT", "T0", 50),
            _inst("LD", "T0"),
            _inst("OUT", "Y1"),
            _inst("LD", "M0"),
            _inst("OUT", "T1", 100),
            _inst("LD", "T1"),
            _inst("OUT", "Y2"),
            _inst("END"),
        ]
        builder = GXWBuilder()
        data = builder.build(instructions, project_name="practice_11")

        # Verify valid OLE2
        ole = olefile.OleFileIO(io.BytesIO(data))
        hdb = ole.openstream("_hdb").read()
        ole.close()

        inner = olefile.OleFileIO(io.BytesIO(hdb))
        s12 = inner.openstream("12").read()
        inner.close()

        # Extract block_size and program bytes
        block_size = struct.unpack_from("<I", s12, 54)[0]
        program = s12[58 : 58 + block_size]

        # Verify END is present
        assert program[-4:] == bytes([0x04, 0x34, 0x02, 0x04])

        # Count instruction tokens in the program
        encoder = ILBinaryEncoder()
        expected_bytes = encoder.encode(instructions)
        assert program == expected_bytes

    def test_all_template_streams_preserved(self):
        """All streams from the template must be present in the output."""
        data = self._build_timer_test()
        ole = olefile.OleFileIO(io.BytesIO(data))
        stream_names = {"/".join(e) for e in ole.listdir()}
        ole.close()

        # Must have these essential streams
        assert "_hdb" in stream_names
        assert "projectlist.xml" in stream_names
