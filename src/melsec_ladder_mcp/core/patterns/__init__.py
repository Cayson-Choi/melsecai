"""Pattern engine for ladder generation."""

from melsec_ladder_mcp.core.patterns.base import BasePattern, PatternRegistry
from melsec_ladder_mcp.core.patterns.self_hold import SelfHoldPattern
from melsec_ladder_mcp.core.patterns.timer_delay import TimerDelayPattern
from melsec_ladder_mcp.core.patterns.sequential import SequentialPattern
from melsec_ladder_mcp.core.patterns.full_reset import FullResetPattern
from melsec_ladder_mcp.core.patterns.flicker import FlickerPattern


def create_default_registry() -> PatternRegistry:
    """Create a registry with all built-in patterns."""
    registry = PatternRegistry()
    registry.register(SequentialPattern())
    registry.register(SelfHoldPattern())
    registry.register(TimerDelayPattern())
    registry.register(FullResetPattern())
    registry.register(FlickerPattern())
    return registry


__all__ = [
    "BasePattern",
    "PatternRegistry",
    "SelfHoldPattern",
    "TimerDelayPattern",
    "SequentialPattern",
    "FullResetPattern",
    "FlickerPattern",
    "create_default_registry",
]
