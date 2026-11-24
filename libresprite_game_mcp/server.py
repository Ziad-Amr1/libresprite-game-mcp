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
from libresprite_game_mcp.core.security import workspace_policy
from libresprite_game_mcp.generators.character_generator import (
    CharacterStyle,
    build_animated_character_project,
    legacy_args_to_blueprint,
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
    export_pixilart_project,
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
    """Safely resolves destination directory and strictly enforces workspace boundaries."""
    target = output_dir if output_dir else get_default_assets_dir()
    return workspace_policy.safe_resolve(target, allow_create_dir=True)


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
def create_character_from_blueprint(
    blueprint: Dict[str, Any],
    profile: Optional[Dict[str, Any]] = None,
    export_sheet: bool = True,
    export_gif: bool = True,
    export_godot: bool = False,
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Creates an animated pixel art character driven by a structured CharacterBlueprint and ArtProfile.
    Validates blueprint schema, renders custom animations/durations, and exports engine-ready assets.
    """
    # 1. Validate Blueprint with Pydantic
    bp_model = CharacterBlueprint.model_validate(blueprint)
    profile_model = ArtProfile.model_validate(profile) if profile else None

    out_dir = safe_resolve_output_dir(output_dir)
    palette_name = profile_model.palette_name if profile_model else "db16"

    # 2. Build Aseprite Project
    project = build_animated_character_project(
        blueprint=bp_model,
        profile=profile_model,
        palette_name=palette_name,
    )
    ase_file = out_dir / f"{bp_model.character_id}.aseprite"
    project.save(ase_file)

    width, height = bp_model.size
    result = {
        "name": bp_model.name,
        "character_id": bp_model.character_id,
        "aseprite_project": str(ase_file),
        "size": f"{width}x{height}",
        "tags": [t.name for t in project.sprite.tags],
        "layers": [l.name for l in project.sprite.layers],
        "pivot": list(bp_model.pivot),
    }

    frame_rects = None
    sheet_png = out_dir / f"{bp_model.character_id}_sheet.png"
    sheet_json = out_dir / f"{bp_model.character_id}_sheet.json"

    # Export Sprite Sheet (PNG + JSON)
    if export_sheet:
        meta = export_sprite_sheet_native(project, sheet_png, sheet_json, padding=1)
        result["sheet_png"] = meta["sheet_path"]
        result["sheet_json"] = meta["json_path"]
        frame_rects = meta.get("frame_rects")

    # Export Animated GIF preview
    if export_gif:
        gif_path = out_dir / f"{bp_model.character_id}_preview.gif"
        export_animated_gif(project, gif_path, scale=4)
        result["preview_gif"] = str(gif_path)

    # Export Godot 4.x SpriteFrames with accurate AtlasTexture SubResources & frame duration factors
    if export_godot:
        godot_tres = out_dir / f"{bp_model.character_id}_spriteframes.tres"
        res_tex_path = f"res://{sheet_png.name}" if "sheet_png" in result else "res://sheet.png"
        export_godot_spriteframes(
            project,
            res_tex_path,
            godot_tres,
            frame_rects=frame_rects,
            fps=profile_model.animation.default_fps if profile_model else 10.0,
            sheet_size=meta["sheet_size"] if export_sheet else None,
        )
        result["godot_spriteframes"] = str(godot_tres)

    return result


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
    Legacy adapter for character generation.
    Converts arguments into a CharacterBlueprint and delegates to create_character_from_blueprint.
    """
    blueprint = legacy_args_to_blueprint(
        name=name,
        width=width,
        height=height,
        shirt_color=shirt_color,
        pants_color=pants_color,
        hair_color=hair_color,
        skin_color=skin_color,
    )
    profile = ArtProfile(
        project_name="GameProject",
        palette_name=palette_name,
    )
    return create_character_from_blueprint(
        blueprint=blueprint.model_dump(),
        profile=profile.model_dump(),
        export_sheet=export_sheet,
        export_gif=export_gif,
        export_godot=export_godot,
        output_dir=output_dir,
    )


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
    anchor_pivot_x: float = 0.5,
    anchor_pivot_y: float = 0.9,
    allow_translucent: bool = False,
    strict_alignment: bool = False,
) -> Dict:
    """
    Runs automated Art QA on a generated pixel art asset (PNG or .aseprite).
    Verifies palette adherence, alpha hygiene, dimensions, cluster noise, and anchor-relative animation alignment.
    """
    p = workspace_policy.safe_resolve(asset_path, must_exist=True)

    palette = GamePalette.from_name(palette_name)
    expected_size = (expected_width, expected_height) if (expected_width and expected_height) else None
    validator = AssetValidator(
        palette=palette,
        expected_size=expected_size,
        anchor_pivot=(anchor_pivot_x, anchor_pivot_y),
        allow_translucent=allow_translucent,
        strict_alignment=strict_alignment,
    )

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
    Strictly verifies workspace boundaries for inputs and outputs.
    """
    inp = workspace_policy.safe_resolve(input_aseprite_file, must_exist=True)

    out_png = workspace_policy.safe_resolve(output_png) if output_png else inp.with_name(f"{inp.stem}_sheet.png")
    out_json = workspace_policy.safe_resolve(output_json) if output_json else inp.with_name(f"{inp.stem}_sheet.json")

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
def export_pixilart_file(
    input_aseprite_file: str,
    output_pixil: Optional[str] = None,
    title: str = "Pixilart Asset",
) -> Dict:
    """
    Exports an Aseprite/LibreSprite file to Pixilart .pixil JSON format.
    Enforces safe workspace boundary resolution so all outputs save cleanly.
    """
    inp = workspace_policy.safe_resolve(input_aseprite_file, must_exist=True)
    out_pix = workspace_policy.safe_resolve(output_pixil) if output_pixil else inp.with_suffix(".pixil")
    project = AsepriteProject.load(inp)
    saved_path = export_pixilart_project(project, out_pix, title=title)
    return {
        "status": "success",
        "saved_path": str(saved_path),
        "format": "pixil",
        "frames": len(project.sprite.frames),
    }


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
    safe_commands = {"create_canvas", "get_preview", "save_sprite", "put_pixel", "draw_rect", "clear_canvas", "exit_session"}
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


# -----------------------------------------------------------------------------
# Learning Layer & Skill Builder Production Tools
# -----------------------------------------------------------------------------
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator

orchestrator = ProductionOrchestrator()


@mcp.tool()
def list_applicable_skills(
    task_category: str = "character",
    perspective: str = "top_down",
    art_profile_name: Optional[str] = None,
) -> List[Dict]:
    """
    Discovers approved production Skills matching the current task category and art profile.
    """
    context = {"task_category": task_category, "perspective": perspective}
    skills = orchestrator.find_applicable_skills(context, art_profile_name=art_profile_name)
    return [s.model_dump() for s in skills]


@mcp.tool()
def execute_production_skill(
    skill_id: str,
    version: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    project_id: str = "default",
) -> Dict:
    """
    Executes an approved deterministic production Skill, enforces QA checks,
    and logs experience telemetry into the Learning Layer.
    """
    return orchestrator.execute_skill(
        skill_id=skill_id,
        version=version,
        parameters=parameters,
        project_id=project_id,
    )


@mcp.tool()
def get_learning_guidance(
    project_id: Optional[str] = None,
    task_category: str = "character",
    width: int = 16,
    height: int = 16,
) -> Dict:
    """
    Retrieves learned Art Bible constraints, recommended palettes, and outline modes
    for the specified task category and resolution, respecting project isolation.
    """
    return orchestrator.get_knowledge_guidance(
        project_id=project_id,
        task_category=task_category,
        resolution=(width, height),
    )


@mcp.tool()
def record_user_feedback(
    experience_id: str,
    feedback_type: str = "approval",  # "approval", "rejection", "correction", "preference"
    rating: Optional[float] = None,   # 1.0 - 5.0
    notes: Optional[str] = None,
) -> Dict:
    """
    Records human approval, rejection, or feedback for a completed asset generation,
    updating empirical confidence scores across related knowledge rules.
    """
    fb = orchestrator.record_feedback(
        experience_id=experience_id,
        feedback_type=feedback_type,
        user_rating=rating,
        notes=notes,
    )
    return fb.model_dump()


def main():
    ensure_relay_running()
    mcp.run()


if __name__ == "__main__":
    main()
