"""
Configuration and system detection for LibreSprite Game MCP.
"""

from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path
from typing import Optional

DEFAULT_PORT = 64823

# Known installation candidates on Windows / macOS / Linux
CANDIDATE_PATHS = [
    # User's known installation path
    r"E:\course\04_Learning_Career\pixel_art\libresprite-development-windows-x86_64\libresprite.exe",
    r"C:\Program Files\LibreSprite\libresprite.exe",
    r"C:\Program Files (x86)\LibreSprite\libresprite.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\LibreSprite\libresprite.exe"),
    os.path.expandvars(r"%APPDATA%\LibreSprite\libresprite.exe"),
    # Linux / macOS
    "/usr/bin/libresprite",
    "/usr/local/bin/libresprite",
    "/Applications/LibreSprite.app/Contents/MacOS/libresprite",
    "libresprite",
]


def find_libresprite_executable() -> Optional[str]:
    """Finds the LibreSprite binary executable path."""
    # Check environment variable first
    env_path = os.environ.get("LIBRESPRITE_EXE")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Check candidates
    for cand in CANDIDATE_PATHS:
        if os.path.isfile(cand):
            return str(Path(cand).resolve())

    # Check PATH
    which_path = shutil.which("libresprite") or shutil.which("libresprite.exe")
    if which_path:
        return str(Path(which_path).resolve())

    return None


def get_libresprite_scripts_dir() -> Path:
    """Returns the platform-specific scripts directory for LibreSprite."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            scripts_dir = Path(appdata) / "LibreSprite" / "scripts"
        else:
            scripts_dir = Path.home() / "AppData" / "Roaming" / "LibreSprite" / "scripts"
    elif sys.platform == "darwin":
        scripts_dir = Path.home() / "Library" / "Application Support" / "LibreSprite" / "scripts"
    else:
        scripts_dir = Path.home() / ".config" / "libresprite" / "scripts"

    scripts_dir.mkdir(parents=True, exist_ok=True)
    return scripts_dir


def get_default_assets_dir() -> Path:
    """Returns default folder for exported assets."""
    assets_dir = Path.cwd() / "game_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    return assets_dir
