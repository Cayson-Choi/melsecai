"""export_gxworks2 tool implementation."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from melsec_ladder_mcp.automation.config import load_config
from melsec_ladder_mcp.core.compiler import LadderCompiler
from melsec_ladder_mcp.formats.gxworks2 import GXWorks2Formatter
from melsec_ladder_mcp.models.export import ExportOptions, ProjectType, ExportEncoding
from melsec_ladder_mcp.models.ladder import LadderProgram

logger = logging.getLogger(__name__)


def export_gxworks2(
    ladder: dict,
    project_type: str = "simple",
    encoding: str = "shift-jis",
    output_path: str | None = None,
    output_format: str = "gxw",
) -> dict:
    """Export ladder program to GX Works2 format and save to file.

    Args:
        ladder: 래더 프로그램 JSON (generate_ladder 출력)
        project_type: 프로젝트 타입 (simple/structured)
        encoding: 인코딩 (shift-jis/utf-8) — text 포맷에서만 사용
        output_path: 저장 경로 (None이면 config 기본 경로 사용)
        output_format: 출력 포맷 ("gxw" = .gxw 프로젝트, "csv" = CSV만, "text" = IL 텍스트)

    Returns:
        내보내기 결과 (program_text, file_path, warnings 등)
    """
    program = LadderProgram(**ladder)

    if output_format == "gxw":
        return _export_gxw(program, output_path)
    elif output_format == "csv":
        return _export_csv(program, output_path)
    else:
        return _export_text(program, project_type, encoding, output_path)


def _export_gxw(
    program: LadderProgram,
    output_path: str | None,
) -> dict:
    """Export as .gxw project via CSV import + UIA automation.

    Flow: IL → CSV file → GX Works2 (UIA) → Save As .gxw
    Falls back to CSV-only export if UIA automation fails.
    """
    from melsec_ladder_mcp.formats.csv_formatter import instructions_to_csv

    compiler = LadderCompiler()
    sequence = compiler.compile(program)

    cfg = load_config()
    output_dir = cfg["output_dir"]
    if output_path is None:
        output_path = os.path.join(output_dir, f"{program.name}.gxw")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write CSV file (intermediate)
    csv_bytes = instructions_to_csv(
        sequence.instructions,
        program_name=program.name,
    )
    csv_path = output_path.rsplit(".", 1)[0] + ".csv"
    with open(csv_path, "wb") as f:
        f.write(csv_bytes)

    # Try UIA automation to create .gxw
    warnings: list[str] = []
    try:
        from melsec_ladder_mcp.automation.gxworks2_uia import GXWorks2UIA

        uia = GXWorks2UIA()
        uia.build_gxw(csv_path, output_path)
        logger.info(f"GXW project created via UIA: {output_path}")
    except ImportError:
        warnings.append(
            "pywinauto 미설치: CSV 파일만 생성됨. "
            "GX Works2에서 [편집] → [CSV 파일에서 읽기]로 Import하세요."
        )
        output_path = csv_path
    except Exception as e:
        logger.warning(f"UIA automation failed, falling back to CSV: {e}")
        warnings.append(
            f"GX Works2 자동화 실패: {e}\n"
            f"CSV 파일: {csv_path}\n"
            "GX Works2에서 [편집] → [CSV 파일에서 읽기]로 Import하세요."
        )
        output_path = csv_path

    return {
        "program_text": sequence.to_text(),
        "device_comments_csv": "",
        "file_path": output_path,
        "csv_path": csv_path,
        "comments_file_path": None,
        "output_format": "gxw" if output_path.endswith(".gxw") else "csv",
        "warnings": warnings,
        "instruction_count": len(sequence.instructions),
        "rung_count": len(program.rungs),
    }


def _export_csv(
    program: LadderProgram,
    output_path: str | None,
) -> dict:
    """Export as CSV file only (for manual import into GX Works2)."""
    from melsec_ladder_mcp.formats.csv_formatter import instructions_to_csv

    compiler = LadderCompiler()
    sequence = compiler.compile(program)

    cfg = load_config()
    output_dir = cfg["output_dir"]
    if output_path is None:
        output_path = os.path.join(output_dir, f"{program.name}.csv")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    csv_bytes = instructions_to_csv(
        sequence.instructions,
        program_name=program.name,
    )
    with open(output_path, "wb") as f:
        f.write(csv_bytes)

    return {
        "program_text": sequence.to_text(),
        "device_comments_csv": "",
        "file_path": output_path,
        "comments_file_path": None,
        "output_format": "csv",
        "warnings": [],
        "instruction_count": len(sequence.instructions),
        "rung_count": len(program.rungs),
    }


def _export_text(
    program: LadderProgram,
    project_type: str,
    encoding: str,
    output_path: str | None,
) -> dict:
    """Export as IL text file (legacy format)."""
    options = ExportOptions(
        project_type=ProjectType(project_type),
        encoding=ExportEncoding(encoding),
    )

    formatter = GXWorks2Formatter()
    result = formatter.format(program, options)

    cfg = load_config()
    output_dir = cfg["output_dir"]
    if output_path is None:
        output_path = os.path.join(output_dir, "code.txt")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    file_encoding = "shift_jis" if encoding == "shift-jis" else "utf-8"
    with open(output_path, "w", encoding=file_encoding) as f:
        f.write(result.program_text)

    comments_path = os.path.join(os.path.dirname(output_path), "comments.csv")
    if result.device_comments_csv:
        with open(comments_path, "w", encoding="utf-8-sig") as f:
            f.write(result.device_comments_csv)

    result_dict = result.model_dump()
    result_dict["file_path"] = output_path
    result_dict["comments_file_path"] = comments_path if result.device_comments_csv else None
    result_dict["output_format"] = "text"
    return result_dict
