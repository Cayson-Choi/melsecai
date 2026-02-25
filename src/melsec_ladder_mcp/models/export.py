"""Export option and result models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    SIMPLE = "simple"
    STRUCTURED = "structured"


class ExportEncoding(str, Enum):
    SHIFT_JIS = "shift-jis"
    UTF8 = "utf-8"


class ExportOptions(BaseModel):
    """Options for GX Works2 export."""

    project_type: ProjectType = Field(default=ProjectType.SIMPLE)
    encoding: ExportEncoding = Field(default=ExportEncoding.SHIFT_JIS)
    include_comments: bool = Field(default=True)
    include_step_numbers: bool = Field(default=False)


class ExportResult(BaseModel):
    """Result of GX Works2 export."""

    program_text: str = Field(..., description="IL 프로그램 텍스트")
    device_comments_csv: str = Field(default="", description="디바이스 코멘트 CSV")
    warnings: list[str] = Field(default_factory=list)
    instruction_count: int = Field(default=0)
    rung_count: int = Field(default=0)
