"""Tests for Pydantic models."""

import pytest

from melsec_ladder_mcp.models.devices import (
    DeviceAddress,
    DeviceAllocation,
    DeviceMap,
    DeviceType,
    TimerConfig,
)
from melsec_ladder_mcp.models.timing import (
    InputDevice,
    InputType,
    OutputDevice,
    SequenceStep,
    TimingDescription,
)
from melsec_ladder_mcp.models.instructions import (
    Instruction,
    InstructionSequence,
    InstructionType,
)
from melsec_ladder_mcp.models.ladder import (
    ContactElement,
    ContactMode,
    CoilElement,
    Rung,
    SeriesConnection,
    TimerElement,
)


class TestDeviceAddress:
    def test_x_octal_display(self):
        addr = DeviceAddress(device_type=DeviceType.X, address=0)
        assert addr.to_string() == "X0"

    def test_x_octal_8_displays_10(self):
        addr = DeviceAddress(device_type=DeviceType.X, address=8)
        assert addr.to_string() == "X10"

    def test_x_octal_15_displays_17(self):
        addr = DeviceAddress(device_type=DeviceType.X, address=15)
        assert addr.to_string() == "X17"

    def test_x_octal_16_displays_20(self):
        addr = DeviceAddress(device_type=DeviceType.X, address=16)
        assert addr.to_string() == "X20"

    def test_y_octal(self):
        addr = DeviceAddress(device_type=DeviceType.Y, address=9)
        assert addr.to_string() == "Y11"

    def test_m_decimal(self):
        addr = DeviceAddress(device_type=DeviceType.M, address=10)
        assert addr.to_string() == "M10"

    def test_t_decimal(self):
        addr = DeviceAddress(device_type=DeviceType.T, address=5)
        assert addr.to_string() == "T5"

    def test_from_string_x0(self):
        addr = DeviceAddress.from_string("X0")
        assert addr.device_type == DeviceType.X
        assert addr.address == 0

    def test_from_string_x17(self):
        addr = DeviceAddress.from_string("X17")
        assert addr.device_type == DeviceType.X
        assert addr.address == 15  # octal 17 = decimal 15

    def test_from_string_m10(self):
        addr = DeviceAddress.from_string("M10")
        assert addr.device_type == DeviceType.M
        assert addr.address == 10

    def test_from_string_invalid(self):
        with pytest.raises(ValueError):
            DeviceAddress.from_string("Z0")

    def test_roundtrip_x(self):
        for i in range(32):
            addr = DeviceAddress(device_type=DeviceType.X, address=i)
            parsed = DeviceAddress.from_string(addr.to_string())
            assert parsed.address == i

    def test_equality(self):
        a = DeviceAddress(device_type=DeviceType.X, address=0)
        b = DeviceAddress(device_type=DeviceType.X, address=0)
        assert a == b

    def test_hash(self):
        a = DeviceAddress(device_type=DeviceType.X, address=0)
        b = DeviceAddress(device_type=DeviceType.X, address=0)
        assert hash(a) == hash(b)


class TestTimerConfig:
    def test_from_seconds_5(self):
        cfg = TimerConfig.from_seconds(5.0)
        assert cfg.k_value == 50
        assert cfg.seconds == 5.0

    def test_from_seconds_10(self):
        cfg = TimerConfig.from_seconds(10.0)
        assert cfg.k_value == 100

    def test_from_seconds_1(self):
        cfg = TimerConfig.from_seconds(1.0)
        assert cfg.k_value == 10

    def test_from_seconds_05(self):
        cfg = TimerConfig.from_seconds(0.5)
        assert cfg.k_value == 5


class TestDeviceMap:
    def test_get_by_name(self):
        dm = DeviceMap(allocations=[
            DeviceAllocation(
                logical_name="PB1",
                address=DeviceAddress(device_type=DeviceType.X, address=0),
            ),
        ])
        assert dm.get_by_name("PB1") is not None
        assert dm.get_by_name("PB2") is None

    def test_get_address_string(self):
        dm = DeviceMap(allocations=[
            DeviceAllocation(
                logical_name="PB1",
                address=DeviceAddress(device_type=DeviceType.X, address=0),
            ),
        ])
        assert dm.get_address_string("PB1") == "X0"


class TestInstruction:
    def test_ld_to_text(self):
        inst = Instruction(instruction=InstructionType.LD, device="X0")
        assert inst.to_text() == "LD X0"

    def test_out_timer_to_text(self):
        inst = Instruction(instruction=InstructionType.OUT, device="T0", k_value=50)
        assert inst.to_text() == "OUT T0 K50"

    def test_end_to_text(self):
        inst = Instruction(instruction=InstructionType.END)
        assert inst.to_text() == "END"

    def test_orb_to_text(self):
        inst = Instruction(instruction=InstructionType.ORB)
        assert inst.to_text() == "ORB"


class TestInstructionSequence:
    def test_to_text(self):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="X0"),
            Instruction(instruction=InstructionType.OUT, device="Y0"),
            Instruction(instruction=InstructionType.END),
        ])
        assert seq.to_text() == "LD X0\nOUT Y0\nEND"


class TestTimingDescription:
    def test_practice_11(self, practice_11_timing):
        assert len(practice_11_timing.inputs) == 2
        assert len(practice_11_timing.outputs) == 3
        assert len(practice_11_timing.sequences) == 4
        assert practice_11_timing.sequences[1].delay == 5
        assert practice_11_timing.sequences[2].delay == 10
