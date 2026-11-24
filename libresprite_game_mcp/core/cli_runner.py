"""
LibreSprite CLI batch runner. Wraps headless commands for exporting sprite sheets,
scaling assets, running batch automation scripts, and compiling textures.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

from libresprite_game_mcp.config import find_libresprite_executable


class LibreSpriteCLI:
    """Wrapper around LibreSprite's batch CLI."""

    def __init__(self, exe_path: Optional[str] = None):
        self.exe_path = exe_path or find_libresprite_executable()

    def is_available(self) -> bool:
        return bool(self.exe_path and Path(self.exe_path).is_file())

    def run_command(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Runs a command against LibreSprite binary."""
        if not self.is_available():
            raise FileNotFoundError(
                "LibreSprite executable not found. Please set LIBRESPRITE_EXE environment variable."
            )

        cmd = [self.exe_path] + args
        # On Windows, run with shell=False or creationflags to prevent GUI popups
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc

    def get_version(self) -> str:
        """Returns the version string of LibreSprite."""
        proc = self.run_command(["--version"])
        out = proc.stdout.strip() or proc.stderr.strip()
        return out or "LibreSprite (detected)"

    def export_sprite_sheet(
        self,
        input_file: Union[str, Path],
        sheet_png: Union[str, Path],
        data_json: Optional[Union[str, Path]] = None,
        sheet_type: str = "packed",
        border_padding: int = 1,
        shape_padding: int = 1,
        inner_padding: int = 0,
        trim: bool = False,
        scale: int = 1,
        format_type: str = "json-hash",
        frame_tag: Optional[str] = None,
        split_layers: bool = False,
        list_tags: bool = True,
        list_layers: bool = True,
    ) -> Dict[str, Union[str, int]]:
        """
        Executes a headless sprite sheet compilation via LibreSprite.
        Produces game-engine-ready texture atlas and json metadata.
        """
        input_p = Path(input_file).resolve()
        sheet_p = Path(sheet_png).resolve()
        sheet_p.parent.mkdir(parents=True, exist_ok=True)

        args = ["-b", str(input_p)]

        if scale > 1:
            args += ["--scale", str(scale)]

        if trim:
            args.append("--trim")

        if border_padding > 0:
            args += ["--border-padding", str(border_padding)]
        if shape_padding > 0:
            args += ["--shape-padding", str(shape_padding)]
        if inner_padding > 0:
            args += ["--inner-padding", str(inner_padding)]

        if sheet_type == "packed":
            args.append("--sheet-pack")
        else:
            args += ["--sheet-type", sheet_type]

        if split_layers:
            args.append("--split-layers")

        if frame_tag:
            args += ["--frame-tag", frame_tag]

        if list_tags:
            args.append("--list-tags")
        if list_layers:
            args.append("--list-layers")

        args += ["--sheet", str(sheet_p)]

        data_p = None
        if data_json:
            data_p = Path(data_json).resolve()
            data_p.parent.mkdir(parents=True, exist_ok=True)
            args += ["--data", str(data_p), "--format", format_type]

        proc = self.run_command(args, timeout=60)
        if proc.returncode != 0:
            raise RuntimeError(f"LibreSprite export failed: {proc.stderr or proc.stdout}")

        return {
            "status": "success",
            "sheet_path": str(sheet_p),
            "data_path": str(data_p) if data_p else "",
            "returncode": proc.returncode,
        }

    def execute_script(self, script_path: Union[str, Path], timeout: int = 30) -> str:
        """Executes a JavaScript script headlessly in LibreSprite."""
        sp = Path(script_path).resolve()
        if not sp.exists():
            raise FileNotFoundError(f"Script not found: {sp}")

        proc = self.run_command(["-b", "--script", str(sp)], timeout=timeout)
        return proc.stdout + "\n" + proc.stderr
