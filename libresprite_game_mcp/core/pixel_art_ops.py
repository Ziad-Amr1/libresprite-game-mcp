"""
Pixel art drawing primitives, symmetry, dithering, outlines, and color transformations.
"""

from __future__ import annotations

from typing import List, Tuple, Optional, Union
from PIL import Image, ImageDraw

from libresprite_game_mcp.core.palettes import RGBA, GamePalette, hex_to_rgba

# 2x2 Bayer Dither Matrix
BAYER_2X2 = [
    [0, 2],
    [3, 1]
]

# 4x4 Bayer Dither Matrix
BAYER_4X4 = [
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5]
]


class PixelCanvas:
    """A 2D pixel art canvas with drawing primitives, layers, and effects."""

    def __init__(self, width: int, height: int, bg_color: Optional[RGBA] = None):
        self.width = width
        self.height = height
        self.image = Image.new("RGBA", (width, height), bg_color or (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

    @classmethod
    def from_image(cls, img: Image.Image) -> "PixelCanvas":
        canvas = cls(img.width, img.height)
        canvas.image = img.convert("RGBA")
        canvas.draw = ImageDraw.Draw(canvas.image)
        return canvas

    def get_pixel(self, x: int, y: int) -> RGBA:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.image.getpixel((x, y))
        return (0, 0, 0, 0)

    def put_pixel(self, x: int, y: int, color: RGBA) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.image.putpixel((x, y), color)

    def put_pixel_symmetric(self, x: int, y: int, color: RGBA, axis_x: Optional[int] = None) -> None:
        """Puts a pixel and its horizontal mirror reflection."""
        self.put_pixel(x, y, color)
        if axis_x is None:
            axis_x = self.width // 2
        mirror_x = (2 * axis_x - 1) - x if self.width % 2 == 0 else (2 * axis_x) - x
        self.put_pixel(mirror_x, y, color)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: RGBA) -> None:
        """Draws a clean 1-pixel line using Bresenham's algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        curr_x, curr_y = x0, y0
        while True:
            self.put_pixel(curr_x, curr_y, color)
            if curr_x == x1 and curr_y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                curr_x += sx
            if e2 < dx:
                err += dx
                curr_y += sy

    def draw_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        fill: Optional[RGBA] = None,
        outline: Optional[RGBA] = None
    ) -> None:
        """Draws a rectangle with optional fill and 1px outline."""
        x1 = x + w - 1
        y1 = y + h - 1
        if fill is not None:
            self.draw.rectangle([x, y, x1, y1], fill=fill)
        if outline is not None:
            self.draw.rectangle([x, y, x1, y1], outline=outline)

    def draw_circle(
        self,
        cx: int,
        cy: int,
        radius: int,
        fill: Optional[RGBA] = None,
        outline: Optional[RGBA] = None
    ) -> None:
        """Draws a circle using Midpoint circle algorithm."""
        bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
        if fill is not None:
            self.draw.ellipse(bbox, fill=fill)
        if outline is not None:
            self.draw.ellipse(bbox, outline=outline)

    def flood_fill(self, x: int, y: int, fill_color: RGBA) -> None:
        """Performs flood fill from (x, y)."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        target_color = self.get_pixel(x, y)
        if target_color == fill_color:
            return

        queue = [(x, y)]
        visited = set()

        while queue:
            cx, cy = queue.pop(0)
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))

            if self.get_pixel(cx, cy) == target_color:
                self.put_pixel(cx, cy, fill_color)
                for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                    if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                        queue.append((nx, ny))

    def add_outline(self, outline_color: RGBA = (0, 0, 0, 255), diagonal: bool = False) -> None:
        """Adds a pixel-art outline around non-transparent pixels."""
        new_img = self.image.copy()
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            offsets += [(-1, -1), (1, -1), (-1, 1), (1, 1)]

        for y in range(self.height):
            for x in range(self.width):
                px = self.get_pixel(x, y)
                if px[3] == 0:  # transparent pixel
                    # check if any neighbor is opaque
                    has_opaque_neighbor = False
                    for dx, dy in offsets:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            neighbor = self.get_pixel(nx, ny)
                            if neighbor[3] > 0:
                                has_opaque_neighbor = True
                                break
                    if has_opaque_neighbor:
                        new_img.putpixel((x, y), outline_color)

        self.image = new_img
        self.draw = ImageDraw.Draw(self.image)

    def add_drop_shadow(self, shadow_color: RGBA = (0, 0, 0, 100), offset_y: int = 1) -> None:
        """Adds a subtle ground drop shadow at the base."""
        # Find lowest opaque pixels bounding box
        min_x, max_x = self.width, 0
        max_y = 0
        found = False
        for y in range(self.height):
            for x in range(self.width):
                if self.get_pixel(x, y)[3] > 0:
                    found = True
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if not found or max_y + offset_y >= self.height:
            return

        cx = (min_x + max_x) // 2
        rx = max(2, (max_x - min_x) // 2)
        sy = min(self.height - 2, max_y + offset_y)
        self.draw.ellipse([cx - rx, sy - 1, cx + rx, sy + 1], fill=shadow_color)

    def apply_dither_pattern(
        self,
        rect: Tuple[int, int, int, int],
        color_a: RGBA,
        color_b: RGBA,
        threshold: float = 0.5
    ) -> None:
        """Fills a rectangular region with 2x2 Bayer dithering between two colors."""
        rx, ry, rw, rh = rect
        for y in range(ry, min(self.height, ry + rh)):
            for x in range(rx, min(self.width, rx + rw)):
                dither_val = (BAYER_2X2[y % 2][x % 2] + 0.5) / 4.0
                chosen = color_a if dither_val < threshold else color_b
                self.put_pixel(x, y, chosen)

    def replace_color(self, old_color: RGBA, new_color: RGBA) -> int:
        """Replaces all occurrences of old_color with new_color."""
        count = 0
        for y in range(self.height):
            for x in range(self.width):
                if self.get_pixel(x, y) == old_color:
                    self.put_pixel(x, y, new_color)
                    count += 1
        return count

    def quantize_to_palette(self, palette: GamePalette) -> None:
        """Snaps all colors in the canvas to the nearest color in the given palette."""
        for y in range(self.height):
            for x in range(self.width):
                color = self.get_pixel(x, y)
                if color[3] > 0:
                    nearest = palette.find_nearest_color(color)
                    self.put_pixel(x, y, nearest)

    def get_upscaled(self, scale_factor: int = 4) -> Image.Image:
        """Returns a nearest-neighbor upscaled image for crisp pixel art preview."""
        new_w = self.width * scale_factor
        new_h = self.height * scale_factor
        return self.image.resize((new_w, new_h), Image.Resampling.NEAREST)
