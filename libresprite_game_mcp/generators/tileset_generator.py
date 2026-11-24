"""
Pixel art tileset generator for 2D platformers and top-down RPGs.
Generates 3x3 Autotile sets (corners, edges, center, island) with
palettes, textures, and engine-ready tile metadata.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple
from PIL import Image

from libresprite_game_mcp.core.palettes import RGBA, hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas
from libresprite_game_mcp.core.aseprite_file import AsepriteProject


class TilesetTheme:
    """Color theme for tileset generation."""

    def __init__(
        self,
        name: str,
        surface_primary: str,
        surface_highlight: str,
        surface_shadow: str,
        base_primary: str,
        base_shadow: str,
        outline: str,
    ):
        self.name = name
        self.surface_primary = hex_to_rgba(surface_primary)
        self.surface_highlight = hex_to_rgba(surface_highlight)
        self.surface_shadow = hex_to_rgba(surface_shadow)
        self.base_primary = hex_to_rgba(base_primary)
        self.base_shadow = hex_to_rgba(base_shadow)
        self.outline = hex_to_rgba(outline)


DEFAULT_THEMES = {
    "grass_dirt": TilesetTheme(
        name="grass_dirt",
        surface_primary="#6daa2c",
        surface_highlight="#dad45e",
        surface_shadow="#346524",
        base_primary="#854c30",
        base_shadow="#442434",
        outline="#140c1c",
    ),
    "stone_dungeon": TilesetTheme(
        name="stone_dungeon",
        surface_primary="#8595a1",
        surface_highlight="#deeed6",
        surface_shadow="#4e4a4e",
        base_primary="#4e4a4e",
        base_shadow="#30346d",
        outline="#140c1c",
    ),
    "wood_planks": TilesetTheme(
        name="wood_planks",
        surface_primary="#d27d2c",
        surface_highlight="#d2aa99",
        surface_shadow="#854c30",
        base_primary="#854c30",
        base_shadow="#442434",
        outline="#140c1c",
    ),
}


def draw_autotile_cell(
    tile_size: int,
    theme: TilesetTheme,
    tile_type: str,  # 'top-left', 'top', 'top-right', 'left', 'center', 'right', 'bottom-left', 'bottom', 'bottom-right', 'island'
) -> Image.Image:
    """Draws an individual tile for a 3x3 autotile grid."""
    canvas = PixelCanvas(tile_size, tile_size)
    rng = random.Random(hash(tile_type) & 0xFFFFFF)

    is_top = "top" in tile_type or tile_type == "island"
    is_bottom = "bottom" in tile_type or tile_type == "island"
    is_left = "left" in tile_type or tile_type == "island"
    is_right = "right" in tile_type or tile_type == "island"
    is_center = tile_type == "center"

    # Fill base with main dirt/stone
    canvas.draw_rect(0, 0, tile_size, tile_size, fill=theme.base_primary)

    # Add procedural texture noise to base
    for y in range(tile_size):
        for x in range(tile_size):
            if rng.random() < 0.15:
                canvas.put_pixel(x, y, theme.base_shadow)

    # If it has a top surface (e.g. grass canopy)
    if is_top:
        fringe_height = max(3, tile_size // 4)
        for y in range(fringe_height):
            for x in range(tile_size):
                canvas.put_pixel(x, y, theme.surface_primary)
        # Highlight on top edge
        for x in range(tile_size):
            canvas.put_pixel(x, 0, theme.surface_highlight)
        # Grass overhang blades
        for x in range(tile_size):
            blade_len = rng.randint(0, 2)
            for dy in range(blade_len):
                canvas.put_pixel(x, fringe_height + dy, theme.surface_shadow)

    # Outlines for outer borders
    if is_top:
        canvas.draw_line(0, 0, tile_size - 1, 0, theme.outline)
    if is_bottom:
        canvas.draw_line(0, tile_size - 1, tile_size - 1, tile_size - 1, theme.outline)
    if is_left:
        canvas.draw_line(0, 0, 0, tile_size - 1, theme.outline)
    if is_right:
        canvas.draw_line(tile_size - 1, 0, tile_size - 1, tile_size - 1, theme.outline)

    # Center tile gets subtle stone mortar / brick accents
    if is_center:
        mid = tile_size // 2
        canvas.draw_line(2, mid, tile_size - 3, mid, theme.base_shadow)

    return canvas.image


def build_autotile_3x3_sheet(
    tile_size: int = 16,
    theme_name: str = "grass_dirt",
) -> Tuple[Image.Image, Dict]:
    """
    Constructs a 3x3 (+ island) autotile sheet.
    Total layout: 4 columns x 3 rows.
    Returns: (composite_image, tile_metadata)
    """
    theme = DEFAULT_THEMES.get(theme_name, DEFAULT_THEMES["grass_dirt"])

    # 4 columns, 3 rows
    # Col 0..2: 3x3 box
    # Col 3: Island (top), Single pillar (mid), Single floor (bot)
    sheet_w = tile_size * 4
    sheet_h = tile_size * 3
    composite = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))

    grid = [
        ["top-left", "top", "top-right", "island"],
        ["left", "center", "right", "island"],
        ["bottom-left", "bottom", "bottom-right", "island"],
    ]

    metadata = {
        "tile_size": tile_size,
        "columns": 4,
        "rows": 3,
        "theme": theme_name,
        "tiles": [],
    }

    for row_idx, row in enumerate(grid):
        for col_idx, tile_type in enumerate(row):
            tile_img = draw_autotile_cell(tile_size, theme, tile_type)
            x_pos = col_idx * tile_size
            y_pos = row_idx * tile_size
            composite.paste(tile_img, (x_pos, y_pos))

            metadata["tiles"].append({
                "type": tile_type,
                "x": x_pos,
                "y": y_pos,
                "col": col_idx,
                "row": row_idx,
                "solid": True,
            })

    return composite, metadata
