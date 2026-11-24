"""
Filesystem security and workspace isolation policy for LibreSprite Game MCP.
Guards all tool inputs and outputs against path traversal, symlink escapes, and unauthorized writes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional, Union

from libresprite_game_mcp.config import get_default_assets_dir


class WorkspacePolicy:
    """Enforces strict filesystem boundaries on all file reads and writes."""

    def __init__(self, approved_roots: Optional[List[Union[str, Path]]] = None):
        self.approved_roots: List[Path] = []

        if approved_roots:
            for r in approved_roots:
                self.add_approved_root(r)
        else:
            # Default approved roots: Current working directory and default assets directory
            self.add_approved_root(Path.cwd())
            self.add_approved_root(get_default_assets_dir())

        # Check environment variable for extra configured roots
        env_roots = os.environ.get("LIBRESPRITE_WORKSPACE_ROOTS")
        if env_roots:
            sep = ";" if sys.platform == "win32" else ":"
            for r in env_roots.split(sep):
                if r.strip():
                    self.add_approved_root(r.strip())

    def add_approved_root(self, root: Union[str, Path]) -> None:
        """Adds and resolves a directory to the approved roots list."""
        resolved = Path(root).resolve()
        if resolved not in self.approved_roots:
            self.approved_roots.append(resolved)

    def is_path_approved(self, path: Union[str, Path]) -> bool:
        """Checks if a resolved path falls within any approved workspace root."""
        try:
            resolved = Path(path).resolve()
            for root in self.approved_roots:
                try:
                    if resolved == root or resolved.is_relative_to(root):
                        return True
                except AttributeError:
                    # Fallback for Python < 3.9 (should not occur on 3.12, but safe)
                    try:
                        resolved.relative_to(root)
                        return True
                    except ValueError:
                        continue
            return False
        except Exception:
            return False

    def safe_resolve(
        self,
        path: Union[str, Path],
        must_exist: bool = False,
        allow_create_dir: bool = False,
        base_dir: Optional[Path] = None,
    ) -> Path:
        """
        Resolves a path, strictly verifies containment within approved roots,
        and returns the canonical Path object.
        Raises PermissionError if the path escapes approved boundaries.
        """
        p = Path(path)
        if not p.is_absolute():
            base = base_dir if base_dir else Path.cwd()
            p = base / p

        resolved = p.resolve()

        if not self.is_path_approved(resolved):
            roots_str = ", ".join(str(r) for r in self.approved_roots)
            raise PermissionError(
                f"Filesystem access violation: path '{resolved}' escapes approved workspace boundaries. Approved roots: [{roots_str}]"
            )

        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"File not found within workspace: {resolved}")

        if allow_create_dir:
            resolved.mkdir(parents=True, exist_ok=True)

        return resolved


# Default global policy
workspace_policy = WorkspacePolicy()
