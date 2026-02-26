"""Tests for car wash chained sequential pattern."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.core.patterns.sequential import SequentialPattern
from melsec_ladder_mcp.models.timing import (
    InputDevice,
    InputMode,
    InputType,
    OutputDevice,
    OutputType,
    SequenceStep,
    TimingDescription,
)
from melsec_ladder_mcp.tools.analyzer import analyze_timing_diagram
from melsec_ladder_mcp.tools.generator import generate_ladder
from melsec_ladder_mcp.tools.exporter import export_gxworks2

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def car_wash_input() -> dict:
    """Car wash input data as raw dict."""
    with open(FIXTURES_DIR / "car_wash_input.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def car_wash_expected_il() -> str:
    """Car wash expected IL text."""
    with open(FIXTURES_DIR / "car_wash_expected_il.txt", encoding="utf-8") as f:
        return f.read().strip()


@pytest.fixture
def car_wash_timing() -> TimingDescription:
    """Car wash as a TimingDescription model."""
    return TimingDescription(
        description="PB1을 누르면 운전등이 켜지고 물 분사가 5초간 동작한다.",
        inputs=[
            InputDevice(name="PB1", type=InputType.PUSH_BUTTON, mode=InputMode.MOMENTARY),
            InputDevice(name="PB2", type=InputType.PUSH_BUTTON, mode=InputMode.MOMENTARY),
        ],
        outputs=[
            OutputDevice(name="RL", type=OutputType.LAMP),
            OutputDevice(name="WP", type=OutputType.PUMP),
            OutputDevice(name="SP", type=OutputType.PUMP),
            OutputDevice(name="TB", type=OutputType.MOTOR),
            OutputDevice(name="SB", type=OutputType.MOTOR),
            OutputDevice(name="UC", type=OutputType.PUMP),
            OutputDevice(name="RP", type=OutputType.PUMP),
            OutputDevice(name="WX", type=OutputType.PUMP),
            OutputDevice(name="BL", type=OutputType.MOTOR),
            OutputDevice(name="BZ", type=OutputType.BUZZER),
            OutputDevice(name="GL", type=OutputType.LAMP),
        ],
        sequences=[
            SequenceStep(trigger="PB1", action="RL ON"),
            SequenceStep(trigger="PB1", action="WP ON"),
            SequenceStep(trigger="WP ON", delay=5, action="SP ON"),
            SequenceStep(trigger="SP ON", delay=3, action="TB ON"),
            SequenceStep(trigger="TB ON", delay=8, action="SB ON"),
            SequenceStep(trigger="SB ON", delay=6, action="UC ON"),
            SequenceStep(trigger="UC ON", delay=5, action="RP ON"),
            SequenceStep(trigger="RP ON", delay=5, action="WX ON"),
            SequenceStep(trigger="WX ON", delay=4, action="BL ON"),
            SequenceStep(trigger="BL ON", delay=10, action="BZ FLICKER"),
            SequenceStep(trigger="BL ON", delay=10, action="GL ON"),
            SequenceStep(trigger="PB2", action="ALL OFF"),
        ],
    )


class TestChainDetection:
    """Tests for chain vs cumulative detection."""

    def test_car_wash_is_chained(self, car_wash_timing):
        assert SequentialPattern._is_chained(car_wash_timing) is True

    def test_practice_11_is_not_chained(self, practice_11_timing):
        assert SequentialPattern._is_chained(practice_11_timing) is False

    def test_single_delayed_not_chained(self):
        timing = TimingDescription(
            description="test",
            inputs=[
                InputDevice(name="PB1"),
                InputDevice(name="PB2"),
            ],
            outputs=[OutputDevice(name="RL"), OutputDevice(name="GL")],
            sequences=[
                SequenceStep(trigger="PB1", action="RL ON"),
                SequenceStep(trigger="RL ON", delay=5, action="GL ON"),
                SequenceStep(trigger="PB2", action="ALL OFF"),
            ],
        )
        assert SequentialPattern._is_chained(timing) is False


class TestChainedGeneration:
    """Tests for chained sequential generation."""

    def test_car_wash_matches_sequential(self, car_wash_timing):
        pattern = SequentialPattern()
        assert pattern.matches(car_wash_timing) is True

    def test_generates_23_rungs(self, car_wash_timing):
        allocator = DeviceAllocator()
        builder = LadderBuilder()
        pattern = SequentialPattern()
        pattern.generate(car_wash_timing, allocator, builder)
        builder.set_device_map(allocator.build_device_map())
        program = builder.build()
        assert len(program.rungs) == 23

    def test_detected_patterns(self, car_wash_timing):
        allocator = DeviceAllocator()
        builder = LadderBuilder()
        pattern = SequentialPattern()
        pattern.generate(car_wash_timing, allocator, builder)
        program = builder.build()
        assert "self_hold" in program.detected_patterns
        assert "timer_delay" in program.detected_patterns
        assert "sequential" in program.detected_patterns

    def test_device_allocation(self, car_wash_timing):
        allocator = DeviceAllocator()
        builder = LadderBuilder()
        pattern = SequentialPattern()
        pattern.generate(car_wash_timing, allocator, builder)

        # Check key device allocations
        assert allocator.get_allocation("PB1") is not None
        assert allocator.get_allocation("PB2") is not None
        assert allocator.get_allocation("M_HOLD") is not None
        assert allocator.get_allocation("M_COMPLETE") is not None
        assert allocator.get_allocation("RL") is not None
        assert allocator.get_allocation("WP") is not None
        assert allocator.get_allocation("BZ") is not None
        assert allocator.get_allocation("GL") is not None

    def test_timer_chain_order(self, car_wash_timing):
        """Verify timers are allocated in correct chain order."""
        allocator = DeviceAllocator()
        builder = LadderBuilder()
        pattern = SequentialPattern()
        pattern.generate(car_wash_timing, allocator, builder)

        # Chain timers: T0 (WP), T1 (SP), T2 (TB), T3 (SB), T4 (UC), T5 (RP), T6 (WX), T7 (BL)
        expected_timers = [
            ("T_WP", "T0", 50),
            ("T_SP", "T1", 30),
            ("T_TB", "T2", 80),
            ("T_SB", "T3", 60),
            ("T_UC", "T4", 50),
            ("T_RP", "T5", 50),
            ("T_WX", "T6", 40),
            ("T_BL", "T7", 100),
        ]
        for logical_name, expected_addr, expected_k in expected_timers:
            alloc = allocator.get_allocation(logical_name)
            assert alloc is not None, f"Timer {logical_name} not allocated"
            assert alloc.address.to_string() == expected_addr
            assert alloc.timer_config.k_value == expected_k

    def test_flicker_timers(self, car_wash_timing):
        """Verify flicker timers are allocated after chain timers."""
        allocator = DeviceAllocator()
        builder = LadderBuilder()
        pattern = SequentialPattern()
        pattern.generate(car_wash_timing, allocator, builder)

        t_on = allocator.get_allocation("T_FLICKER_BZ_ON")
        t_off = allocator.get_allocation("T_FLICKER_BZ_OFF")
        assert t_on is not None
        assert t_off is not None
        assert t_on.address.to_string() == "T8"
        assert t_off.address.to_string() == "T9"
        assert t_on.timer_config.k_value == 5
        assert t_off.timer_config.k_value == 5

    def test_output_addresses_octal(self, car_wash_timing):
        """Verify Y outputs use correct octal addresses."""
        allocator = DeviceAllocator()
        builder = LadderBuilder()
        pattern = SequentialPattern()
        pattern.generate(car_wash_timing, allocator, builder)

        expected_outputs = [
            ("RL", "Y0"),
            ("WP", "Y1"),
            ("SP", "Y2"),
            ("TB", "Y3"),
            ("SB", "Y4"),
            ("UC", "Y5"),
            ("RP", "Y6"),
            ("WX", "Y7"),
            ("BL", "Y10"),   # octal 10 = decimal 8
            ("BZ", "Y11"),   # octal 11 = decimal 9
            ("GL", "Y12"),   # octal 12 = decimal 10
        ]
        for name, expected_addr in expected_outputs:
            alloc = allocator.get_allocation(name)
            assert alloc is not None, f"Output {name} not allocated"
            assert alloc.address.to_string() == expected_addr


class TestCarWashE2E:
    """End-to-end pipeline tests for car wash."""

    def test_full_pipeline(self, car_wash_input):
        analysis = analyze_timing_diagram(**car_wash_input)
        assert analysis["has_sequential"] is True

        ladder = generate_ladder(**car_wash_input)
        assert len(ladder["rungs"]) == 23

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "car_wash.csv")
            export = export_gxworks2(ladder, output_path=out_path, output_format="csv")
            program_text = export["program_text"].strip()
            assert program_text.endswith("END")

    def test_exact_il_match(self, car_wash_input, car_wash_expected_il):
        """Test that generated IL exactly matches expected output."""
        ladder = generate_ladder(**car_wash_input)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "car_wash.csv")
            export = export_gxworks2(ladder, output_path=out_path, output_format="csv")
            program_text = export["program_text"].strip()
            expected = car_wash_expected_il.strip()

            actual_lines = program_text.split("\n")
            expected_lines = expected.split("\n")

            assert actual_lines == expected_lines, (
                f"IL mismatch:\n"
                f"Expected:\n{expected}\n\n"
                f"Actual:\n{program_text}"
            )

    def test_csv_export(self, car_wash_input):
        ladder = generate_ladder(**car_wash_input)
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "car_wash.csv")
            export = export_gxworks2(ladder, output_path=out_path, output_format="csv")
            assert export["output_format"] == "csv"
            assert os.path.isfile(out_path)
            assert export["rung_count"] == 23

    def test_key_il_instructions(self, car_wash_input):
        """Verify key instructions are present in output."""
        ladder = generate_ladder(**car_wash_input)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "car_wash.csv")
            export = export_gxworks2(ladder, output_path=out_path, output_format="csv")
        il = export["program_text"]

        # Self-hold
        assert "LD X0" in il
        assert "OR M0" in il
        assert "ANI X1" in il
        assert "OUT M0" in il

        # Direct output
        assert "OUT Y0" in il

        # Chain timers
        assert "OUT T0 K50" in il   # WP: 5s
        assert "OUT T1 K30" in il   # SP: 3s
        assert "OUT T2 K80" in il   # TB: 8s
        assert "OUT T3 K60" in il   # SB: 6s
        assert "OUT T4 K50" in il   # UC: 5s
        assert "OUT T5 K50" in il   # RP: 5s
        assert "OUT T6 K40" in il   # WX: 4s
        assert "OUT T7 K100" in il  # BL: 10s

        # Gated outputs
        assert "OUT Y1" in il   # WP
        assert "OUT Y10" in il  # BL (octal)

        # Completion
        assert "OUT M1" in il
        assert "OUT T8 K5" in il   # Flicker ON
        assert "OUT T9 K5" in il   # Flicker OFF
        assert "OUT Y11" in il     # BZ
        assert "OUT Y12" in il     # GL


class TestCumulativeRegression:
    """Ensure existing cumulative mode still works (Practice 11)."""

    def test_practice_11_still_works(self, practice_11_input, practice_11_expected_il):
        """Practice 11 must produce identical IL as before."""
        ladder = generate_ladder(**practice_11_input)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "practice_11.csv")
            export = export_gxworks2(ladder, output_path=out_path, output_format="csv")
            program_text = export["program_text"].strip()
            expected = practice_11_expected_il.strip()

            actual_lines = program_text.split("\n")
            expected_lines = expected.split("\n")

            assert actual_lines == expected_lines, (
                f"Practice 11 regression!\n"
                f"Expected:\n{expected}\n\n"
                f"Actual:\n{program_text}"
            )
