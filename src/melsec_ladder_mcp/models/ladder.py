"""Ladder IR (Intermediate Representation) models."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from melsec_ladder_mcp.models.devices import DeviceMap


class ContactMode(str, Enum):
    NO = "NO"  # a접점 (Normally Open)
    NC = "NC"  # b접점 (Normally Closed)


class ContactElement(BaseModel):
    """접점 요소 (a접점/b접점)."""

    type: Literal["contact"] = "contact"
    device: str = Field(..., description="디바이스 문자열 (예: X0, M0)")
    mode: ContactMode = Field(default=ContactMode.NO)


class CoilElement(BaseModel):
    """코일 출력 요소."""

    type: Literal["coil"] = "coil"
    device: str = Field(..., description="디바이스 문자열 (예: Y0, M0)")


class TimerElement(BaseModel):
    """타이머 출력 요소."""

    type: Literal["timer"] = "timer"
    device: str = Field(..., description="타이머 디바이스 (예: T0)")
    k_value: int = Field(..., gt=0, description="K값 (100ms 단위)")


class CounterElement(BaseModel):
    """카운터 출력 요소."""

    type: Literal["counter"] = "counter"
    device: str = Field(..., description="카운터 디바이스 (예: C0)")
    k_value: int = Field(..., gt=0, description="K값 (카운트 수)")


class SetResetElement(BaseModel):
    """SET/RST 출력 요소."""

    type: Literal["set", "reset"]
    device: str


# Input elements for the rung's input section
InputElement = ContactElement

# Output elements for the rung's output section
OutputElement = Annotated[
    Union[CoilElement, TimerElement, CounterElement, SetResetElement],
    Field(discriminator="type"),
]


class SeriesConnection(BaseModel):
    """직렬 접속 (AND 로직)."""

    type: Literal["series"] = "series"
    elements: list[Union[ContactElement, "ParallelBranch"]] = Field(default_factory=list)


class ParallelBranch(BaseModel):
    """병렬 분기 (OR 로직)."""

    type: Literal["parallel"] = "parallel"
    branches: list[SeriesConnection] = Field(default_factory=list)


# Rebuild for forward references
SeriesConnection.model_rebuild()


# Input section of a rung: either a series connection or a parallel branch
InputSection = Union[SeriesConnection, ParallelBranch]


class Rung(BaseModel):
    """래더 프로그램의 한 Rung (행)."""

    number: int = Field(ge=0)
    comment: str = Field(default="")
    input_section: InputSection
    output_section: list[OutputElement] = Field(default_factory=list)


class LadderProgram(BaseModel):
    """Complete ladder program."""

    name: str = Field(default="MAIN")
    device_map: DeviceMap = Field(default_factory=DeviceMap)
    rungs: list[Rung] = Field(default_factory=list)
    detected_patterns: list[str] = Field(default_factory=list)
