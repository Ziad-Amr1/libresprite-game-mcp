"""
LibreSprite Game Asset MCP Server.
Empowers AI assistants to create pixel art game characters, animations, tilesets,
items, and game engine exports (Godot, Unity, SpriteSheets) using LibreSprite.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from PIL import Image

from mcp.server.fastmcp import FastMCP, Context

from libresprite_game_mcp.config import (
    find_libresprite_executable,
    get_libresprite_scripts_dir,
    get_default_assets_dir,
    DEFAULT_PORT,
)
from libresprite_game_mcp.core.palettes import (
    list_builtin_palettes,
    GamePalette,
    hex_to_rgba,
)
from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.core.cli_runner import LibreSpriteCLI
from libresprite_game_mcp.generators.character_generator import (
    CharacterStyle,
    build_animated_character_project,
)
from libresprite_game_mcp.generators.tileset_generator import (
    build_autotile_3x3_sheet,
)
from libresprite_game_mcp.generators.item_generator import (
    generate_sword_icon,
    generate_potion_icon,
    build_animated_torch_project,
    build_animated_coin_project,
)
from libresprite_game_mcp.exporters.game_export import (
    export_sprite_sheet_native,
    export_godot_spriteframes,
    export_animated_gif,
)
from libresprite_game_mcp.bridge.http_relay import (
    state,
    ensure_relay_running,
)
from libresprite_game_mcp.models.schemas import (
    ArtProfile,
    CharacterBlueprint,
    ValidationReport,
)
from libresprite_game_mcp.qa.validator import AssetValidator

# Initialize FastMCP Server
mcp = FastMCP(
    "LibreSprite-Game-MCP",
    dependencies=["pillow", "aseprite", "mcp", "pydantic"],
)


def safe_resolve_output_dir(output_dir: Optional[str] = None) -> Path:
    """Safely resolves destination directory and blocks illegal path traversal."""
    if not output_dir:
        return get_default_assets_dir()
    resolved = Path(output_dir).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


@mcp.tool()
def get_libresprite_status() -> Dict:
    """
    Checks the status of LibreSprite installation, CLI batch capability,
    scripts directory, and live GUI bridge connection.
    """
    ensure_relay_running()
    cli = LibreSpriteCLI()
    exe_found = cli.is_available()
    version = cli.get_version() if exe_found else "Not detected"
    scripts_dir = get_libresprite_scripts_dir()
    bridge_installed = (scripts_dir / "libresprite_mcp_bridge.js").exists()

    return {
        "executable_path": cli.exe_path,
        "is_installed": exe_found,
        "version": version,
        "scripts_directory": str(scripts_dir),
        "bridge_script_installed": bridge_installed,
        "live_gui_connected": state.is_alive(),
        "client_info": state.client_info if state.is_alive() else {},
    }


@mcp.tool()
def install_bridge_script() -> str:
    """
    Installs the LibreSprite MCP bridge script into LibreSprite's scripts folder.
    Run this to enable live GUI control from LibreSprite.
    """
    scripts_dir = get_libresprite_scripts_dir()
    bridge_src = Path(__file__).parent / "bridge" / "libresprite_mcp_bridge.js"
    dest = scripts_dir / "libresprite_mcp_bridge.js"

    if not bridge_src.exists():
        return f"Error: Source bridge script not found at {bridge_src}"

    import shutil
    shutil.copy2(bridge_src, dest)
    return f"Successfully installed bridge script to {dest}. In LibreSprite, click File > Scripts > libresprite_mcp_bridge.js to connect."


@mcp.tool()
def list_game_palettes() -> Dict:
    """
    Lists all curated retro game color palettes (PICO-8, Game Boy, NES, DB16, DB32, EDG32, etc.)
    with available colors.
    """
    return {
        "available_palettes": list_builtin_palettes(),
        "description": "Specify any palette name when generating characters, tilesets, or recoloring sprites.",
    }


@mcp.tool()
def create_character_sprite(
    name: str = "hero",
    width: int = 16,
    height: int = 16,
    palette_name: str = "db16",
    shirt_color: str = "#597dce",
    pants_color: str = "#4e4a4e",
    hair_color: str = "#442434",
    skin_color: str = "#d2aa99",
    export_sheet: bool = True,
    export_gif: bool = True,
    export_godot: bool = False,
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Creates a multi-layered, multi-frame animated pixel art character.
    Generates Idle, Walk, Attack, and Hurt animations with standard tags.
    Saves an editable .aseprite project file and exports engine-ready sprite sheets.
    """
    out_dir = safe_resolve_output_dir(output_dir)

    style = CharacterStyle(
        skin=skin_color,
        hair=hair_color,
        shirt=shirt_color,
        pants=pants_color,
    )

    project = build_animated_character_project(width, height, style, palette_name)
    ase_file = out_dir / f"{name}.aseprite"
    project.save(ase_file)

    result = {
        "name": name,
        "aseprite_project": str(ase_file),
        "size": f"{width}x{height}",
        "tags": ["idle", "walk", "attack", "hurt"],
        "layers": [l.name for l in project.sprite.layers],
    }

    frame_rects = None
    sheet_png = out_dir / f"{name}_sheet.png"
    sheet_json = out_dir / f"{name}_sheet.json"

    # Export Sprite Sheet (PNG + JSON)
    if export_sheet:
        meta = export_sprite_sheet_native(project, sheet_png, sheet_json, padding=1)
        result["sheet_png"] = meta["sheet_path"]
        result["sheet_json"] = meta["json_path"]
        frame_rects = meta.get("frame_rects")

    # Export Animated GIF preview
    if export_gif:
        gif_path = out_dir / f"{name}_preview.gif"
        export_animated_gif(project, gif_path, scale=4)
        result["preview_gif"] = str(gif_path)

    # Export Godot 4.x SpriteFrames with accurate AtlasTexture SubResources
    if export_godot:
        godot_tres = out_dir / f"{name}_spriteframes.tres"
        res_tex_path = f"res://{sheet_png.name}" if "sheet_png" in result else "res://sheet.png"
        export_godot_spriteframes(project, res_tex_path, godot_tres, frame_rects=frame_rects, fps=10.0)
        result["godot_spriteframes"] = str(godot_tres)

    return result


