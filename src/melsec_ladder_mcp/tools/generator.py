"""generate_ladder tool implementation."""

from __future__ import annotations

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.core.patterns import create_default_registry
from melsec_ladder_mcp.errors import PatternNotFoundError
from melsec_ladder_mcp.models.timing import (
    InputDevice,
    OutputDevice,
    SequenceStep,
    TimingDescription,
)


def generate_ladder(
    description: str,
    inputs: list[dict],
    outputs: list[dict],
    sequences: list[dict],
    device_start: dict | None = None,
) -> dict:
    """Generate ladder logic from timing description.

    Args:
        description: 동작 설명 텍스트
        inputs: 입력 디바이스 목록
        outputs: 출력 디바이스 목록
        sequences: 시퀀스 스텝 목록
        device_start: 디바이스 시작 번호 옵션 (예: {"X": 0, "Y": 0})

    Returns:
        래더 프로그램 JSON
    """
    # Parse input
    timing = TimingDescription(
        description=description,
        inputs=[InputDevice(**inp) for inp in inputs],
        outputs=[OutputDevice(**out) for out in outputs],
        sequences=[SequenceStep(**seq) for seq in sequences],
    )

    # Create allocator and builder
    allocator = DeviceAllocator()
    builder = LadderBuilder(name="MAIN")

    # Find and apply best matching pattern
    registry = create_default_registry()
    best_pattern = registry.find_best(timing)

    if best_pattern is None:
        raise PatternNotFoundError(
            f"No matching pattern found for: {description[:100]}"
        )

    # Generate ladder using the pattern
    best_pattern.generate(timing, allocator, builder)

    # Set device map
    builder.set_device_map(allocator.build_device_map())

    program = builder.build()
    return program.model_dump()
