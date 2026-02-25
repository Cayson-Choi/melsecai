"""GX Works2 menu path definitions for each supported language."""

from __future__ import annotations

MENU_PATHS: dict[str, dict[str, str]] = {
    "ko": {
        "new_project": "프로젝트(&P)->새로 만들기(&N)",
        "read_text": "프로젝트(&P)->읽어들이기(&I)->텍스트 파일",
        "close_project": "프로젝트(&P)->닫기(&C)",
        "dialog_open_title": "열기",
        "btn_open": "열기(&O)",
        "file_name_label": "파일 이름(&N):",
        "btn_ok": "확인",
        "btn_cancel": "취소",
        "btn_no": "아니오(&N)",
        "btn_yes": "예(&Y)",
        "save_confirm_title": "확인",
    },
    "en": {
        "new_project": "Project(&P)->New(&N)",
        "read_text": "Project(&P)->Read from file(&I)->Text file",
        "close_project": "Project(&P)->Close(&C)",
        "dialog_open_title": "Open",
        "btn_open": "Open(&O)",
        "file_name_label": "File name(&N):",
        "btn_ok": "OK",
        "btn_cancel": "Cancel",
        "btn_no": "No(&N)",
        "btn_yes": "Yes(&Y)",
        "save_confirm_title": "Confirm",
    },
    "ja": {
        "new_project": "プロジェクト(&P)->新規作成(&N)",
        "read_text": "プロジェクト(&P)->読出し(&I)->テキストファイル",
        "close_project": "プロジェクト(&P)->閉じる(&C)",
        "dialog_open_title": "開く",
        "btn_open": "開く(&O)",
        "file_name_label": "ファイル名(&N):",
        "btn_ok": "OK",
        "btn_cancel": "キャンセル",
        "btn_no": "いいえ(&N)",
        "btn_yes": "はい(&Y)",
        "save_confirm_title": "確認",
    },
}

# GX Works2 default install paths to try
DEFAULT_INSTALL_PATHS = [
    r"C:\Program Files (x86)\MELSOFT\GPPW2\GD2.exe",
    r"C:\Program Files\MELSOFT\GPPW2\GD2.exe",
    r"C:\Program Files (x86)\MELSOFT\GX Works2\gxw2.exe",
    r"C:\Program Files\MELSOFT\GX Works2\gxw2.exe",
    r"C:\MELSOFT\GX Works2\gxw2.exe",
]

# CPU type display names for new project dialog
CPU_TYPES = {
    "Q03UDE": "Q03UDE",
    "Q03UD": "Q03UD",
    "Q06UDH": "Q06UDH",
    "Q04UDH": "Q04UDH",
    "Q13UDH": "Q13UDH",
    "Q26UDH": "Q26UDH",
    "QnU": "QnU",
}
