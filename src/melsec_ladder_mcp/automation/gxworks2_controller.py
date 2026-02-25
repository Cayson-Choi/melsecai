"""GX Works2 Windows UI automation controller using pywinauto."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from melsec_ladder_mcp.automation.menu_paths import DEFAULT_INSTALL_PATHS, MENU_PATHS
from melsec_ladder_mcp.automation.dialog_handlers import dismiss_save_prompt, handle_file_dialog

logger = logging.getLogger(__name__)


class GXWorks2Error(Exception):
    """Errors specific to GX Works2 automation."""


class GXWorks2NotFoundError(GXWorks2Error):
    """GX Works2 executable not found."""


class GXWorks2TimeoutError(GXWorks2Error):
    """Timeout waiting for GX Works2 UI element."""


class GXWorks2Controller:
    """GX Works2 Windows UI automation controller.

    Uses pywinauto to:
    1. Launch or connect to GX Works2
    2. Create a new project
    3. Import a text file (IL program)
    """

    def __init__(
        self,
        language: str = "ko",
        gxworks2_path: str | None = None,
        timeouts: dict | None = None,
    ) -> None:
        self.language = language
        self.menu = MENU_PATHS.get(language, MENU_PATHS["ko"])
        self.gxworks2_path = gxworks2_path or self._find_gxworks2()
        self.timeouts = timeouts or {"launch": 10, "dialog": 5, "import_wait": 10}
        self._app = None

    def _find_gxworks2(self) -> str:
        """Find GX Works2 executable path."""
        for path in DEFAULT_INSTALL_PATHS:
            if os.path.isfile(path):
                return path
        raise GXWorks2NotFoundError(
            "GX Works2를 찾을 수 없습니다. "
            "gxworks2_path 파라미터로 설치 경로를 지정해주세요.\n"
            f"탐색 경로: {DEFAULT_INSTALL_PATHS}"
        )

    def connect_or_launch(self) -> None:
        """Connect to a running GX Works2 or launch a new instance."""
        from pywinauto import Application
        from pywinauto.timings import TimeoutError as PywinautoTimeout

        # Try to connect to existing instance
        try:
            self._app = Application(backend="uia").connect(
                title_re=".*GX Works2.*",
                timeout=3,
            )
            logger.info("Connected to existing GX Works2 instance")
            return
        except Exception:
            logger.info("No running GX Works2 found, launching new instance")

        # Launch new instance
        if not os.path.isfile(self.gxworks2_path):
            raise GXWorks2NotFoundError(
                f"GX Works2 실행 파일이 존재하지 않습니다: {self.gxworks2_path}"
            )

        self._app = Application(backend="uia").start(
            self.gxworks2_path,
            timeout=self.timeouts["launch"],
        )

        # Wait for main window to appear
        launch_timeout = self.timeouts["launch"]
        try:
            main = self._app.window(title_re=".*GX Works2.*")
            main.wait("ready", timeout=launch_timeout)
            logger.info("GX Works2 launched successfully")
        except PywinautoTimeout:
            raise GXWorks2TimeoutError(
                f"GX Works2가 {launch_timeout}초 내에 시작되지 않았습니다"
            )

        # Extra wait for UI to stabilize
        time.sleep(2)

    def create_new_project(
        self,
        cpu_type: str = "Q03UDE",
        project_type: str = "simple",
    ) -> None:
        """Create a new project in GX Works2."""
        if self._app is None:
            raise GXWorks2Error("GX Works2에 연결되지 않았습니다. connect_or_launch()를 먼저 호출하세요.")

        main = self._app.window(title_re=".*GX Works2.*")
        main.set_focus()
        time.sleep(0.5)

        # Open new project menu
        try:
            main.menu_select(self.menu["new_project"])
        except Exception as e:
            logger.warning(f"Menu select failed, trying keyboard shortcut: {e}")
            main.type_keys("^n")  # Ctrl+N fallback

        time.sleep(1)

        # Dismiss save prompt if it appears
        dismiss_save_prompt(self._app, self.menu, timeout=2)
        time.sleep(1)

        # Handle new project dialog
        # The dialog structure varies by GX Works2 version
        # Try to find and interact with the new project dialog
        try:
            new_proj_dlg = self._app.window(title_re=".*新規.*|.*새로.*|.*New.*")
            if new_proj_dlg.exists(timeout=3):
                # Look for OK button to accept defaults
                ok_btn = new_proj_dlg.child_window(
                    title_re=f".*{self.menu['btn_ok']}.*|.*OK.*",
                    control_type="Button",
                )
                if ok_btn.exists(timeout=2):
                    ok_btn.click()
                    logger.info("New project dialog: clicked OK with defaults")
        except Exception as e:
            logger.warning(f"New project dialog handling: {e}")

        time.sleep(2)

    def import_text_file(self, file_path: str) -> None:
        """Import a text file into the current GX Works2 project."""
        if self._app is None:
            raise GXWorks2Error("GX Works2에 연결되지 않았습니다.")

        # Verify file exists
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"텍스트 파일이 존재하지 않습니다: {file_path}")

        main = self._app.window(title_re=".*GX Works2.*")
        main.set_focus()
        time.sleep(0.5)

        # Open text import menu
        try:
            main.menu_select(self.menu["read_text"])
        except Exception as e:
            raise GXWorks2Error(
                f"텍스트 Import 메뉴를 열 수 없습니다: {e}\n"
                f"메뉴 경로: {self.menu['read_text']}"
            )

        time.sleep(1)

        # Handle file dialog
        handle_file_dialog(
            self._app,
            self.menu,
            file_path,
            timeout=self.timeouts["dialog"],
        )

        # Wait for import to complete
        time.sleep(self.timeouts["import_wait"])
        logger.info(f"Text file imported: {file_path}")

    def run(
        self,
        file_path: str,
        cpu_type: str = "Q03UDE",
        project_type: str = "simple",
    ) -> dict:
        """Full automation: launch → new project → import text file.

        Args:
            file_path: Path to the IL text file
            cpu_type: MELSEC CPU type
            project_type: Project type (simple/structured)

        Returns:
            Status dict with result info
        """
        try:
            self.connect_or_launch()
            self.create_new_project(cpu_type, project_type)
            self.import_text_file(file_path)

            return {
                "status": "success",
                "message": "GX Works2에 래더를 자동 Import했습니다. 래더 편집 화면에서 확인하세요.",
                "file_path": file_path,
            }
        except GXWorks2NotFoundError as e:
            return {
                "status": "error",
                "error_type": "not_found",
                "message": str(e),
                "file_path": file_path,
                "fallback": (
                    f"텍스트 파일이 저장되었습니다: {file_path}\n"
                    "수동으로 Import하려면:\n"
                    "[프로젝트] → [읽어들이기] → [텍스트 파일]에서 위 파일을 선택하세요."
                ),
            }
        except (GXWorks2TimeoutError, TimeoutError) as e:
            return {
                "status": "error",
                "error_type": "timeout",
                "message": str(e),
                "file_path": file_path,
                "fallback": (
                    f"GX Works2 자동 Import에 실패했습니다.\n"
                    f"텍스트 파일: {file_path}\n"
                    "수동으로 Import하려면:\n"
                    "[프로젝트] → [읽어들이기] → [텍스트 파일]에서 위 파일을 선택하세요."
                ),
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": "unknown",
                "message": str(e),
                "file_path": file_path,
                "fallback": (
                    f"GX Works2 자동 Import 중 오류가 발생했습니다: {e}\n"
                    f"텍스트 파일: {file_path}\n"
                    "수동으로 Import하려면:\n"
                    "[프로젝트] → [읽어들이기] → [텍스트 파일]에서 위 파일을 선택하세요."
                ),
            }
