"""export_gxworks2 tool implementation."""

from __future__ import annotations

from melsec_ladder_mcp.formats.gxworks2 import GXWorks2Formatter
from melsec_ladder_mcp.models.export import ExportOptions, ProjectType, ExportEncoding
from melsec_ladder_mcp.models.ladder import LadderProgram


def export_gxworks2(
    ladder: dict,
    project_type: str = "simple",
    encoding: str = "shift-jis",
) -> dict:
    """Export ladder program to GX Works2 text import format.

    Args:
        ladder: 래더 프로그램 JSON (generate_ladder 출력)
        project_type: 프로젝트 타입 (simple/structured)
        encoding: 인코딩 (shift-jis/utf-8)

    Returns:
        내보내기 결과 (program_text, device_comments_csv, warnings)
    """
    # Parse ladder program
    program = LadderProgram(**ladder)

    # Create export options
    options = ExportOptions(
        project_type=ProjectType(project_type),
        encoding=ExportEncoding(encoding),
    )

    # Format
    formatter = GXWorks2Formatter()
    result = formatter.format(program, options)

    return result.model_dump()
