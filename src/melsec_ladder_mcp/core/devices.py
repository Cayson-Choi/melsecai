"""Device allocator for MELSEC-Q series."""

from __future__ import annotations

from melsec_ladder_mcp.errors import DeviceConflictError, DeviceRangeError
from melsec_ladder_mcp.models.devices import (
    DeviceAddress,
    DeviceAllocation,
    DeviceMap,
    DeviceType,
    OCTAL_DEVICES,
    TimerConfig,
)

# Maximum internal addresses per device type
DEVICE_LIMITS: dict[DeviceType, int] = {
    DeviceType.X: 32,   # X0-X37 (octal) = 0-31 internal
    DeviceType.Y: 32,   # Y0-Y37 (octal) = 0-31 internal
    DeviceType.M: 100,  # M0-M99
    DeviceType.T: 100,  # T0-T99
    DeviceType.C: 100,  # C0-C99
    DeviceType.D: 100,  # D0-D99
}


class DeviceAllocator:
    """Sequential device allocator with conflict detection."""

    def __init__(self) -> None:
        self._next_address: dict[DeviceType, int] = {dt: 0 for dt in DeviceType}
        self._allocated: dict[DeviceType, set[int]] = {dt: set() for dt in DeviceType}
        self._allocations: list[DeviceAllocation] = []

    def allocate(
        self,
        logical_name: str,
        device_type: DeviceType,
        comment: str = "",
        timer_config: TimerConfig | None = None,
        preferred_address: int | None = None,
    ) -> DeviceAllocation:
        """Allocate the next available address for a device type."""
        # Check for duplicate logical name
        for alloc in self._allocations:
            if alloc.logical_name == logical_name:
                return alloc

        if preferred_address is not None:
            address = preferred_address
        else:
            address = self._next_address[device_type]

        # Find next free address
        limit = DEVICE_LIMITS[device_type]
        while address in self._allocated[device_type]:
            address += 1
            if address >= limit:
                raise DeviceRangeError(
                    f"No more addresses available for {device_type.value} "
                    f"(limit: {limit})"
                )

        if address >= limit:
            raise DeviceRangeError(
                f"Address {address} exceeds limit for {device_type.value} "
                f"(max: {limit - 1})"
            )

        # Check conflict
        if address in self._allocated[device_type]:
            raise DeviceConflictError(
                f"Address {device_type.value}{address} is already allocated"
            )

        self._allocated[device_type].add(address)
        self._next_address[device_type] = address + 1

        device_address = DeviceAddress(device_type=device_type, address=address)
        allocation = DeviceAllocation(
            logical_name=logical_name,
            address=device_address,
            comment=comment,
            timer_config=timer_config,
        )
        self._allocations.append(allocation)
        return allocation

    def allocate_input(self, name: str, comment: str = "") -> DeviceAllocation:
        return self.allocate(name, DeviceType.X, comment=comment)

    def allocate_output(self, name: str, comment: str = "") -> DeviceAllocation:
        return self.allocate(name, DeviceType.Y, comment=comment)

    def allocate_relay(self, name: str, comment: str = "") -> DeviceAllocation:
        return self.allocate(name, DeviceType.M, comment=comment)

    def allocate_timer(
        self, name: str, seconds: float, comment: str = ""
    ) -> DeviceAllocation:
        config = TimerConfig.from_seconds(seconds, comment=comment)
        return self.allocate(
            name, DeviceType.T, comment=comment, timer_config=config
        )

    def build_device_map(self) -> DeviceMap:
        """Build a DeviceMap from all allocations."""
        return DeviceMap(allocations=list(self._allocations))

    def get_allocation(self, logical_name: str) -> DeviceAllocation | None:
        for alloc in self._allocations:
            if alloc.logical_name == logical_name:
                return alloc
        return None
