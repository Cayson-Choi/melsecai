"""Full reset pattern."""

from __future__ import annotations

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.core.patterns.base import BasePattern
from melsec_ladder_mcp.models.timing import TimingDescription


class FullResetPattern(BasePattern):
    """Full reset: stop button turns everything OFF.

    This pattern is typically handled by the self-hold circuit's ANI stop contact.
    It's used as an auxiliary pattern when explicit RST instructions are needed.
    """

    @property
    def name(self) -> str:
        return "full_reset"

    @property
    def description(self) -> str:
        return "전체 리셋 (정지 버튼으로 전체 OFF)"

    @property
    def priority(self) -> int:
        return 3

    def matches(self, timing: TimingDescription) -> bool:
        """Match if there's an ALL OFF action."""
        for seq in timing.sequences:
            action_upper = seq.action.upper()
            if "ALL OFF" in action_upper or "ALL" in action_upper and "OFF" in action_upper:
                return True
            if "전체" in seq.action and ("정지" in seq.action or "OFF" in action_upper):
                return True
        return False

    def generate(
        self,
        timing: TimingDescription,
        allocator: DeviceAllocator,
        builder: LadderBuilder,
    ) -> None:
        """Full reset is typically handled by the self-hold ANI contact.

        This pattern exists for detection/reporting; the actual reset logic
        is embedded in the self-hold pattern via the NC stop contact.
        """
        builder.add_pattern("full_reset")
