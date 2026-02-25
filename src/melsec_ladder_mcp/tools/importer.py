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
            "message": f"텍스트 파일이 존재하지 않습니다: {file_path}",
        }

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
