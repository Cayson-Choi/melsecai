"""Tests for pattern engine."""

import pytest

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.core.patterns import create_default_registry
from melsec_ladder_mcp.core.patterns.self_hold import SelfHoldPattern
from melsec_ladder_mcp.core.patterns.timer_delay import TimerDelayPattern
from melsec_ladder_mcp.core.patterns.sequential import SequentialPattern
from melsec_ladder_mcp.core.patterns.full_reset import FullResetPattern
from melsec_ladder_mcp.core.patterns.flicker import FlickerPattern


class TestPatternMatching:
    def test_sequential_matches_practice_11(self, practice_11_timing):
        pattern = SequentialPattern()
        assert pattern.matches(practice_11_timing) is True

    def test_self_hold_matches_simple(self, simple_onoff_timing):
        pattern = SelfHoldPattern()
        assert pattern.matches(simple_onoff_timing) is True

    def test_flicker_matches(self, flicker_timing):
        pattern = FlickerPattern()
        assert pattern.matches(flicker_timing) is True

    def test_flicker_not_matches_practice_11(self, practice_11_timing):
        pattern = FlickerPattern()
        assert pattern.matches(practice_11_timing) is False

    def test_timer_delay_matches(self, practice_11_timing):
        pattern = TimerDelayPattern()
        assert pattern.matches(practice_11_timing) is True

    def test_full_reset_matches(self, practice_11_timing):
        pattern = FullResetPattern()
        assert pattern.matches(practice_11_timing) is True


class TestRegistryPriority:
    def test_sequential_has_highest_priority(self):
        registry = create_default_registry()
        patterns = registry.patterns
        # Sequential should be first (highest priority)
        assert patterns[0].name == "sequential"

    def test_best_match_practice_11(self, practice_11_timing):
        registry = create_default_registry()
        best = registry.find_best(practice_11_timing)
        assert best is not None
        assert best.name == "sequential"

    def test_best_match_flicker(self, flicker_timing):
        registry = create_default_registry()
        best = registry.find_best(flicker_timing)
        assert best is not None
        assert best.name == "flicker"


class TestSelfHoldGeneration:
    def test_generates_rungs(self, simple_onoff_timing):
        allocator = DeviceAllocator()
        builder = LadderBuilder()
        pattern = SelfHoldPattern()
        pattern.generate(simple_onoff_timing, allocator, builder)
        program = builder.build()
        assert len(program.rungs) >= 1
        assert "self_hold" in program.detected_patterns


class TestSequentialGeneration:
    def test_generates_practice_11(self, practice_11_timing):
        allocator = DeviceAllocator()
        builder = LadderBuilder()
        pattern = SequentialPattern()
        pattern.generate(practice_11_timing, allocator, builder)

        builder.set_device_map(allocator.build_device_map())
        program = builder.build()

        # Should have: self-hold + RL output + T0 timer + GL output + T1 timer + BZ output
        assert len(program.rungs) >= 4
        assert "self_hold" in program.detected_patterns
        assert "timer_delay" in program.detected_patterns


class TestFlickerGeneration:
    def test_generates_flicker(self, flicker_timing):
        allocator = DeviceAllocator()
        builder = LadderBuilder()
        pattern = FlickerPattern()
        pattern.generate(flicker_timing, allocator, builder)

        builder.set_device_map(allocator.build_device_map())
        program = builder.build()

        # Should have: self-hold + timer1 + timer2 + output
        assert len(program.rungs) >= 3
        assert "flicker" in program.detected_patterns
