"""Tests for GX Works2 formatter."""

import pytest

from melsec_ladder_mcp.formats.gxworks2 import GXWorks2Formatter
from melsec_ladder_mcp.models.devices import (
    DeviceAddress,
    DeviceAllocation,
    DeviceMap,
    DeviceType,
    TimerConfig,
)
from melsec_ladder_mcp.models.export import ExportOptions
from melsec_ladder_mcp.models.ladder import (
    CoilElement,
    ContactElement,
    ContactMode,
    LadderProgram,
    ParallelBranch,
    Rung,
    SeriesConnection,
    TimerElement,
)


@pytest.fixture
def formatter():
    return GXWorks2Formatter()


def _make_simple_program():
    """LD X0 / OUT Y0"""
    return LadderProgram(rungs=[
        Rung(
            number=0,
            input_section=SeriesConnection(elements=[
                ContactElement(device="X0", mode=ContactMode.NO),
            ]),
            output_section=[CoilElement(device="Y0")],
        ),
    ])


class TestProgramTextFormat:
    def test_simple_program(self, formatter):
        program = _make_simple_program()
        result = formatter.format(program)
        assert result.program_text == "LD X0\nOUT Y0\nEND"

    def test_ends_with_end(self, formatter):
        program = _make_simple_program()
        result = formatter.format(program)
        assert result.program_text.strip().endswith("END")

    def test_no_step_numbers(self, formatter):
        program = _make_simple_program()
        result = formatter.format(program)
        assert "STEP" not in result.program_text

    def test_instruction_count(self, formatter):
        program = _make_simple_program()
        result = formatter.format(program)
        assert result.instruction_count == 3  # LD, OUT, END

    def test_rung_count(self, formatter):
        program = _make_simple_program()
        result = formatter.format(program)
        assert result.rung_count == 1


class TestDeviceComments:
    def test_csv_format(self, formatter):
        program = LadderProgram(
            device_map=DeviceMap(allocations=[
                DeviceAllocation(
                    logical_name="PB1",
                    address=DeviceAddress(device_type=DeviceType.X, address=0),
                    comment="시작 버튼",
                ),
                DeviceAllocation(
                    logical_name="RL",
                    address=DeviceAddress(device_type=DeviceType.Y, address=0),
                    comment="적색 램프",
                ),
            ]),
            rungs=[
                Rung(
                    number=0,
                    input_section=SeriesConnection(elements=[
                        ContactElement(device="X0", mode=ContactMode.NO),
                    ]),
                    output_section=[CoilElement(device="Y0")],
                ),
            ],
        )
        result = formatter.format(program)
        csv = result.device_comments_csv
        assert "Device,Comment" in csv
        assert "X0" in csv
        assert "Y0" in csv

    def test_timer_comment_includes_config(self, formatter):
        program = LadderProgram(
            device_map=DeviceMap(allocations=[
                DeviceAllocation(
                    logical_name="T_DELAY",
                    address=DeviceAddress(device_type=DeviceType.T, address=0),
                    comment="5초 지연",
                    timer_config=TimerConfig(k_value=50, seconds=5.0, comment="GL 점등용"),
                ),
            ]),
            rungs=[
                Rung(
                    number=0,
                    input_section=SeriesConnection(elements=[
                        ContactElement(device="M0", mode=ContactMode.NO),
                    ]),
                    output_section=[TimerElement(device="T0", k_value=50)],
                ),
            ],
        )
        result = formatter.format(program)
        assert "GL 점등용" in result.device_comments_csv
