"""Dialog handler utilities for GX Works2 automation."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


def dismiss_save_prompt(app, menu: dict, timeout: float = 3.0) -> bool:
    """Dismiss the 'Save changes?' dialog if it appears.

    When creating a new project while one is already open,
    GX Works2 asks whether to save. We click 'No'.

    Returns True if a dialog was dismissed, False otherwise.
    """
    try:
        from pywinauto.timings import TimeoutError as PywinautoTimeout

        try:
            dlg = app.window(title_re=f".*{menu['save_confirm_title']}.*")
            dlg.wait("visible", timeout=timeout)
            # Click 'No' to discard
            no_btn = dlg.child_window(title_re=f".*{menu['btn_no']}.*", control_type="Button")
            if no_btn.exists():
                no_btn.click()
                logger.info("Dismissed save confirmation dialog (clicked No)")
                return True
        except PywinautoTimeout:
            pass
    except Exception as e:
        logger.debug(f"No save dialog to dismiss: {e}")
    return False


def handle_file_dialog(
    app,
    menu: dict,
    file_path: str,
    timeout: float = 5.0,
) -> None:
    """Handle the file open dialog: enter path and click Open.

    Args:
        app: pywinauto Application instance
        menu: Menu path dict for the current language
        file_path: Absolute path to the file to open
        timeout: Max wait time for the dialog to appear
    """
    from pywinauto.timings import TimeoutError as PywinautoTimeout

    # Wait for file dialog
    try:
        file_dialog = app.window(title_re=f".*{menu['dialog_open_title']}.*")
        file_dialog.wait("visible", timeout=timeout)
    except PywinautoTimeout:
        raise TimeoutError(
            f"File dialog did not appear within {timeout}s. "
            f"Expected title containing: {menu['dialog_open_title']}"
        )

    time.sleep(0.5)

    # Type the file path into the file name field
    # Try multiple approaches to find the filename edit box
    edit = None

    # Approach 1: Find by automation ID (common in Windows file dialogs)
    try:
        edit = file_dialog.child_window(title="파일 이름(&N):", control_type="Edit")
        if not edit.exists(timeout=1):
            edit = None
    except Exception:
        edit = None

    # Approach 2: Try English label
    if edit is None:
        try:
            edit = file_dialog.child_window(title="File name:", control_type="Edit")
            if not edit.exists(timeout=1):
                edit = None
        except Exception:
            edit = None

    # Approach 3: Find ComboBox then its Edit child
    if edit is None:
        try:
            combo = file_dialog.child_window(
                title_re=f".*{menu['file_name_label']}.*",
                control_type="ComboBox",
            )
            if combo.exists(timeout=1):
                edit = combo.child_window(control_type="Edit")
        except Exception:
            edit = None

    # Approach 4: Just find any Edit in the dialog
    if edit is None:
        try:
            edits = file_dialog.children(control_type="Edit")
            if edits:
                edit = edits[-1]  # Usually the last Edit is the filename
        except Exception:
            pass

    if edit is None:
        raise RuntimeError("Could not find filename input in file dialog")

    edit.set_text("")
    edit.type_keys(file_path, with_spaces=True)
    time.sleep(0.3)

    # Click Open button
    open_btn = None
    for title_re in [menu["btn_open"], "열기", "Open", "開く"]:
        try:
            btn = file_dialog.child_window(title_re=f".*{title_re}.*", control_type="Button")
            if btn.exists(timeout=1):
                open_btn = btn
                break
        except Exception:
            continue

    if open_btn is None:
        raise RuntimeError("Could not find Open button in file dialog")

    open_btn.click()
    logger.info(f"File dialog: selected '{file_path}' and clicked Open")
