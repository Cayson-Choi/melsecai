"""analyze_timing_diagram tool implementation."""

from __future__ import annotations

from melsec_ladder_mcp.models.timing import (
    DetectedPattern,
    InputDevice,
    OutputDevice,
    SequenceStep,
    TimingAnalysis,
    TimingDescription,
)


def analyze_timing_diagram(
    description: str,
    inputs: list[dict],
    outputs: list[dict],
    sequences: list[dict],
) -> dict:
    """Analyze timing diagram description and detect patterns.

    Args:
        description: 동작 설명 텍스트
        inputs: 입력 디바이스 목록
        outputs: 출력 디바이스 목록
        sequences: 시퀀스 스텝 목록

    Returns:
        구조화된 타이밍 분석 결과
    """
    # Parse input models
    input_devices = [InputDevice(**inp) for inp in inputs]
    output_devices = [OutputDevice(**out) for out in outputs]
    sequence_steps = [SequenceStep(**seq) for seq in sequences]

    timing = TimingDescription(
        description=description,
        inputs=input_devices,
        outputs=output_devices,
        sequences=sequence_steps,
    )

    # Detect patterns
    detected: list[DetectedPattern] = []
    warnings: list[str] = []

    has_self_hold = False
    has_timer = False
    has_flicker = False
    has_sequential = False
    has_full_reset = False

    # Check for self-hold pattern
    has_start = any(
        "ON" in s.action.upper() and "ALL" not in s.action.upper() and s.delay is None
        for s in sequence_steps
    )
    has_stop = any(
        "OFF" in s.action.upper() or "정지" in s.action
        for s in sequence_steps
    )
    if has_start and has_stop and len(input_devices) >= 2:
        has_self_hold = True
        detected.append(DetectedPattern(
            pattern_type="self_hold",
            confidence=0.9,
            details={"start": input_devices[0].name, "stop": input_devices[-1].name},
        ))

    # Check for timer delays
    timer_steps = [s for s in sequence_steps if s.delay is not None and s.delay > 0]
    if timer_steps:
        has_timer = True
        detected.append(DetectedPattern(
            pattern_type="timer_delay",
            confidence=0.95,
            details={"count": len(timer_steps), "delays": [s.delay for s in timer_steps]},
        ))

    # Check for flicker
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in ["점멸", "flicker", "blink", "반복", "깜빡"]):
        has_flicker = True
        detected.append(DetectedPattern(
            pattern_type="flicker",
            confidence=0.85,
        ))

    # Check for full reset
    if any("ALL" in s.action.upper() and "OFF" in s.action.upper() for s in sequence_steps):
        has_full_reset = True
        detected.append(DetectedPattern(
            pattern_type="full_reset",
            confidence=0.95,
        ))

    # Sequential is self_hold + timer
    if has_self_hold and has_timer:
        has_sequential = True
        detected.append(DetectedPattern(
            pattern_type="sequential",
            confidence=0.9,
        ))

    # Validation warnings
    if not input_devices:
        warnings.append("입력 디바이스가 없습니다")
    if not output_devices:
        warnings.append("출력 디바이스가 없습니다")
    if not sequence_steps:
        warnings.append("시퀀스 스텝이 없습니다")

    analysis = TimingAnalysis(
        timing=timing,
        detected_patterns=detected,
        has_self_hold=has_self_hold,
        has_timer=has_timer,
        has_flicker=has_flicker,
        has_sequential=has_sequential,
        has_full_reset=has_full_reset,
        warnings=warnings,
    )

    return analysis.model_dump()
