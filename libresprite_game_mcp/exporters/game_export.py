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

    for idx, frame_img in enumerate(frames):
        c = idx % cols
        r = idx // cols
        x = padding + c * cell_w
        y = padding + r * cell_h

        sheet_img.paste(frame_img, (x, y))

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
        "tags": meta_tags,
    }


def export_godot_spriteframes(
    project: AsepriteProject,
    sheet_texture_res_path: str,
    output_tres_path: Union[str, Path],
    fps: float = 10.0,
) -> Path:
    """
    Exports a Godot 4.x SpriteFrames (.tres) resource for use in AnimatedSprite2D.
    """
    tres_path = Path(output_tres_path).resolve()
    tres_path.parent.mkdir(parents=True, exist_ok=True)

    # Godot Resource text format
    content = [
        '[gd_resource type="SpriteFrames" load_steps=2 format=3]',
        "",
        f'[ext_resource type="Texture2D" path="{sheet_texture_res_path}" id="1_texture"]',
        "",
        '[resource]',
        "animations = [{",
    ]

    # Map tags or create default animation
    tags = list(project.sprite.tags)
    if not tags:
        # Default animation covering all frames
        content.append('  "frames": [')
        for i in range(len(project.sprite.frames)):
            content.append(f'    {{ "duration": 1.0, "texture": SubResource("AtlasTexture_{i}") }},')
        content.append('  ],')
        content.append('  "loop": true,')
        content.append('  "name": &"default",')
        content.append(f'  "speed": {fps}')
    else:
        for tag in tags:
            content.append(f'  "frames": [')
            for f_idx in range(tag.from_frame, tag.to_frame + 1):
                content.append(f'    {{ "duration": 1.0, "texture": SubResource("AtlasTexture_{f_idx}") }},')
            content.append('  ],')
            content.append('  "loop": true,')
            content.append(f'  "name": &"{tag.name}",')
            content.append(f'  "speed": {fps}')
            content.append("}, {")
        if content[-1] == "}, {":
            content.pop()

    content.append("}]")

    with open(tres_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content) + "\n")

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
