"""GX Works2 UI automation via pywinauto UIA backend.

Uses UIA (UI Automation) backend to control 32-bit GX Works2
from 64-bit Python. This solves the 32/64-bit mismatch issue
that blocks the win32 backend approach.

Flow:
1. Open a template .gxw file in GX Works2
2. Dismiss any popup dialogs (language mismatch, etc.)
3. Import IL program via Edit > Read from CSV File
4. Save As new .gxw file
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Default template .gxw file (empty Q03UDV project)
_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "formats"


class GXWorks2UIAError(Exception):
    """GX Works2 UIA automation error."""


class GXWorks2UIA:
    """GX Works2 controller using pywinauto UIA backend.

    This controller automates GX Works2 to:
    1. Open a template project
    2. Import IL instructions via CSV
    3. Save the resulting .gxw file
    """

    def __init__(
        self,
        template_gxw: str | None = None,
        timeouts: dict | None = None,
    ) -> None:
        self._template_gxw = template_gxw
        self._timeouts = timeouts or {"launch": 15, "dialog": 5, "save": 10}
        self._app = None
        self._pid: int | None = None

    def _find_gxworks2_pid(self) -> int | None:
        """Find running GX Works2 PID."""
        result = subprocess.run(
            ["tasklist", "/fi", "imagename eq GD2.exe"],
            capture_output=True, text=True,
        )
        match = re.search(r"GD2\.exe\s+(\d+)", result.stdout)
        return int(match.group(1)) if match else None

    def _launch_gxw(self, gxw_path: str) -> int:
        """Open a .gxw file and return the GX Works2 PID."""
        os.startfile(gxw_path)
        # Wait for process to start
        for _ in range(self._timeouts["launch"]):
            time.sleep(1)
            pid = self._find_gxworks2_pid()
            if pid:
                return pid
        raise GXWorks2UIAError(
            f"GX Works2가 {self._timeouts['launch']}초 내에 시작되지 않았습니다"
        )

    def _connect(self, pid: int) -> None:
        """Connect to GX Works2 via UIA backend."""
        from pywinauto import Application

        self._app = Application(backend="uia").connect(process=pid)
        self._pid = pid
        logger.info(f"Connected to GX Works2 (PID={pid})")

    def _get_main_window(self):
        """Get the main GX Works2 window."""
        return self._app.top_window()

    def _dismiss_popups(self) -> None:
        """Dismiss any popup dialogs (language mismatch, etc.)."""
        main = self._get_main_window()
        # Try auto_id=2 (OK button in many dialogs)
        try:
            ok_btn = main.child_window(auto_id="2", control_type="Button")
            if ok_btn.exists(timeout=2):
                ok_btn.click_input()
                time.sleep(0.5)
                logger.info("Dismissed popup dialog (auto_id=2)")
                return
        except Exception:
            pass
        # Try MELSOFT dialog with Yes/OK button
        self._click_dialog_yes(timeout=1)

    def _click_dialog_yes(self, timeout: int = 2) -> bool:
        """Find and click Yes/OK in a MELSOFT confirmation dialog.

        Returns True if a dialog was found and a button was clicked.
        """
        main = self._get_main_window()
        try:
            dlg = main.child_window(
                title="MELSOFT Series GX Works2", control_type="Window",
            )
            if not dlg.exists(timeout=timeout):
                return False
            children = dlg.wrapper_object().children()
            # Prefer buttons with specific Yes/OK text patterns
            for c in children:
                if c.element_info.control_type != "Button":
                    continue
                txt = c.window_text()
                # Match: "Yes", "예(Y)", "はい(Y)", "OK", "확인", "Ȯ��"
                if any(k in txt for k in ("Yes", "예", "はい", "OK", "확인")):
                    c.click_input()
                    time.sleep(0.5)
                    logger.info(f"Clicked dialog button: {txt!r}")
                    return True
            # Fallback: click auto_id=6 (Yes) or auto_id=1 (OK)
            for aid in ("6", "1"):
                try:
                    btn = dlg.child_window(auto_id=aid, control_type="Button")
                    if btn.exists(timeout=0):
                        btn.click_input()
                        time.sleep(0.5)
                        logger.info(f"Clicked dialog button auto_id={aid}")
                        return True
                except Exception:
                    pass
        except Exception:
            pass
        return False

    def _clear_existing_program(self) -> None:
        """Select all and delete existing program to start fresh."""
        from pywinauto import keyboard

        main = self._get_main_window()
        main.set_focus()
        time.sleep(0.3)

        # Ctrl+A to select all, then Delete
        keyboard.send_keys("^a")
        time.sleep(0.3)
        keyboard.send_keys("{DELETE}")
        time.sleep(0.3)

        self._click_dialog_yes(timeout=1)

    def _import_csv(self, csv_path: str) -> None:
        """Import a CSV file via Edit > Read from CSV File(J)..."""
        from pywinauto import keyboard

        main = self._get_main_window()
        main.set_focus()
        time.sleep(0.3)

        # Open Edit menu via Alt+E
        keyboard.send_keys("%e")
        time.sleep(0.5)

        # Find and click "Read from CSV File(J)..."
        menus = main.descendants(control_type="Menu")
        clicked = False
        for m in menus:
            if m.window_text() == "Edit":
                items = m.descendants(control_type="MenuItem")
                for item in items:
                    if "CSV" in item.window_text() and "Read" in item.window_text():
                        logger.info(f"Clicking: {item.window_text()}")
                        item.click_input()
                        clicked = True
                        break
                break

        if not clicked:
            keyboard.send_keys("{ESC}")
            raise GXWorks2UIAError("'Read from CSV File' 메뉴를 찾을 수 없습니다")

        time.sleep(1)

        # Handle file open dialog
        self._handle_file_dialog(csv_path, "Read from CSV File")

        time.sleep(1)

        # Handle "Read from the specified file. Are you sure?" confirmation
        self._click_dialog_yes(timeout=3)

        # Wait for import to complete
        time.sleep(3)
        self._dismiss_popups()

    def _handle_file_dialog(self, file_path: str, dialog_title: str) -> None:
        """Handle a file open/save dialog by typing the path and clicking Open/Save."""
        from pywinauto import keyboard

        main = self._get_main_window()

        # Find the dialog
        try:
            dialog = main.child_window(title=dialog_title, control_type="Window")
            if not dialog.exists(timeout=self._timeouts["dialog"]):
                raise GXWorks2UIAError(f"'{dialog_title}' 다이얼로그를 찾을 수 없습니다")
        except Exception:
            # Try broader search
            dialog = main.child_window(title_re=f".*{dialog_title.split()[0]}.*", control_type="Window")
            if not dialog.exists(timeout=self._timeouts["dialog"]):
                raise GXWorks2UIAError(f"파일 다이얼로그를 찾을 수 없습니다")

        # Set the filename - find the Edit control with auto_id 1148
        try:
            filename_edit = dialog.child_window(auto_id="1148", control_type="Edit")
            filename_edit.set_focus()
            time.sleep(0.2)
            keyboard.send_keys("^a")
            time.sleep(0.1)
            # Type the full path
            keyboard.send_keys(file_path, with_spaces=True)
            time.sleep(0.3)
        except Exception as e:
            raise GXWorks2UIAError(f"파일 이름 입력 실패: {e}")

        # Click Open/Save button (auto_id=1)
        try:
            open_btn = dialog.child_window(auto_id="1", control_type="Button")
            open_btn.click_input()
            time.sleep(1)
        except Exception as e:
            raise GXWorks2UIAError(f"열기/저장 버튼 클릭 실패: {e}")

    def _convert_ladder(self) -> None:
        """Press F4 to compile/convert the imported program."""
        from pywinauto import keyboard

        main = self._get_main_window()
        main.set_focus()
        time.sleep(0.3)
        keyboard.send_keys("{F4}")
        time.sleep(2)

        # Dismiss any compilation result dialogs
        self._dismiss_popups()

    def _save_as(self, output_path: str) -> None:
        """Save the project as a new .gxw file via Project > Save As..."""
        from pywinauto import keyboard

        main = self._get_main_window()
        main.set_focus()
        time.sleep(0.3)

        # Ctrl+Shift+S or menu Project > Save As
        keyboard.send_keys("%p")  # Alt+P for Project
        time.sleep(0.5)

        # Find "Save As..." in menu
        menus = main.descendants(control_type="Menu")
        clicked = False
        for m in menus:
            if m.window_text() == "Project":
                items = m.descendants(control_type="MenuItem")
                for item in items:
                    if "Save As" in item.window_text():
                        item.click_input()
                        clicked = True
                        break
                break

        if not clicked:
            keyboard.send_keys("{ESC}")
            raise GXWorks2UIAError("'Save As...' 메뉴를 찾을 수 없습니다")

        time.sleep(1)

        # Handle save dialog
        self._handle_file_dialog(output_path, "Save As")

        # Handle any overwrite confirmation
        time.sleep(1)
        self._click_dialog_yes(timeout=2)

        time.sleep(self._timeouts["save"])
        logger.info(f"Project saved: {output_path}")

    def _save(self) -> None:
        """Save the current project via Ctrl+S."""
        from pywinauto import keyboard

        main = self._get_main_window()
        main.set_focus()
        time.sleep(0.3)
        keyboard.send_keys("^s")
        time.sleep(3)

        # Handle any confirmation dialogs
        self._dismiss_popups()

    def build_gxw(
        self,
        csv_path: str,
        output_path: str,
        template_gxw: str | None = None,
    ) -> str:
        """Full automation flow: template → import CSV → save as .gxw.

        Args:
            csv_path: Path to the CSV file with IL instructions.
            output_path: Path for the output .gxw file.
            template_gxw: Path to the template .gxw file to use.

        Returns:
            Path to the saved .gxw file.
        """
        template = template_gxw or self._template_gxw
        if template is None:
            template = str(_TEMPLATE_DIR / "template.gxw")

        if not os.path.isfile(template):
            raise GXWorks2UIAError(f"템플릿 파일이 존재하지 않습니다: {template}")

        # Check if GX Works2 is already running
        existing_pid = self._find_gxworks2_pid()
        if existing_pid:
            logger.info(f"GX Works2 already running (PID={existing_pid}), closing first")
            # Close existing instance
            subprocess.run(["taskkill", "/pid", str(existing_pid)], capture_output=True)
            time.sleep(2)

        # Launch GX Works2 with template
        pid = self._launch_gxw(template)
        self._connect(pid)

        # Wait for UI to stabilize
        time.sleep(3)

        # Dismiss popups
        self._dismiss_popups()
        time.sleep(0.5)

        # Clear existing program
        self._clear_existing_program()

        # Import CSV
        self._import_csv(csv_path)

        # Compile (F4)
        self._convert_ladder()

        # Save As
        self._save_as(output_path)

        return output_path
