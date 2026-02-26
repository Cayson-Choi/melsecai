"""import_to_gxworks2 tool implementation."""

from __future__ import annotations

import os

from melsec_ladder_mcp.automation.config import load_config


def import_to_gxworks2(
    file_path: str,
    auto_open: bool = True,
    cpu_type: str | None = None,
    project_type: str | None = None,
    gxworks2_language: str | None = None,
    gxworks2_path: str | None = None,
) -> dict:
    """Import a generated text file into GX Works2 automatically.

    Uses pywinauto to:
    1. Launch GX Works2 (or connect to running instance)
    2. Create a new project
    3. Import the IL text file
    4. Display the ladder in the editor

    Args:
        file_path: 텍스트 파일 경로 (예: D:\\melsecai\\melseccode\\code.txt)
        auto_open: GX Works2 자동 실행 여부
        cpu_type: CPU 타입 (예: Q03UDE). None이면 config 기본값 사용.
        project_type: 프로젝트 타입 (simple/structured). None이면 config 기본값.
        gxworks2_language: GX Works2 메뉴 언어 (ko/en/ja). None이면 config 기본값.
        gxworks2_path: GX Works2 실행 파일 경로. None이면 자동 탐지.

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
        return _import_csv(file_path, auto_open)

    # .txt files: legacy pywinauto import flow
    return _import_text(
        file_path, auto_open, cpu_type, project_type,
        gxworks2_language, gxworks2_path,
    )


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


def _import_csv(file_path: str, auto_open: bool) -> dict:
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
        uia.build_gxw(file_path, output_path)
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


def _import_text(
    file_path: str,
    auto_open: bool,
    cpu_type: str | None,
    project_type: str | None,
    gxworks2_language: str | None,
    gxworks2_path: str | None,
) -> dict:
    """Import a .txt IL file via pywinauto (legacy flow)."""
    # Load config
    cfg = load_config()
    language = gxworks2_language or cfg["language"]
    cpu = cpu_type or cfg["default_cpu"]
    proj_type = project_type or cfg["default_project_type"]
    exe_path = gxworks2_path or cfg["install_path"]
    timeouts = cfg["timeouts"]

    if not auto_open:
        return {
            "status": "skipped",
            "message": (
                f"auto_open=False로 설정되어 자동 Import를 건너뜁니다.\n"
                f"텍스트 파일: {file_path}\n"
                "수동으로 Import하려면:\n"
                "[프로젝트] → [읽어들이기] → [텍스트 파일]에서 위 파일을 선택하세요."
            ),
            "file_path": file_path,
        }

    # Try pywinauto automation
    try:
        from melsec_ladder_mcp.automation.gxworks2_controller import GXWorks2Controller

        controller = GXWorks2Controller(
            language=language,
            gxworks2_path=exe_path,
            timeouts=timeouts,
        )
        return controller.run(
            file_path=file_path,
            cpu_type=cpu,
            project_type=proj_type,
        )
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
                f"텍스트 파일이 저장되었습니다: {file_path}\n"
                "수동으로 Import하려면:\n"
                "[프로젝트] → [읽어들이기] → [텍스트 파일]에서 위 파일을 선택하세요."
            ),
        }
