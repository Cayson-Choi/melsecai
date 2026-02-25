"""Tests for LadderCompiler."""

import pytest

from melsec_ladder_mcp.core.compiler import LadderCompiler
from melsec_ladder_mcp.models.instructions import InstructionType
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
def compiler():
    return LadderCompiler()


class TestSeriesCompilation:
    def test_simple_ld_out(self, compiler):
        """LD X0 / OUT Y0"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="X0", mode=ContactMode.NO),
                ]),
                output_section=[CoilElement(device="Y0")],
            ),
        ])
        seq = compiler.compile(program)
        texts = [i.to_text() for i in seq.instructions]
        assert texts == ["LD X0", "OUT Y0", "END"]

    def test_series_and(self, compiler):
        """LD X0 / AND M0 / OUT Y0"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="X0", mode=ContactMode.NO),
                    ContactElement(device="M0", mode=ContactMode.NO),
                ]),
                output_section=[CoilElement(device="Y0")],
            ),
        ])
        seq = compiler.compile(program)
        texts = [i.to_text() for i in seq.instructions]
        assert texts == ["LD X0", "AND M0", "OUT Y0", "END"]

    def test_series_ani(self, compiler):
        """LD X0 / ANI X1 / OUT M0"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="X0", mode=ContactMode.NO),
                    ContactElement(device="X1", mode=ContactMode.NC),
                ]),
                output_section=[CoilElement(device="M0")],
            ),
        ])
        seq = compiler.compile(program)
        texts = [i.to_text() for i in seq.instructions]
        assert texts == ["LD X0", "ANI X1", "OUT M0", "END"]


class TestParallelCompilation:
    def test_self_hold_simple_or(self, compiler):
        """LD X0 / OR M0 → ANI X1 → OUT M0 (simple parallel uses OR)"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ParallelBranch(branches=[
                        SeriesConnection(elements=[
                            ContactElement(device="X0", mode=ContactMode.NO),
                        ]),
                        SeriesConnection(elements=[
                            ContactElement(device="M0", mode=ContactMode.NO),
                        ]),
                    ]),
                    ContactElement(device="X1", mode=ContactMode.NC),
                ]),
                output_section=[CoilElement(device="M0")],
            ),
        ])
        seq = compiler.compile(program)
        texts = [i.to_text() for i in seq.instructions]
        assert texts == ["LD X0", "OR M0", "ANI X1", "OUT M0", "END"]

    def test_complex_parallel_uses_orb(self, compiler):
        """Complex branches (multi-element) use LD+ORB."""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=ParallelBranch(branches=[
                    SeriesConnection(elements=[
                        ContactElement(device="X0", mode=ContactMode.NO),
                        ContactElement(device="X1", mode=ContactMode.NO),
                    ]),
                    SeriesConnection(elements=[
                        ContactElement(device="X2", mode=ContactMode.NO),
                        ContactElement(device="X3", mode=ContactMode.NO),
                    ]),
                ]),
                output_section=[CoilElement(device="Y0")],
            ),
        ])
        seq = compiler.compile(program)
        texts = [i.to_text() for i in seq.instructions]
        assert texts == [
            "LD X0", "AND X1", "LD X2", "AND X3", "ORB", "OUT Y0", "END"
        ]


class TestTimerCompilation:
    def test_timer_output(self, compiler):
        """LD M0 / OUT T0 K50"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="M0", mode=ContactMode.NO),
                ]),
                output_section=[TimerElement(device="T0", k_value=50)],
            ),
        ])
        seq = compiler.compile(program)
        texts = [i.to_text() for i in seq.instructions]
        assert texts == ["LD M0", "OUT T0 K50", "END"]


class TestMultiOutput:
    def test_mps_mpp(self, compiler):
        """MPS / OUT Y0 / MPP / OUT Y1"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="M0", mode=ContactMode.NO),
                ]),
                output_section=[
                    CoilElement(device="Y0"),
                    CoilElement(device="Y1"),
                ],
            ),
        ])
        seq = compiler.compile(program)
        texts = [i.to_text() for i in seq.instructions]
        assert texts == ["LD M0", "MPS", "OUT Y0", "MPP", "OUT Y1", "END"]

    def test_mps_mrd_mpp(self, compiler):
        """Three outputs: MPS / OUT Y0 / MRD / OUT Y1 / MPP / OUT Y2"""
        program = LadderProgram(rungs=[
            Rung(
                number=0,
                input_section=SeriesConnection(elements=[
                    ContactElement(device="M0", mode=ContactMode.NO),
                ]),
                output_section=[
                    CoilElement(device="Y0"),
                    CoilElement(device="Y1"),
                    CoilElement(device="Y2"),
                ],
            ),
        ])
        seq = compiler.compile(program)
        texts = [i.to_text() for i in seq.instructions]
        assert texts == [
            "LD M0", "MPS", "OUT Y0", "MRD", "OUT Y1", "MPP", "OUT Y2", "END"
        ]
