"""
Pixel art game items, weapons, potions, icons, and animated props generator.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional
from PIL import Image

from libresprite_game_mcp.core.palettes import RGBA, hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas
from libresprite_game_mcp.core.aseprite_file import AsepriteProject


def generate_sword_icon(size: int = 16) -> Image.Image:
    """Generates a crisp diagonal RPG sword icon."""
    canvas = PixelCanvas(size, size)
    scale = max(1, size // 16)

    blade = hex_to_rgba("#8595a1")
    blade_highlight = hex_to_rgba("#deeed6")
    hilt = hex_to_rgba("#d27d2c")
    gem = hex_to_rgba("#d04648")
    outline = hex_to_rgba("#140c1c")

    # Diagonal blade from bottom-left towards top-right
    # Pommel & Grip: (2, size-3) to (5, size-6)
    for i in range(2, 6):
        canvas.put_pixel(i * scale, (size - 1 - i) * scale, hilt)

    # Crossguard (perpendicular):
    gx = 5 * scale
    gy = (size - 6) * scale
    canvas.put_pixel(gx - scale, gy - scale, hilt)
    canvas.put_pixel(gx, gy, gem)
    canvas.put_pixel(gx + scale, gy + scale, hilt)

    # Blade: (6, size-7) to (size-3, 2)
    for i in range(6, size - 2):
        bx = i * scale
        by = (size - 1 - i) * scale
        canvas.put_pixel(bx, by, blade)
        canvas.put_pixel(bx, by - scale, blade_highlight)

    # Tip
    canvas.put_pixel((size - 2) * scale, 1 * scale, blade_highlight)

    canvas.add_outline(outline)
    return canvas.image


def generate_potion_icon(
    size: int = 16,
    potion_type: str = "health"  # "health" (red), "mana" (blue), "stamina" (green), "elixir" (gold)
) -> Image.Image:
    """Generates a rounded glass potion flask with liquid and glass highlight."""
    canvas = PixelCanvas(size, size)
    scale = max(1, size // 16)
    mid_x = size // 2

    # Liquid color theme
    colors = {
        "health": (hex_to_rgba("#d04648"), hex_to_rgba("#f6757a")),
        "mana": (hex_to_rgba("#597dce"), hex_to_rgba("#6dc2ca")),
        "stamina": (hex_to_rgba("#6daa2c"), hex_to_rgba("#dad45e")),
        "elixir": (hex_to_rgba("#d27d2c"), hex_to_rgba("#fee761")),
    }
    liquid_main, liquid_light = colors.get(potion_type, colors["health"])
    glass_rim = hex_to_rgba("#deeed6")
    cork = hex_to_rgba("#854c30")
    outline = hex_to_rgba("#140c1c")

    # 1. Cork stopper
    canvas.draw_rect(mid_x - 1 * scale, 2 * scale, 2 * scale, 2 * scale, fill=cork)

    # 2. Flask Neck
    canvas.draw_rect(mid_x - 1 * scale, 4 * scale, 2 * scale, 3 * scale, fill=glass_rim)

    # 3. Round Flask Body (ellipse)
    flask_r = 4 * scale
    flask_cy = 10 * scale
    canvas.draw_circle(mid_x, flask_cy, flask_r, fill=liquid_main)

    # 4. Liquid surface & bubbles
    canvas.draw_line(mid_x - 3 * scale, flask_cy - 1 * scale, mid_x + 3 * scale, flask_cy - 1 * scale, liquid_light)
    canvas.put_pixel(mid_x - 1 * scale, flask_cy + 1 * scale, liquid_light)
    canvas.put_pixel(mid_x + 1 * scale, flask_cy + 2 * scale, liquid_light)

    # 5. Glass highlight curve (top-left reflection)
    canvas.put_pixel(mid_x - 2 * scale, flask_cy - 2 * scale, (255, 255, 255, 220))
    canvas.put_pixel(mid_x - 3 * scale, flask_cy - 1 * scale, (255, 255, 255, 220))

    canvas.add_outline(outline)
    return canvas.image


def build_animated_torch_project(size: int = 16) -> AsepriteProject:
    """Builds a 4-frame animated dungeon wall torch with dancing flame."""
    project = AsepriteProject(size, size)
    scale = max(1, size // 16)
    mid_x = size // 2

    wood = hex_to_rgba("#854c30")
    metal = hex_to_rgba("#4e4a4e")
    outline = hex_to_rgba("#140c1c")
    fire_core = hex_to_rgba("#fff1e8")
    fire_yellow = hex_to_rgba("#fee761")
    fire_orange = hex_to_rgba("#f77622")
    fire_red = hex_to_rgba("#e43b44")

    # 4 flame shapes for animation
    flame_offsets = [
        [(0, 0), (-1, -1), (0, -2), (1, -1)],
        [(-1, 0), (0, -1), (1, -2), (0, -3)],
        [(1, 0), (0, -1), (-1, -2), (0, -3)],
        [(0, 0), (1, -1), (0, -2), (-1, -1)],
    ]

    for frame_idx, offsets in enumerate(flame_offsets):
        canvas = PixelCanvas(size, size)

        # Torch Wood Handle & Wall Sconce
        canvas.draw_rect(mid_x - 1 * scale, 9 * scale, 2 * scale, 6 * scale, fill=wood)
        # Metal bracket ring
        canvas.draw_rect(mid_x - 2 * scale, 8 * scale, 4 * scale, 2 * scale, fill=metal)

        # Dancing Flame (layered: Red base -> Orange mid -> Yellow core -> White spark)
        flame_base_y = 7 * scale
        canvas.draw_circle(mid_x, flame_base_y - 1 * scale, 3 * scale, fill=fire_red)
        canvas.draw_circle(mid_x + offsets[0][0], flame_base_y - 2 * scale, 2 * scale, fill=fire_orange)
        canvas.draw_circle(mid_x + offsets[1][0], flame_base_y - 3 * scale, 1 * scale, fill=fire_yellow)
        canvas.put_pixel(mid_x + offsets[2][0], flame_base_y - 4 * scale, fire_core)

        canvas.add_outline(outline)

        project.add_animation_frame(duration_ms=100, layer_images={"Torch": canvas.image})

    project.add_tag("burn", 0, 3)
    return project


def build_animated_coin_project(size: int = 16) -> AsepriteProject:
    """Builds a 4-frame spinning gold coin animation."""
    project = AsepriteProject(size, size)
    scale = max(1, size // 16)
    mid_x = size // 2
    cy = size // 2

    gold_base = hex_to_rgba("#df7126")
    gold_mid = hex_to_rgba("#fbf236")
    gold_high = hex_to_rgba("#ffffff")
    outline = hex_to_rgba("#524b24")

    # 4 rotation frames: Full face (rx=4), 3/4 turn (rx=3), edge-on (rx=1), 3/4 turn (rx=3)
    widths = [4, 3, 1, 3]

    for f_idx, rx in enumerate(widths):
        canvas = PixelCanvas(size, size)
        rx_scaled = rx * scale
        ry_scaled = 4 * scale

        # Coin rim
        canvas.draw.ellipse(
            [mid_x - rx_scaled, cy - ry_scaled, mid_x + rx_scaled, cy + ry_scaled],
            fill=gold_base, outline=outline
        )
        # Inner surface
        if rx_scaled > 1:
            canvas.draw.ellipse(
                [mid_x - rx_scaled + 1, cy - ry_scaled + 1, mid_x + rx_scaled - 1, cy + ry_scaled - 1],
                fill=gold_mid
            )
            # Sparkle highlight
            canvas.put_pixel(mid_x - rx_scaled + 1, cy - 1, gold_high)

        project.add_animation_frame(duration_ms=100, layer_images={"Coin": canvas.image})

    project.add_tag("spin", 0, 3)
    return project
