"""export_gxworks2 tool implementation."""

from __future__ import annotations

import os
from pathlib import Path

from melsec_ladder_mcp.automation.config import load_config
from melsec_ladder_mcp.formats.gxworks2 import GXWorks2Formatter
from melsec_ladder_mcp.models.export import ExportOptions, ProjectType, ExportEncoding
from melsec_ladder_mcp.models.ladder import LadderProgram


def export_gxworks2(
    ladder: dict,
    project_type: str = "simple",
    encoding: str = "shift-jis",
    output_path: str | None = None,
) -> dict:
    """Export ladder program to GX Works2 text import format and save to file.

    The IL text is saved to disk (default: D:\\melsecai\\melseccode\\code.txt)
    so that import_to_gxworks2 can auto-import it.

    Args:
        ladder: 래더 프로그램 JSON (generate_ladder 출력)
        project_type: 프로젝트 타입 (simple/structured)
        encoding: 인코딩 (shift-jis/utf-8)
        output_path: 저장 경로 (None이면 config 기본 경로 사용)

    Returns:
        내보내기 결과 (program_text, device_comments_csv, file_path, warnings)
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

    # Determine output path
    cfg = load_config()
    output_dir = cfg["output_dir"]
    if output_path is None:
        output_path = os.path.join(output_dir, "code.txt")

    # Save to disk
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    file_encoding = "shift_jis" if encoding == "shift-jis" else "utf-8"
    with open(output_path, "w", encoding=file_encoding) as f:
        f.write(result.program_text)

    # Save device comments CSV alongside
    comments_path = os.path.join(os.path.dirname(output_path), "comments.csv")
    if result.device_comments_csv:
        with open(comments_path, "w", encoding="utf-8-sig") as f:
            f.write(result.device_comments_csv)

    result_dict = result.model_dump()
    result_dict["file_path"] = output_path
    result_dict["comments_file_path"] = comments_path if result.device_comments_csv else None
    return result_dict
