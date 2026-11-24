"""
Curated retro game palettes and color manipulation utilities for pixel art.
Includes PICO-8, Game Boy, NES, DB16, DB32, EDG32, Sweetie16, and GPL file loading.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union

# RGBA tuple format: (r, g, b, a) where r,g,b,a in 0..255
RGBA = Tuple[int, int, int, int]
RGB = Tuple[int, int, int]


def hex_to_rgba(hex_str: str, alpha: int = 255) -> RGBA:
    """Converts hex code (#RGB, #RGBA, #RRGGBB, #RRGGBBAA) to RGBA tuple."""
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 3:
        r = int(hex_clean[0] * 2, 16)
        g = int(hex_clean[1] * 2, 16)
        b = int(hex_clean[2] * 2, 16)
        return (r, g, b, alpha)
    elif len(hex_clean) == 4:
        r = int(hex_clean[0] * 2, 16)
        g = int(hex_clean[1] * 2, 16)
        b = int(hex_clean[2] * 2, 16)
        a = int(hex_clean[3] * 2, 16)
        return (r, g, b, a)
    elif len(hex_clean) == 6:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        return (r, g, b, alpha)
    elif len(hex_clean) == 8:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        a = int(hex_clean[6:8], 16)
        return (r, g, b, a)
    raise ValueError(f"Invalid hex color format: {hex_str}")


def rgba_to_hex(color: Union[RGBA, RGB]) -> str:
    """Converts RGBA or RGB tuple to #RRGGBBAA or #RRGGBB hex string."""
    if len(color) == 4:
        r, g, b, a = color
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"
    r, g, b = color
    return f"#{r:02x}{g:02x}{b:02x}"


# Standard Game Palettes (hex representation)
BUILTIN_PALETTES: Dict[str, List[str]] = {
    "pico-8": [
        "#000000", "#1D2B53", "#7E2553", "#008751",
        "#AB5236", "#5F574F", "#C2C3C7", "#FFF1E8",
        "#FF004D", "#FFA300", "#FFEC27", "#00E436",
        "#29ADFF", "#83769C", "#FF77A8", "#FFCCAA",
    ],
    "gameboy": [
        "#0f380f", "#306230", "#8bac0f", "#9bbc0f",
    ],
    "gameboy-pocket": [
        "#282828", "#525252", "#8e8e8e", "#e0e0e0",
    ],
    "db16": [  # DawnBringer 16
        "#140c1c", "#442434", "#30346d", "#4e4a4e",
        "#854c30", "#346524", "#d04648", "#757161",
        "#597dce", "#d27d2c", "#8595a1", "#6daa2c",
        "#d2aa99", "#6dc2ca", "#dad45e", "#deeed6",
    ],
    "db32": [  # DawnBringer 32
        "#000000", "#222034", "#45283c", "#663931",
        "#8f563b", "#df7126", "#d9a066", "#eec39a",
        "#fbf236", "#99e550", "#6abe30", "#37946e",
        "#4b692f", "#524b24", "#323c39", "#3f3f74",
        "#306082", "#5b6ee1", "#639bff", "#5fcde4",
        "#cbdbfc", "#ffffff", "#9badb7", "#847e87",
        "#696a6a", "#595652", "#76428a", "#ac3232",
        "#d95763", "#d77643", "#63c74d", "#fee761",
    ],
    "endesga-32": [  # EDG 32
        "#be4a2f", "#d77643", "#ead4aa", "#e4a672",
        "#b86f50", "#733e39", "#3e2731", "#a22633",
        "#e43b44", "#f77622", "#feae34", "#fee761",
        "#63c74d", "#3e8948", "#265c42", "#193c3e",
        "#124e89", "#0099db", "#2ce8f5", "#ffffff",
        "#c0cbdc", "#8b9bb4", "#5a6988", "#3a4466",
        "#262b44", "#181425", "#ff0044", "#68386c",
        "#b55088", "#f6757a", "#e8b796", "#c28569",
    ],
    "sweetie-16": [
        "#1a1c2b", "#57294b", "#9b2242", "#ea443a",
        "#f69e46", "#fbe159", "#89e658", "#3db856",
        "#1d6f54", "#193345", "#24608c", "#47a3e0",
        "#95e8fb", "#ffffff", "#939ab7", "#444a6b",
    ],
    "cyberpunk": [
        "#0d0221", "#0f084b", "#26408b", "#a6cfd5",
        "#c2e7d9", "#05d9e8", "#005678", "#01012b",
        "#ff2a6d", "#d1f7ff", "#05ffa1", "#b967ff",
    ],
    "monochrome": [
        "#000000", "#ffffff",
    ],
}


class GamePalette:
    """Represents a pixel art color palette with color matching & ramping."""

    def __init__(self, name: str, colors: List[RGBA]):
        self.name = name
        self.colors = colors

    @classmethod
    def from_hex_list(cls, name: str, hex_list: List[str]) -> "GamePalette":
        colors = [hex_to_rgba(h) for h in hex_list]
        return cls(name, colors)

    @classmethod
    def from_name(cls, name: str) -> "GamePalette":
        clean_name = name.lower().strip()
        if clean_name not in BUILTIN_PALETTES:
            available = ", ".join(BUILTIN_PALETTES.keys())
            raise ValueError(f"Unknown palette '{name}'. Available: {available}")
        return cls.from_hex_list(clean_name, BUILTIN_PALETTES[clean_name])

    @classmethod
    def from_gpl_file(cls, path: Union[str, Path]) -> "GamePalette":
        """Loads a GIMP/LibreSprite .gpl palette file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"GPL file not found: {file_path}")

        colors: List[RGBA] = []
        name = file_path.stem
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        data_started = False
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("GIMP Palette"):
                continue
            if line.lower().startswith("name:"):
                name = line.split(":", 1)[1].strip()
                continue
            if line.lower().startswith("columns:") or line.lower().startswith("channels:"):
                continue

            # Color line: R G B [Name]
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                colors.append((r, g, b, 255))

        return cls(name, colors)

    def to_hex_list(self) -> List[str]:
        return [rgba_to_hex(c) for c in self.colors]

    def find_nearest_color(self, target: RGBA) -> RGBA:
        """Finds the nearest color in the palette using weighted Euclidean distance."""
        if target[3] == 0:
            return (0, 0, 0, 0)

        tr, tg, tb, ta = target
        best_color = self.colors[0]
        min_dist = float("inf")

        for r, g, b, a in self.colors:
            # Human perception weights: Red 0.30, Green 0.59, Blue 0.11
            dr = tr - r
            dg = tg - g
            db = tb - b
            dist = 0.30 * (dr * dr) + 0.59 * (dg * dg) + 0.11 * (db * db)
            if dist < min_dist:
                min_dist = dist
                best_color = (r, g, b, ta)

        return best_color

    def export_gpl(self, output_path: Union[str, Path]) -> Path:
        """Exports the palette to standard GIMP .gpl format for LibreSprite."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"GIMP Palette\nName: {self.name}\nColumns: 8\n#\n")
            for c in self.colors:
                r, g, b, _ = c
                f.write(f"{r:3d} {g:3d} {b:3d}\t{rgba_to_hex((r, g, b))}\n")
        return out


def list_builtin_palettes() -> Dict[str, int]:
    """Returns a dictionary of all available built-in palettes and color counts."""
    return {name: len(colors) for name, colors in BUILTIN_PALETTES.items()}
