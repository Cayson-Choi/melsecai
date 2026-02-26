"""import_to_gxworks2 tool implementation."""

from __future__ import annotations

import os


def import_to_gxworks2(
    file_path: str,
    auto_open: bool = True,
    cpu_type: str | None = None,
    series: str = "QCPU (Q mode)",
    **_kwargs,
) -> dict:
    """Import a generated file into GX Works2.

    Supports .gxw (open directly) and .csv (UIA automation) files.

    Args:
        file_path: 파일 경로 (.gxw 또는 .csv)
        auto_open: GX Works2 자동 실행 여부 (False면 수동 안내만 반환)
        cpu_type: CPU 타입 (e.g. "Q03UDE"). CSV import 시 새 프로젝트 생성에 사용.
        series: PLC 시리즈 (기본: "QCPU (Q mode)")

    Returns:
        결과 dict (status, message, file_path, fallback 등)
    """
    # Verify file exists
    if not os.path.isfile(file_path):
        return {
            "status": "error",
            "error_type": "file_not_found",
            "message": f"파일이 존재하지 않습니다: {file_path}",
        }

    # .gxw files: open directly with os.startfile (GX Works2 association)
    if file_path.lower().endswith(".gxw"):
        return _open_gxw(file_path, auto_open)

    # .csv files: import via UIA automation
    if file_path.lower().endswith(".csv"):
        return _import_csv(file_path, auto_open, cpu_type=cpu_type, series=series)

    return {
        "status": "error",
        "error_type": "unsupported_format",
        "message": f"지원하지 않는 파일 형식입니다: {file_path}\n.gxw 또는 .csv 파일만 지원합니다.",
    }


def _open_gxw(file_path: str, auto_open: bool) -> dict:
    """Open a .gxw file directly in GX Works2."""
    if not auto_open:
        return {
            "status": "skipped",
            "message": (
                f"auto_open=False로 설정되어 자동 열기를 건너뜁니다.\n"
                f"프로젝트 파일: {file_path}\n"
                "GX Works2에서 [프로젝트] → [열기]로 위 파일을 선택하세요."
            ),
            "file_path": file_path,
        }
    try:
        os.startfile(file_path)
        return {
            "status": "success",
            "message": f"GX Works2에서 프로젝트를 열었습니다: {file_path}",
            "file_path": file_path,
        }
    except OSError as e:
        return {
            "status": "error",
            "error_type": "open_failed",
            "message": f"프로젝트 파일 열기 실패: {e}",
            "file_path": file_path,
            "fallback": (
                f"프로젝트 파일이 저장되었습니다: {file_path}\n"
                "GX Works2에서 [프로젝트] → [열기]로 위 파일을 선택하세요."
            ),
        }


def _import_csv(
    file_path: str,
    auto_open: bool,
    cpu_type: str | None = None,
    series: str = "QCPU (Q mode)",
) -> dict:
    """Import a CSV file into GX Works2 via UIA automation."""
    if not auto_open:
        return {
            "status": "skipped",
            "message": (
                f"auto_open=False로 설정되어 자동 Import를 건너뜁니다.\n"
                f"CSV 파일: {file_path}\n"
                "GX Works2에서 [편집] → [CSV 파일에서 읽기]로 위 파일을 선택하세요."
            ),
            "file_path": file_path,
        }
    try:
        from melsec_ladder_mcp.automation.gxworks2_uia import GXWorks2UIA

        output_path = file_path.rsplit(".", 1)[0] + ".gxw"
        uia = GXWorks2UIA()
        uia.build_gxw(
            file_path, output_path, cpu_type=cpu_type, series=series,
        )
        return {
            "status": "success",
            "message": f"GX Works2에서 CSV를 Import하고 프로젝트를 저장했습니다: {output_path}",
            "file_path": output_path,
            "csv_path": file_path,
        }
    except ImportError:
        return {
            "status": "error",
            "error_type": "dependency_missing",
            "message": (
                "pywinauto가 설치되지 않았습니다.\n"
                "설치: pip install pywinauto\n"
                "또는 Windows 환경에서만 사용 가능합니다."
            ),
            "file_path": file_path,
            "fallback": (
                f"CSV 파일이 저장되었습니다: {file_path}\n"
                "GX Works2에서 [편집] → [CSV 파일에서 읽기]로 위 파일을 선택하세요."
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "automation_failed",
            "message": str(e),
            "file_path": file_path,
            "fallback": (
                f"CSV 파일이 저장되었습니다: {file_path}\n"
                "GX Works2에서 [편집] → [CSV 파일에서 읽기]로 위 파일을 선택하세요."
            ),
        }
