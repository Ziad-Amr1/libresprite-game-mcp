"""
Game engine exporters for Godot 4.x, Unity, TexturePacker JSON, and animated GIF previews.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from PIL import Image

from libresprite_game_mcp.core.aseprite_file import AsepriteProject


def export_sprite_sheet_native(
    project: AsepriteProject,
    output_png: Union[str, Path],
    output_json: Optional[Union[str, Path]] = None,
    padding: int = 1,
    layout: str = "horizontal",  # "horizontal" or "grid"
) -> Dict:
    """
    Packs all frames of an Aseprite project into a sprite sheet texture and JSON metadata.
    """
    frames = project.get_all_frame_images()
    if not frames:
        raise ValueError("Project contains no frames to export.")

    frame_w = project.width
    frame_h = project.height
    frame_count = len(frames)

    # Determine layout dimensions
    if layout == "horizontal":
        cols = frame_count
        rows = 1
    else:  # roughly square grid
        import math
        cols = math.ceil(math.sqrt(frame_count))
        rows = math.ceil(frame_count / cols)

    cell_w = frame_w + padding
    cell_h = frame_h + padding
    sheet_w = cols * cell_w + padding
    sheet_h = rows * cell_h + padding

    sheet_img = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    frames_meta = {}
    frame_rects: List[Tuple[int, int, int, int]] = []

    for idx, frame_img in enumerate(frames):
        c = idx % cols
        r = idx // cols
        x = padding + c * cell_w
        y = padding + r * cell_h

        sheet_img.paste(frame_img, (x, y))
        frame_rects.append((x, y, frame_w, frame_h))

        duration_ms = 100
        if idx < len(project.sprite.frames):
            duration_ms = project.sprite.frames[idx].duration_ms

        frame_key = f"frame_{idx:03d}"
        frames_meta[frame_key] = {
            "frame": {"x": x, "y": y, "w": frame_w, "h": frame_h},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": frame_w, "h": frame_h},
            "sourceSize": {"w": frame_w, "h": frame_h},
            "duration": duration_ms,
        }

    # Save PNG
    png_path = Path(output_png).resolve()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    sheet_img.save(png_path)

    # Build meta tags
    meta_tags = []
    for tag in project.sprite.tags:
        meta_tags.append({
            "name": tag.name,
            "from": tag.from_frame,
            "to": tag.to_frame,
            "direction": "forward",
        })

    json_data = {
        "frames": frames_meta,
        "meta": {
            "app": "LibreSprite Game MCP",
            "version": "1.0",
            "image": png_path.name,
            "format": "RGBA8888",
            "size": {"w": sheet_w, "h": sheet_h},
            "scale": "1",
            "frameTags": meta_tags,
        }
    }

    if output_json:
        j_path = Path(output_json).resolve()
        j_path.parent.mkdir(parents=True, exist_ok=True)
        with open(j_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

    return {
        "sheet_path": str(png_path),
        "json_path": str(Path(output_json).resolve()) if output_json else None,
        "sheet_size": (sheet_w, sheet_h),
        "frames_count": frame_count,
        "frame_rects": frame_rects,
        "tags": meta_tags,
    }


def export_godot_spriteframes(
    project: AsepriteProject,
    sheet_texture_res_path: str,
    output_tres_path: Union[str, Path],
    frame_rects: Optional[List[Tuple[int, int, int, int]]] = None,
    fps: float = 10.0,
    padding: int = 1,
    sheet_size: Optional[Tuple[int, int]] = None,
) -> Path:
    """
    Exports a 100% syntactically valid Godot 4.x SpriteFrames (.tres) resource.
    Preserves exact frame durations, verifies atlas regions, and handles tag ranges safely.
    """
    tres_path = Path(output_tres_path).resolve()
    tres_path.parent.mkdir(parents=True, exist_ok=True)

    frame_count = len(project.sprite.frames)
    if frame_count == 0:
        raise ValueError("Cannot export SpriteFrames: project has 0 frames.")

    frame_w = project.width
    frame_h = project.height

    # Calculate default horizontal strip if rects not passed
    if not frame_rects or len(frame_rects) != frame_count:
        frame_rects = []
        cell_w = frame_w + padding
        for i in range(frame_count):
            rx = padding + i * cell_w
            ry = padding
            frame_rects.append((rx, ry, frame_w, frame_h))

    # Verify atlas regions against sheet dimensions if provided
    if sheet_size:
        sheet_w, sheet_h = sheet_size
        for i, (rx, ry, rw, rh) in enumerate(frame_rects):
            if rx < 0 or ry < 0 or (rx + rw) > sheet_w or (ry + rh) > sheet_h:
                raise ValueError(
                    f"Frame {i} region ({rx}, {ry}, {rw}, {rh}) exceeds atlas sheet bounds {sheet_size}"
                )

    load_steps = 2 + frame_count
    base_frame_ms = 1000.0 / max(0.1, fps)

    lines = [
        f'[gd_resource type="SpriteFrames" load_steps={load_steps} format=3]',
        "",
        f'[ext_resource type="Texture2D" path="{sheet_texture_res_path}" id="1_texture"]',
        "",
    ]

    # SubResource declarations for AtlasTexture
    for i, (rx, ry, rw, rh) in enumerate(frame_rects):
        lines.append(f'[sub_resource type="AtlasTexture" id="AtlasTexture_{i}"]')
        lines.append('atlas = ExtResource("1_texture")')
        lines.append(f'region = Rect2({rx}, {ry}, {rw}, {rh})')
        lines.append("")

    lines.append("[resource]")
    lines.append("animations = [{")

    tags = list(project.sprite.tags)
    if not tags:
        # Fallback to default animation covering all frames
        lines.append('  "frames": [')
        for i in range(frame_count):
            dur_ms = project.sprite.frames[i].duration_ms
            dur_factor = max(0.01, round(dur_ms / base_frame_ms, 3))
            lines.append(f'    {{ "duration": {dur_factor}, "texture": SubResource("AtlasTexture_{i}") }},')
        lines.append('  ],')
        lines.append('  "loop": true,')
        lines.append('  "name": &"default",')
        lines.append(f'  "speed": {fps}')
    else:
        for idx, tag in enumerate(tags):
            # Clamp and sanitize tag frame ranges
            from_f = max(0, min(tag.from_frame, frame_count - 1))
            to_f = max(0, min(tag.to_frame, frame_count - 1))
            if from_f > to_f:
                from_f, to_f = to_f, from_f

            lines.append('  "frames": [')
            for f_idx in range(from_f, to_f + 1):
                dur_ms = project.sprite.frames[f_idx].duration_ms
                dur_factor = max(0.01, round(dur_ms / base_frame_ms, 3))
                lines.append(f'    {{ "duration": {dur_factor}, "texture": SubResource("AtlasTexture_{f_idx}") }},')
            lines.append('  ],')
            lines.append('  "loop": true,')
            lines.append(f'  "name": &"{tag.name}",')
            lines.append(f'  "speed": {fps}')
            if idx < len(tags) - 1:
                lines.append("}, {")

    lines.append("}]")

    with open(tres_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return tres_path


def export_animated_gif(
    project: AsepriteProject,
    output_gif: Union[str, Path],
    scale: int = 4,
    loop: int = 0,
) -> Path:
    """
    Exports the project animation as a clean, crisp scaled GIF.
    """
    gif_path = Path(output_gif).resolve()
    gif_path.parent.mkdir(parents=True, exist_ok=True)

    frames = project.get_all_frame_images()
    if not frames:
        raise ValueError("Project contains no frames.")

    scaled_frames = []
    durations = []

    for idx, f in enumerate(frames):
        sf = f.resize((f.width * scale, f.height * scale), Image.Resampling.NEAREST)
        scaled_frames.append(sf)

        d = 100
        if idx < len(project.sprite.frames):
            d = project.sprite.frames[idx].duration_ms
        durations.append(d)

    # Save as GIF
    scaled_frames[0].save(
        gif_path,
        save_all=True,
        append_images=scaled_frames[1:],
        duration=durations,
        loop=loop,
        disposal=2,
    )
    return gif_path


def export_pixilart_project(
    project: AsepriteProject,
    output_pixil: Union[str, Path],
    title: str = "Pixilart Asset",
    fps: int = 10,
) -> Path:
    """
    Exports an AsepriteProject into a valid .pixil JSON project format
    compatible with Pixilart web and desktop editors.
    """
    pixil_path = Path(output_pixil).resolve()
    pixil_path.parent.mkdir(parents=True, exist_ok=True)

    frames_img = project.get_all_frame_images()
    if not frames_img:
        raise ValueError("Project contains no frames to export.")

    w = project.width
    h = project.height

    palette_set = set()
    pixil_frames = []

    for idx, frame in enumerate(frames_img):
        rgba = frame.convert("RGBA")
        pixels = []
        dur_ms = 100
        if idx < len(project.sprite.frames):
            dur_ms = project.sprite.frames[idx].duration_ms

        for y in range(h):
            for x in range(w):
                r, g, b, a = rgba.getpixel((x, y))
                if a > 0:
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    palette_set.add(hex_color)
                    pixels.append({
                        "x": x,
                        "y": y,
                        "color": hex_color,
                        "opacity": round(a / 255.0, 2),
                    })

        pixil_frames.append({
            "frame_index": idx,
            "duration_ms": dur_ms,
            "layers": [
                {
                    "name": "Layer 1",
                    "opacity": 1.0,
                    "visible": True,
                    "pixels": pixels,
                }
            ],
        })

    pixil_data = {
        "version": "1.0.0",
        "format": "pixil",
        "title": title,
        "width": w,
        "height": h,
        "fps": fps,
        "palette": sorted(list(palette_set)),
        "frames": pixil_frames,
    }

    with open(pixil_path, "w", encoding="utf-8") as f:
        json.dump(pixil_data, f, indent=2)

    return pixil_path

