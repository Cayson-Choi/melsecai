"""Input models for timing diagram analysis."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class InputType(str, Enum):
    PUSH_BUTTON = "push_button"
    TOGGLE_SWITCH = "toggle_switch"
    SENSOR = "sensor"
    LIMIT_SWITCH = "limit_switch"


class InputMode(str, Enum):
    MOMENTARY = "momentary"
    MAINTAINED = "maintained"


class OutputType(str, Enum):
    LAMP = "lamp"
    MOTOR = "motor"
    BUZZER = "buzzer"
    SOLENOID = "solenoid"
    RELAY = "relay"


class InputDevice(BaseModel):
    """An input device in the timing diagram."""

    name: str = Field(..., description="논리 이름 (예: PB1)")
    type: InputType = Field(default=InputType.PUSH_BUTTON)
    mode: InputMode = Field(default=InputMode.MOMENTARY)
    comment: str = Field(default="", description="디바이스 코멘트")


class OutputDevice(BaseModel):
    """An output device in the timing diagram."""

    name: str = Field(..., description="논리 이름 (예: RL)")
    type: OutputType = Field(default=OutputType.LAMP)
    comment: str = Field(default="", description="디바이스 코멘트")


class SequenceStep(BaseModel):
    """A single step in the timing sequence."""

    trigger: str = Field(..., description="트리거 조건 (예: PB1, RL ON)")
    action: str = Field(..., description="동작 (예: RL ON, ALL OFF)")
    delay: float | None = Field(default=None, description="지연 시간(초)")


class TimingDescription(BaseModel):
    """Complete timing diagram description as input to the system."""

    description: str = Field(..., description="동작 설명 텍스트")
    inputs: list[InputDevice] = Field(default_factory=list)
    outputs: list[OutputDevice] = Field(default_factory=list)
    sequences: list[SequenceStep] = Field(default_factory=list)


class DetectedPattern(BaseModel):
    """A pattern detected during timing analysis."""

    pattern_type: str = Field(..., description="패턴 유형 (self_hold, timer_delay, ...)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    details: dict = Field(default_factory=dict)


class TimingAnalysis(BaseModel):
    """Result of timing diagram analysis."""

    timing: TimingDescription
    detected_patterns: list[DetectedPattern] = Field(default_factory=list)
    has_self_hold: bool = False
    has_timer: bool = False
    has_flicker: bool = False
    has_sequential: bool = False
    has_full_reset: bool = False
    warnings: list[str] = Field(default_factory=list)
