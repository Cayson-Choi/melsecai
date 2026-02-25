"""Tests for DeviceAllocator."""

import pytest

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.errors import DeviceRangeError
from melsec_ladder_mcp.models.devices import DeviceType


class TestDeviceAllocator:
    def test_sequential_x_allocation(self):
        alloc = DeviceAllocator()
        a0 = alloc.allocate_input("PB1")
        a1 = alloc.allocate_input("PB2")
        assert a0.address.to_string() == "X0"
        assert a1.address.to_string() == "X1"

    def test_sequential_y_allocation(self):
        alloc = DeviceAllocator()
        a0 = alloc.allocate_output("RL")
        a1 = alloc.allocate_output("GL")
        a2 = alloc.allocate_output("BZ")
        assert a0.address.to_string() == "Y0"
        assert a1.address.to_string() == "Y1"
        assert a2.address.to_string() == "Y2"

    def test_octal_sequence_x(self):
        """X0-X7 then X10-X17 (octal addressing)."""
        alloc = DeviceAllocator()
        addrs = []
        for i in range(16):
            a = alloc.allocate_input(f"IN{i}")
            addrs.append(a.address.to_string())

        assert addrs[0] == "X0"
        assert addrs[7] == "X7"
        assert addrs[8] == "X10"  # octal
        assert addrs[15] == "X17"  # octal

    def test_m_decimal_allocation(self):
        alloc = DeviceAllocator()
        a0 = alloc.allocate_relay("M_HOLD")
        a1 = alloc.allocate_relay("M_FLAG")
        assert a0.address.to_string() == "M0"
        assert a1.address.to_string() == "M1"

    def test_timer_allocation(self):
        alloc = DeviceAllocator()
        a = alloc.allocate_timer("T_DELAY", seconds=5.0, comment="5초 지연")
        assert a.address.to_string() == "T0"
        assert a.timer_config is not None
        assert a.timer_config.k_value == 50

    def test_duplicate_name_returns_same(self):
        alloc = DeviceAllocator()
        a1 = alloc.allocate_input("PB1")
        a2 = alloc.allocate_input("PB1")
        assert a1.address == a2.address

    def test_conflict_detection(self):
        alloc = DeviceAllocator()
        alloc.allocate("A", DeviceType.X, preferred_address=0)
        # Next auto-allocation should skip 0
        a2 = alloc.allocate("B", DeviceType.X)
        assert a2.address.address == 1

    def test_device_map_build(self):
        alloc = DeviceAllocator()
        alloc.allocate_input("PB1", comment="시작 버튼")
        alloc.allocate_output("RL", comment="적색 램프")
        dm = alloc.build_device_map()
        assert len(dm.allocations) == 2
        assert dm.get_by_name("PB1") is not None
        assert dm.get_address_string("RL") == "Y0"
