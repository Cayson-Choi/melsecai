"""Base pattern and pattern registry."""

from __future__ import annotations

from abc import ABC, abstractmethod

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.models.timing import SequenceStep, TimingDescription


class BasePattern(ABC):
    """Abstract base class for ladder generation patterns."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Pattern name identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable pattern description."""
        ...

    @property
    def priority(self) -> int:
        """Higher priority patterns are checked first. Default 0."""
        return 0

    @abstractmethod
    def matches(self, timing: TimingDescription) -> bool:
        """Check if this pattern matches the given timing description."""
        ...

    @abstractmethod
    def generate(
        self,
        timing: TimingDescription,
        allocator: DeviceAllocator,
        builder: LadderBuilder,
    ) -> None:
        """Generate ladder rungs for this pattern.

        Modifies builder and allocator in-place.
        """
        ...


class PatternRegistry:
    """Registry for pattern matching and lookup."""

    def __init__(self) -> None:
        self._patterns: list[BasePattern] = []

    def register(self, pattern: BasePattern) -> None:
        """Register a pattern."""
        self._patterns.append(pattern)
        # Keep sorted by priority (highest first)
        self._patterns.sort(key=lambda p: p.priority, reverse=True)

    def find_matching(self, timing: TimingDescription) -> list[BasePattern]:
        """Find all patterns that match the timing description."""
        return [p for p in self._patterns if p.matches(timing)]

    def find_best(self, timing: TimingDescription) -> BasePattern | None:
        """Find the highest-priority matching pattern."""
        matches = self.find_matching(timing)
        return matches[0] if matches else None

    def get_pattern(self, name: str) -> BasePattern | None:
        """Get a pattern by name."""
        for p in self._patterns:
            if p.name == name:
                return p
        return None

    @property
    def patterns(self) -> list[BasePattern]:
        return list(self._patterns)
