"""GX Works2 configuration loader."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


# Default config path: project_root/config/gxworks2_config.yaml
_CONFIG_SEARCH_PATHS = [
    Path(__file__).resolve().parents[3] / "config" / "gxworks2_config.yaml",
    Path("config") / "gxworks2_config.yaml",
]

_DEFAULTS = {
    "install_path": r"C:\Program Files (x86)\MELSOFT\GPPW2\GD2.exe",
    "language": "ko",
    "default_cpu": "Q03UDE",
    "default_project_type": "simple",
    "output_dir": r"D:\Antigravity\melsecai\melseccode",
    "encoding": "shift-jis",
    "after_import": {"auto_convert": True, "focus_ladder": True},
    "timeouts": {"launch": 10, "dialog": 5, "import_wait": 10},
}


def load_config(config_path: str | None = None) -> dict:
    """Load GX Works2 config, falling back to defaults."""
    cfg = dict(_DEFAULTS)

    # Try to load from file
    path = None
    if config_path and os.path.isfile(config_path):
        path = config_path
    else:
        for p in _CONFIG_SEARCH_PATHS:
            if p.is_file():
                path = str(p)
                break

    if path:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data and "gxworks2" in data:
            gx = data["gxworks2"]
            for key in _DEFAULTS:
                if key in gx and gx[key] is not None:
                    cfg[key] = gx[key]

    return cfg
