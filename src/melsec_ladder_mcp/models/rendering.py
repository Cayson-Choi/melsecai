"""Rendering option and result models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RenderFormat(str, Enum):
    SVG = "svg"
    TEXT = "text"


class RenderOptions(BaseModel):
    """Options for ladder diagram rendering."""

    format: RenderFormat = Field(default=RenderFormat.TEXT)
    show_comments: bool = Field(default=True)
    show_device_names: bool = Field(default=True)


class RenderResult(BaseModel):
    """Result of ladder diagram rendering."""

    content: str = Field(..., description="렌더링된 콘텐츠")
    format: RenderFormat
    rung_count: int = Field(default=0)
