"""Device address models for MELSEC-Q series."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class DeviceType(str, Enum):
    X = "X"  # Input
    Y = "Y"  # Output
    M = "M"  # Auxiliary relay
    T = "T"  # Timer
    C = "C"  # Counter
    D = "D"  # Data register


# Devices that use octal addressing
OCTAL_DEVICES = {DeviceType.X, DeviceType.Y}


class DeviceAddress(BaseModel):
    """A MELSEC device address with octal/decimal handling.

    For X/Y devices: internal address is sequential integer,
    display format is octal (X0, X1, ..., X7, X10, X11, ...).
    For M/T/C/D devices: address is decimal as-is.
    """

    device_type: DeviceType
    address: int = Field(ge=0, description="Internal sequential address")

    def to_string(self) -> str:
        """Convert to display string (e.g., X0, X17, M0, T0)."""
        if self.device_type in OCTAL_DEVICES:
            return f"{self.device_type.value}{oct(self.address)[2:].upper()}"
        return f"{self.device_type.value}{self.address}"

    @classmethod
    def from_string(cls, s: str) -> DeviceAddress:
        """Parse a device string like 'X0', 'X17', 'M10', 'T0'."""
        if not s or len(s) < 2:
            raise ValueError(f"Invalid device string: {s}")

        device_char = s[0].upper()
        addr_str = s[1:]

        try:
            device_type = DeviceType(device_char)
        except ValueError:
            raise ValueError(f"Unknown device type: {device_char}")

        if device_type in OCTAL_DEVICES:
            address = int(addr_str, 8)
        else:
            address = int(addr_str)

        return cls(device_type=device_type, address=address)

    def __str__(self) -> str:
        return self.to_string()

    def __hash__(self) -> int:
        return hash((self.device_type, self.address))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DeviceAddress):
            return self.device_type == other.device_type and self.address == other.address
        return NotImplemented


class TimerConfig(BaseModel):
    """Timer configuration."""

    k_value: int = Field(..., gt=0, description="K value (100ms units)")
    seconds: float = Field(..., gt=0, description="Time in seconds")
    comment: str = Field(default="")

    @classmethod
    def from_seconds(cls, seconds: float, comment: str = "") -> TimerConfig:
        """Create from seconds (100ms base unit)."""
        k_value = int(seconds * 10)
        if k_value <= 0:
            k_value = 1
        return cls(k_value=k_value, seconds=seconds, comment=comment)


class DeviceAllocation(BaseModel):
    """A single device allocation mapping."""

    logical_name: str = Field(..., description="논리 이름 (예: PB1, RL)")
    address: DeviceAddress
    comment: str = Field(default="")
    timer_config: TimerConfig | None = Field(default=None)


class DeviceMap(BaseModel):
    """Complete device allocation map for a program."""

    allocations: list[DeviceAllocation] = Field(default_factory=list)

    def get_by_name(self, name: str) -> DeviceAllocation | None:
        """Find allocation by logical name."""
        for alloc in self.allocations:
            if alloc.logical_name == name:
                return alloc
        return None

    def get_by_address(self, address: DeviceAddress) -> DeviceAllocation | None:
        """Find allocation by device address."""
        for alloc in self.allocations:
            if alloc.address == address:
                return alloc
        return None

    def get_address_string(self, name: str) -> str | None:
        """Get display string for a logical name."""
        alloc = self.get_by_name(name)
        return alloc.address.to_string() if alloc else None
