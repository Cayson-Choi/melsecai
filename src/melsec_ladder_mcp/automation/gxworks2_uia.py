"""GX Works2 UI automation via pywinauto UIA backend.

Uses UIA (UI Automation) backend to control 32-bit GX Works2
from 64-bit Python. This solves the 32/64-bit mismatch issue
that blocks the win32 backend approach.

Flow (template-free):
1. Launch GX Works2 empty → New Project dialog → select CPU
2. Import IL program via Edit > Read from CSV File
3. Save As new .gxw file

Legacy flow (template):
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

    def _launch_empty(self) -> int:
        """Launch GX Works2 without opening a project file.

        Uses the install_path from config to start GD2.exe directly.
        Returns the PID of the launched process.
        """
        from melsec_ladder_mcp.automation.config import load_config

        cfg = load_config()
        exe_path = cfg["install_path"]

        if not os.path.isfile(exe_path):
            raise GXWorks2UIAError(f"GX Works2 실행 파일을 찾을 수 없습니다: {exe_path}")

        subprocess.Popen([exe_path])

        for _ in range(self._timeouts["launch"]):
            time.sleep(1)
            pid = self._find_gxworks2_pid()
            if pid:
                return pid
        raise GXWorks2UIAError(
            f"GX Works2가 {self._timeouts['launch']}초 내에 시작되지 않았습니다"
        )

    def _create_new_project(
        self,
        series: str = "QCPU (Q mode)",
        cpu_type: str = "Q03UDE",
        project_type: str = "Simple Project",
        language: str = "Ladder",
    ) -> None:
        """Create a new project via Project > New dialog.

        Automates the New Project dialog (4 ComboBoxes):
        - Series ComboBox → select(series)
        - Type ComboBox → select(cpu_type)
        - Project Type ComboBox → select(project_type)
        - Language ComboBox → select(language)
        - Click OK

        Args:
            series: PLC series name (e.g. "QCPU (Q mode)")
            cpu_type: CPU type name (e.g. "Q03UDE", "Q03UDV")
            project_type: Project type (e.g. "Simple Project")
            language: Programming language (e.g. "Ladder")
        """
        from pywinauto import keyboard

        main = self._get_main_window()
        main.set_focus()
        time.sleep(0.5)

        # Open New Project dialog via Ctrl+N
        keyboard.send_keys("^n")
        time.sleep(2)

        # Find the New Project dialog
        new_dlg = None
        for title_pattern in ["New Project", "新規プロジェクト", "새 프로젝트", "New"]:
            try:
                d = main.child_window(
                    title_re=f".*{title_pattern}.*", control_type="Window",
                )
                if d.exists(timeout=2):
                    new_dlg = d
                    break
            except Exception:
                continue

        if new_dlg is None:
            raise GXWorks2UIAError("'New Project' 다이얼로그를 찾을 수 없습니다")

        # Find ComboBox controls — order: Series, Type, Project Type, Language
        combos = new_dlg.descendants(control_type="ComboBox")
        if len(combos) < 4:
            raise GXWorks2UIAError(
                f"New Project 다이얼로그에서 ComboBox 4개를 기대했으나 "
                f"{len(combos)}개 발견"
            )

        # 1) Series ComboBox
        self._select_combo(combos[0], series, "Series")
        time.sleep(1)

        # 2) Type ComboBox — may refresh after series selection
        combos = new_dlg.descendants(control_type="ComboBox")
        self._select_combo(combos[1], cpu_type, "Type")
        time.sleep(0.5)

        # 3) Project Type ComboBox
        self._select_combo(combos[2], project_type, "Project Type")
        time.sleep(0.5)

        # 4) Language ComboBox
        self._select_combo(combos[3], language, "Language")
        time.sleep(0.5)

        # 5) Uncheck "Use Label" checkbox
        try:
            checkboxes = new_dlg.descendants(control_type="CheckBox")
            for cb in checkboxes:
                txt = cb.window_text()
                if "Label" in txt or "ラベル" in txt or "라벨" in txt:
                    if cb.get_toggle_state() == 1:  # checked
                        cb.click_input()
                        time.sleep(0.3)
                        logger.info(f"Unchecked: {txt!r}")
                    break
        except Exception as e:
            logger.warning(f"Use Label 체크박스 해제 실패: {e}")

        # Click OK button
        try:
            ok_btn = new_dlg.child_window(title="OK", control_type="Button")
            if ok_btn.exists(timeout=2):
                ok_btn.click_input()
            else:
                ok_btn = new_dlg.child_window(auto_id="1", control_type="Button")
                ok_btn.click_input()
        except Exception as e:
            raise GXWorks2UIAError(f"New Project OK 버튼 클릭 실패: {e}")

        time.sleep(2)

        # Dismiss any post-creation popups (e.g. language mismatch)
        self._dismiss_popups()
        time.sleep(0.5)

        logger.info(
            f"New project created: series={series}, cpu={cpu_type}, "
            f"project_type={project_type}, language={language}"
        )

    def _select_combo(self, combo, value: str, label: str) -> None:
        """Select a value in a ComboBox with fallback."""
        try:
            combo.select(value)
            logger.info(f"{label} selected: {value}")
        except Exception as e:
            logger.warning(f"{label} 선택 실패 ({value}): {e}")
            self._select_combo_item(combo, value)

    def _select_combo_item(self, combo, target_text: str) -> None:
        """Fallback combo selection by partial text match."""
        try:
            items = combo.texts()
            for item in items:
                if target_text.lower() in item.lower():
                    combo.select(item)
                    return
            # If no partial match, try the first item and warn
            logger.warning(
                f"'{target_text}' not found in combo items: {items}. "
                f"Using current selection."
            )
        except Exception as e:
            logger.warning(f"Combo item selection fallback failed: {e}")

    def _connect(self, pid: int) -> None:
        """Connect to GX Works2 via UIA backend."""
        from pywinauto import Application

        self._app = Application(backend="uia").connect(process=pid)
        self._pid = pid
        logger.info(f"Connected to GX Works2 (PID={pid})")

    def _reconnect(self) -> None:
        """Re-find GX Works2 PID and reconnect.

        After _create_new_project(), popup dismissal can leave pywinauto's
        window references stale. Reconnecting refreshes them.
        """
        pid = self._find_gxworks2_pid()
        if pid is None:
            raise GXWorks2UIAError("GX Works2 프로세스를 찾을 수 없습니다")
        self._connect(pid)

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

        # Strategy 1: Try UIA menu item search
        keyboard.send_keys("%p")  # Alt+P for Project
        time.sleep(1)

        clicked = False
        for d in main.descendants(control_type="MenuItem"):
            txt = d.window_text()
            if txt and ("Save As" in txt or "名前を付けて保存" in txt or "다른 이름" in txt):
                logger.info(f"Found Save As menu item: {txt!r}")
                d.click_input()
                clicked = True
                break

        if not clicked:
            keyboard.send_keys("{ESC}")
            time.sleep(0.3)

            # Strategy 2: Keyboard navigation — Alt+P then arrow down to Save As
            # Typical Project menu order: New, Open, Close, Save, Save As
            keyboard.send_keys("%p")
            time.sleep(0.8)
            for _ in range(10):
                keyboard.send_keys("{DOWN}")
                time.sleep(0.15)
                # Check if a Save As dialog appeared
            keyboard.send_keys("{ESC}")
            time.sleep(0.3)

            # Strategy 3: Direct accelerator — Alt+P, A (if 'A' is Save As accelerator)
            keyboard.send_keys("%p")
            time.sleep(0.8)
            keyboard.send_keys("a")
            time.sleep(1)

        time.sleep(1)

        # Check if a save dialog appeared (try multiple title patterns)
        dialog_found = False
        for title_pattern in ["Save As", "名前を付けて", "다른 이름", "Save"]:
            try:
                dlg = main.child_window(title_re=f".*{title_pattern}.*", control_type="Window")
                if dlg.exists(timeout=2):
                    dialog_found = True
                    break
            except Exception:
                continue

        if not dialog_found:
            # Strategy 4: Try folder browse dialog (GX Works2 uses folder selection for Save As)
            # GX Works2 Save As opens a folder browser, not a standard file dialog
            try:
                dlg = main.child_window(control_type="Window", found_index=0)
                if dlg.exists(timeout=2):
                    dialog_found = True
            except Exception:
                pass

        if not dialog_found:
            raise GXWorks2UIAError("'Save As' 다이얼로그를 열 수 없습니다")

        # Handle save dialog
        self._handle_save_as_dialog(output_path)

        # Handle any overwrite confirmation
        time.sleep(1)
        self._click_dialog_yes(timeout=2)

        time.sleep(self._timeouts["save"])
        logger.info(f"Project saved: {output_path}")

    def _handle_save_as_dialog(self, output_path: str) -> None:
        """Handle GX Works2 Save As dialog.

        GX Works2 uses a folder browser for Save As (project name + location).
        It may also use a standard file dialog depending on version.
        """
        from pywinauto import keyboard

        main = self._get_main_window()

        # Try standard file dialog first (auto_id=1148 for filename)
        try:
            dialog = None
            for title_pattern in ["Save As", "名前を付けて", "다른 이름", "Save"]:
                try:
                    d = main.child_window(title_re=f".*{title_pattern}.*", control_type="Window")
                    if d.exists(timeout=1):
                        dialog = d
                        break
                except Exception:
                    continue

            if dialog is None:
                # Try any child window that appeared
                dialog = main.child_window(control_type="Window", found_index=0)

            # Look for filename edit field
            try:
                filename_edit = dialog.child_window(auto_id="1148", control_type="Edit")
                filename_edit.set_focus()
                time.sleep(0.2)
                keyboard.send_keys("^a")
                time.sleep(0.1)
                keyboard.send_keys(output_path, with_spaces=True)
                time.sleep(0.3)

                # Click Save button (auto_id=1)
                save_btn = dialog.child_window(auto_id="1", control_type="Button")
                save_btn.click_input()
                time.sleep(1)
                return
            except Exception:
                pass

            # GX Works2 folder-based Save As: has a tree view + project name edit
            # Find any Edit control and type the path
            edits = dialog.descendants(control_type="Edit")
            if edits:
                # Use the last edit (usually the project name field)
                project_dir = str(Path(output_path).parent)
                project_name = Path(output_path).stem

                edits[-1].set_focus()
                time.sleep(0.2)
                keyboard.send_keys("^a")
                keyboard.send_keys(project_name, with_spaces=True)
                time.sleep(0.3)

                # Click OK/Save button
                for aid in ("1", "2"):
                    try:
                        btn = dialog.child_window(auto_id=aid, control_type="Button")
                        txt = btn.window_text()
                        if any(k in txt for k in ("OK", "Save", "확인", "저장")):
                            btn.click_input()
                            time.sleep(1)
                            return
                    except Exception:
                        continue

                # Just press Enter as last resort
                keyboard.send_keys("{ENTER}")
                time.sleep(1)

        except Exception as e:
            logger.warning(f"Save As dialog handling failed: {e}")
            raise GXWorks2UIAError(f"Save As 다이얼로그 처리 실패: {e}")

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
        cpu_type: str | None = None,
        series: str = "QCPU (Q mode)",
        template_gxw: str | None = None,
    ) -> str:
        """Full automation flow: import CSV → save as .gxw.

        Supports two modes:
        1. **New Project** (cpu_type given): Launch GX Works2 empty → create
           new project with specified CPU → import CSV → save.
        2. **Template** (legacy, cpu_type=None + template exists): Open template
           .gxw → clear → import CSV → save as.

        If neither cpu_type nor template is provided, falls back to config's
        default_cpu to create a new project.

        Args:
            csv_path: Path to the CSV file with IL instructions.
            output_path: Path for the output .gxw file.
            cpu_type: CPU type for new project (e.g. "Q03UDE", "Q03UDV").
            series: PLC series name (default: "QCPU (Q mode)").
            template_gxw: Path to a template .gxw file (legacy mode).

        Returns:
            Path to the saved .gxw file.
        """
        # Determine mode
        template = template_gxw or self._template_gxw
        use_new_project = cpu_type is not None

        if not use_new_project and template is None:
            # No explicit cpu_type and no template → use config default_cpu
            from melsec_ladder_mcp.automation.config import load_config

            cfg = load_config()
            cpu_type = cfg.get("default_cpu", "Q03UDE")
            use_new_project = True

        # Check if GX Works2 is already running
        existing_pid = self._find_gxworks2_pid()
        if existing_pid:
            logger.info(f"GX Works2 already running (PID={existing_pid}), closing first")
            subprocess.run(["taskkill", "/pid", str(existing_pid)], capture_output=True)
            time.sleep(2)

        if use_new_project:
            # --- New Project mode ---
            pid = self._launch_empty()
            self._connect(pid)
            time.sleep(3)
            self._dismiss_popups()
            time.sleep(0.5)
            self._create_new_project(series=series, cpu_type=cpu_type)
            # Reconnect — popup dismissal inside _create_new_project can
            # leave pywinauto window references stale.
            time.sleep(2)
            self._reconnect()
        else:
            # --- Template mode (legacy) ---
            if template is None:
                template = str(_TEMPLATE_DIR / "template.gxw")
            if not os.path.isfile(template):
                raise GXWorks2UIAError(f"템플릿 파일이 존재하지 않습니다: {template}")
            pid = self._launch_gxw(template)
            self._connect(pid)
            time.sleep(3)
            self._dismiss_popups()
            time.sleep(0.5)
            self._clear_existing_program()

        # Import CSV
        self._import_csv(csv_path)

        # Compile (F4)
        self._convert_ladder()

        # Save As
        self._save_as(output_path)

        return output_path
