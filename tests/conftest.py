"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from melsec_ladder_mcp.models.timing import (
    InputDevice,
    InputMode,
    InputType,
    OutputDevice,
    OutputType,
    SequenceStep,
    TimingDescription,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def practice_11_input() -> dict:
    """Practice 11 input data as raw dict."""
    with open(FIXTURES_DIR / "practice_11_input.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def practice_11_expected_il() -> str:
    """Practice 11 expected IL text."""
    with open(FIXTURES_DIR / "practice_11_expected_il.txt", encoding="utf-8") as f:
        return f.read().strip()


@pytest.fixture
def practice_11_timing() -> TimingDescription:
    """Practice 11 as a TimingDescription model."""
    return TimingDescription(
        description="PB1을 누르면 RL이 점등되고 5초 후 GL이 점등되며, 10초 후 BZ가 동작한다. PB2를 누르면 모든 동작이 정지한다.",
        inputs=[
            InputDevice(name="PB1", type=InputType.PUSH_BUTTON, mode=InputMode.MOMENTARY, comment="시작 버튼"),
            InputDevice(name="PB2", type=InputType.PUSH_BUTTON, mode=InputMode.MOMENTARY, comment="정지 버튼"),
        ],
        outputs=[
            OutputDevice(name="RL", type=OutputType.LAMP, comment="적색 램프"),
            OutputDevice(name="GL", type=OutputType.LAMP, comment="녹색 램프"),
            OutputDevice(name="BZ", type=OutputType.BUZZER, comment="부저"),
        ],
        sequences=[
            SequenceStep(trigger="PB1", action="RL ON"),
            SequenceStep(trigger="RL ON", delay=5, action="GL ON"),
            SequenceStep(trigger="RL ON", delay=10, action="BZ ON"),
            SequenceStep(trigger="PB2", action="ALL OFF"),
        ],
    )


@pytest.fixture
def simple_onoff_timing() -> TimingDescription:
    """Simple ON/OFF timing description."""
    return TimingDescription(
        description="PB1을 누르면 Y0 ON, PB2를 누르면 Y0 OFF",
        inputs=[
            InputDevice(name="PB1", type=InputType.PUSH_BUTTON, mode=InputMode.MOMENTARY),
            InputDevice(name="PB2", type=InputType.PUSH_BUTTON, mode=InputMode.MOMENTARY),
        ],
        outputs=[
            OutputDevice(name="LAMP", type=OutputType.LAMP),
        ],
        sequences=[
            SequenceStep(trigger="PB1", action="LAMP ON"),
            SequenceStep(trigger="PB2", action="ALL OFF"),
        ],
    )


@pytest.fixture
def flicker_timing() -> TimingDescription:
    """Flicker timing description."""
    return TimingDescription(
        description="PB1을 누르면 RL이 1초 간격으로 점멸한다. PB2를 누르면 정지한다.",
        inputs=[
            InputDevice(name="PB1", type=InputType.PUSH_BUTTON, mode=InputMode.MOMENTARY),
            InputDevice(name="PB2", type=InputType.PUSH_BUTTON, mode=InputMode.MOMENTARY),
        ],
        outputs=[
            OutputDevice(name="RL", type=OutputType.LAMP),
        ],
        sequences=[
            SequenceStep(trigger="PB1", action="RL ON", delay=1),
            SequenceStep(trigger="PB2", action="ALL OFF"),
        ],
    )