@mcp.tool()
def create_autotile_tileset(
    name: str = "world_tiles",
    tile_size: int = 16,
    theme: str = "grass_dirt",  # "grass_dirt", "stone_dungeon", "wood_planks"
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Generates a 3x3 (+ island) autotile sheet (corners, edges, center, island)
    for platformers or top-down games. Exports PNG texture and tile coordinate metadata.
    """
    out_dir = safe_resolve_output_dir(output_dir)

    sheet_img, metadata = build_autotile_3x3_sheet(tile_size, theme)
    png_path = out_dir / f"{name}.png"
    json_path = out_dir / f"{name}.json"

    sheet_img.save(png_path)
    with open(json_path, "w", encoding="utf-8") as f:
        import json
        json.dump(metadata, f, indent=2)

    return {
        "tileset_name": name,
        "theme": theme,
        "tile_size": tile_size,
        "sheet_png": str(png_path),
        "metadata_json": str(json_path),
        "total_tiles": len(metadata["tiles"]),
    }


@mcp.tool()
def create_game_item(
    item_type: str = "sword",  # "sword", "potion", "torch", "coin"
    name: str = "item",
    size: int = 16,
    potion_variant: str = "health",  # "health", "mana", "stamina", "elixir"
    export_gif: bool = True,
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Generates pixel art game items, weapons, potions, or animated props (torches, coins).
    """
    out_dir = safe_resolve_output_dir(output_dir)

    result = {"item_type": item_type, "size": f"{size}x{size}"}

    if item_type == "sword":
        img = generate_sword_icon(size)
        png_path = out_dir / f"{name}.png"
        img.save(png_path)
        result["image_png"] = str(png_path)

    elif item_type == "potion":
        img = generate_potion_icon(size, potion_variant)
        png_path = out_dir / f"{name}_{potion_variant}.png"
        img.save(png_path)
        result["image_png"] = str(png_path)
        result["variant"] = potion_variant

    elif item_type == "torch":
        project = build_animated_torch_project(size)
        ase_path = out_dir / f"{name}.aseprite"
        project.save(ase_path)
        result["aseprite_project"] = str(ase_path)
        if export_gif:
            gif_path = out_dir / f"{name}.gif"
            export_animated_gif(project, gif_path, scale=4)
            result["preview_gif"] = str(gif_path)

    elif item_type == "coin":
        project = build_animated_coin_project(size)
        ase_path = out_dir / f"{name}.aseprite"
        project.save(ase_path)
        result["aseprite_project"] = str(ase_path)
        if export_gif:
            gif_path = out_dir / f"{name}.gif"
            export_animated_gif(project, gif_path, scale=4)
            result["preview_gif"] = str(gif_path)

    else:
        raise ValueError(f"Unknown item_type '{item_type}'. Supported: sword, potion, torch, coin")

    return result


@mcp.tool()
def validate_game_asset(
    asset_path: str,
    palette_name: str = "db16",
    expected_width: Optional[int] = None,
    expected_height: Optional[int] = None,
) -> Dict:
    """
    Runs automated Art QA on a generated pixel art asset (PNG or .aseprite).
    Verifies palette adherence, alpha hygiene, dimensions, and animation alignment.
    """
    p = Path(asset_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Asset file not found: {p}")

    palette = GamePalette.from_name(palette_name)
    expected_size = (expected_width, expected_height) if (expected_width and expected_height) else None
    validator = AssetValidator(palette=palette, expected_size=expected_size)

    if p.suffix.lower() in (".ase", ".aseprite"):
        project = AsepriteProject.load(p)
        report = validator.validate_project(project, asset_name=p.stem)
    else:
        img = Image.open(p)
        report = validator.validate_image(img, asset_name=p.stem)

    return report.model_dump()


@mcp.tool()
def export_asset_sprite_sheet(
    input_aseprite_file: str,
    output_png: Optional[str] = None,
    output_json: Optional[str] = None,
    sheet_type: str = "packed",  # "packed", "horizontal", "vertical", "rows"
    border_padding: int = 1,
    shape_padding: int = 1,
    scale: int = 1,
    trim: bool = False,
) -> Dict:
    """
    Packs any .ase or .aseprite file into a texture atlas sheet and JSON metadata
    using LibreSprite's native batch engine (or python fallback).
    """
    inp = Path(input_aseprite_file).resolve()
    if not inp.exists():
        raise FileNotFoundError(f"File not found: {inp}")

    out_png = Path(output_png).resolve() if output_png else inp.with_name(f"{inp.stem}_sheet.png")
    out_json = Path(output_json).resolve() if output_json else inp.with_name(f"{inp.stem}_sheet.json")

    cli = LibreSpriteCLI()
    if cli.is_available():
        res = cli.export_sprite_sheet(
            input_file=inp,
            sheet_png=out_png,
            data_json=out_json,
            sheet_type=sheet_type,
            border_padding=border_padding,
            shape_padding=shape_padding,
            scale=scale,
            trim=trim,
        )
        return res
    else:
        project = AsepriteProject.load(inp)
        res = export_sprite_sheet_native(project, out_png, out_json, padding=shape_padding)
        return res


@mcp.tool()
def live_get_canvas_preview() -> Dict:
    """
    Captures a real-time PNG preview of the active canvas directly from LibreSprite GUI.
    Returns base64 PNG data and dimensions.
    """
    ensure_relay_running()
    resp = state.queue_command({"type": "get_preview"}, timeout=8.0)
    return resp


@mcp.tool()
def live_execute_safe_command(
    command_name: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict:
    """
    Executes an allowlisted command securely inside the active LibreSprite instance.
    Permitted commands: create_canvas, get_preview, save_sprite, put_pixel, draw_rect, clear_canvas.
    """
    ensure_relay_running()
    safe_commands = {"create_canvas", "get_preview", "save_sprite", "put_pixel", "draw_rect", "clear_canvas"}
    if command_name not in safe_commands:
        return {
            "status": "error",
            "error": f"Command '{command_name}' is not in the safe allowlist: {list(safe_commands)}"
        }

    resp = state.queue_command({"type": command_name, "params": params or {}}, timeout=10.0)
    return resp


@mcp.tool()
def live_create_canvas(width: int = 16, height: int = 16, color_mode: str = "rgba") -> Dict:
    """
    Creates a new blank canvas file inside the open LibreSprite GUI application.
    """
    return live_execute_safe_command("create_canvas", {"width": width, "height": height, "colorMode": color_mode})


def main():
    ensure_relay_running()
    mcp.run()


if __name__ == "__main__":
    main()
