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
    build_blob47_sheet,
    build_wang16_sheet,
    generate_tileset_suite,
)
from libresprite_game_mcp.generators.title_generator import (
    generate_title_assets,
    build_game_title_logo,
)
from libresprite_game_mcp.generators.item_generator import (
    generate_sword_icon,
    generate_weapon_icon,
    generate_armor_icon,
    generate_potion_icon,
    generate_consumable_icon,
    build_animated_torch_project,
    build_animated_coin_project,
    build_animated_radiant_lantern,
    build_animated_shadow_orb,
    build_animated_crystal_shard,
    build_animated_heart_pickup,
    build_animated_key_pickup,
    build_animated_gem_drop,
    build_animated_chest_project,
    build_animated_pot_break_project,
)
from libresprite_game_mcp.generators.vfx_generator import (
    build_animated_projectile,
    build_animated_impact,
    build_animated_aoe_rune,
    build_animated_shield_aura,
)
from libresprite_game_mcp.exporters.game_export import (
    export_sprite_sheet_native,
    export_godot_spriteframes,
    export_godot_tileset,
    export_animated_gif,
    export_tag_gifs,
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
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator

# Initialize FastMCP Server and Production Orchestrator
mcp = FastMCP(
    "LibreSprite-Game-MCP",
    dependencies=["pillow", "aseprite", "mcp", "pydantic"],
)

orchestrator = ProductionOrchestrator()


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
    import time
    start_time = time.perf_counter()

    bp_model = CharacterBlueprint.model_validate(blueprint)
    profile_model = ArtProfile.model_validate(profile) if profile else None

    out_dir = safe_resolve_output_dir(output_dir)
    palette_name = profile_model.palette_name if profile_model else "db16"
    width, height = bp_model.size

    # 2. Retrieve Learning Layer Guidance from ProductionOrchestrator
    project_id = profile_model.project_name if profile_model else "default"
    guidance = orchestrator.build_character_guidance(
        resolution=(width, height),
        art_profile_name=profile_model.project_name if profile_model else "DefaultGame",
        archetype=bp_model.archetype,
        palette_name=palette_name,
        project_id=project_id,
    )

    # 3. Build Aseprite Project with Learning Layer guidance
    project = build_animated_character_project(
        blueprint=bp_model,
        profile=profile_model,
        palette_name=palette_name,
        guidance=guidance.model_dump(),
    )
    ase_file = out_dir / f"{bp_model.character_id}.aseprite"
    project.save(ase_file)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

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
        tag_gifs = export_tag_gifs(project, out_dir, bp_model.character_id, scale=4)
        if tag_gifs:
            result["tag_gifs"] = tag_gifs

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

    # 4. Record experience in Learning Layer
    exp = orchestrator.experience_collector.record_task_run(
        task_id=f"mcp_blueprint_{bp_model.character_id}_{int(time.time() * 1000)}",
        task_category="character",
        asset_category="sprite",
        resolution=(width, height),
        input_context={
            "blueprint": bp_model.model_dump(),
            "profile": profile_model.model_dump() if profile_model else None,
        },
        output_summary=result,
        tools_used=["create_character_from_blueprint"],
        execution_time_ms=duration_ms,
        execution_outcome="SUCCESS",
        art_profile={"name": profile_model.project_name if profile_model else "DefaultGame", "palette": palette_name},
        project_id=project_id,
    )
    result["experience_id"] = exp.id
    result["guidance_applied"] = guidance.applicable_rules
    result["guidance_rules_consumed"] = getattr(project, "metadata", {}).get("guidance_rules_consumed", [])
    result["guidance_rules_ignored"] = getattr(project, "metadata", {}).get("guidance_rules_ignored", [])

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
    theme: str = "grass_dirt",  # "grass_dirt", "stone_dungeon", "wood_planks", "sand_desert", "snow_ice", "scifi_metal"
    system: str = "blob_47",    # "blob_47" (48 tiles), "wang_16" (16 tiles), "autotile_3x3" (12 tiles)
    export_godot: bool = False,
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Generates production-grade autotile sheets with cluster shading and seamless connections.
    Supports 47-blob (8x6), 16-wang (4x4), and 3x3 platformers.
    Optionally exports Godot 4.x TileSet (.tres) resource with physics collisions.
    """
    out_dir = safe_resolve_output_dir(output_dir)

    sheet_img, metadata = generate_tileset_suite(
        system=system,
        tile_size=tile_size,
        theme_name=theme,
    )
    png_path = out_dir / f"{name}.png"
    json_path = out_dir / f"{name}.json"

    sheet_img.save(png_path)
    with open(json_path, "w", encoding="utf-8") as f:
        import json
        json.dump(metadata, f, indent=2)

    result = {
        "tileset_name": name,
        "theme": theme,
        "system": system,
        "tile_size": tile_size,
        "sheet_png": str(png_path),
        "metadata_json": str(json_path),
        "total_tiles": metadata.get("total_tiles", len(metadata["tiles"])),
        "width": sheet_img.width,
        "height": sheet_img.height,
    }

    if export_godot:
        tres_path = out_dir / f"{name}.tres"
        export_godot_tileset(
            tileset_meta=metadata,
            sheet_texture_res_path=f"res://{png_path.name}",
            output_tres_path=tres_path,
            terrain_name=theme,
        )
        result["godot_tres"] = str(tres_path)

    return result


@mcp.tool()
def create_game_title_logo(
    title: str = "LIBRESPRITE",
    subtitle: Optional[str] = None,
    theme: str = "fantasy_gold",  # "fantasy_gold", "cyberpunk_neon", "eldritch_gothic", "arcade_fire", "steel_chrome"
    scale: int = 2,
    extrusion_depth: int = 4,
    name: str = "game_title",
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Generates a retro pixel art game title and logo banner.
    Produces layered .aseprite project, high-res PNG, and animated twinkle GIF.
    """
    out_dir = safe_resolve_output_dir(output_dir)

    return generate_title_assets(
        title_text=title,
        subtitle=subtitle,
        theme_name=theme,
        scale=scale,
        extrusion_depth=extrusion_depth,
        output_dir=out_dir,
        file_prefix=name,
    )


@mcp.tool()
def create_game_item(
    item_type: str = "sword",
    name: str = "item",
    size: int = 16,
    variant: Optional[str] = None,
    potion_variant: str = "health",
    export_gif: bool = True,
    export_sheet: bool = True,
    export_godot: bool = False,
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Generates pixel art game items, weapons, potions, animated pickups, containers, and props.
    Supported item_type:
      - sword, weapon (variants: radiant_sword, void_dagger, iron_broadsword, shadow_scythe, starlight_staff, hunter_bow)
      - shield, armor (variants: radiant_shield, iron_buckler, void_barrier)
      - potion, consumable (variants: health, mana, stamina, elixir_dawn, void_draught, cozy_apple, golden_apple, glow_mushroom, ancient_scroll)
      - shard (variants: radiant, void, arcane, life)
      - heart (vitality pickup)
      - key (variants: golden, skeleton)
      - gem (variants: ruby, sapphire, emerald, amethyst, diamond)
      - coin (variants: gold, silver, copper)
      - chest (variants: wood_gold, sanctuary_white, shadow_crypt)
      - pot (variants: terracotta, urn_ancient)
      - lantern (sacred radiant lantern)
      - shadow_orb (eldritch void orb)
      - torch (dungeon wall torch)
    Optionally exports Godot 4.x SpriteFrames (.tres) and animated GIFs.
    """
    out_dir = safe_resolve_output_dir(output_dir)
    result = {"item_type": item_type, "size": f"{size}x{size}"}

    project = None
    img = None
    effective_variant = variant or potion_variant

    if item_type in ("sword", "weapon"):
        w_type = variant or "radiant_sword" if item_type == "weapon" else "iron_broadsword"
        img = generate_weapon_icon(w_type, size=size)
        result["variant"] = w_type

    elif item_type in ("shield", "armor"):
        a_type = variant or "radiant_shield"
        img = generate_armor_icon(a_type, size=size)
        result["variant"] = a_type

    elif item_type in ("potion", "consumable"):
        c_type = variant or (f"{potion_variant}_potion" if item_type == "consumable" else potion_variant)
        img = generate_consumable_icon(c_type, size=size)
        result["variant"] = c_type

    elif item_type in ("shard", "crystal"):
        elem = variant or "radiant"
        project = build_animated_crystal_shard(size=size, element=elem)
        result["variant"] = elem

    elif item_type == "heart":
        project = build_animated_heart_pickup(size=size)

    elif item_type == "key":
        k_type = variant or "golden"
        project = build_animated_key_pickup(size=size, key_type=k_type)
        result["variant"] = k_type

    elif item_type == "gem":
        g_type = variant or "ruby"
        project = build_animated_gem_drop(size=size, gem_type=g_type)
        result["variant"] = g_type

    elif item_type == "coin":
        c_var = variant or "gold"
        project = build_animated_coin_project(size=size, variant=c_var)
        result["variant"] = c_var

    elif item_type == "chest":
        ch_type = variant or "wood_gold"
        project = build_animated_chest_project(size=size, chest_type=ch_type)
        result["variant"] = ch_type

    elif item_type == "pot":
        p_type = variant or "terracotta"
        project = build_animated_pot_break_project(size=size, pot_type=p_type)
        result["variant"] = p_type

    elif item_type == "torch":
        project = build_animated_torch_project(size=size)

    elif item_type == "lantern":
        project = build_animated_radiant_lantern(size=size)

    elif item_type == "shadow_orb":
        project = build_animated_shadow_orb(size=size)

    else:
        raise ValueError(
            f"Unknown item_type '{item_type}'. Supported: sword, weapon, shield, armor, potion, consumable, "
            f"shard, heart, key, gem, coin, chest, pot, torch, lantern, shadow_orb"
        )

    # Export project or static image
    if project is not None:
        ase_path = out_dir / f"{name}.aseprite"
        project.save(ase_path)
        result["aseprite_project"] = str(ase_path)

        sheet_res = None
        if export_sheet:
            sheet_png = out_dir / f"{name}_sheet.png"
            sheet_json = out_dir / f"{name}_sheet.json"
            sheet_res = export_sprite_sheet_native(project, sheet_png, sheet_json)
            result["sheet_png"] = str(sheet_png)
            result["sheet_json"] = str(sheet_json)

        if export_gif:
            gif_path = out_dir / f"{name}.gif"
            export_animated_gif(project, gif_path, scale=4)
            result["preview_gif"] = str(gif_path)

        if export_godot:
            godot_tres = out_dir / f"{name}.tres"
            sheet_tex = f"res://{name}_sheet.png" if export_sheet else f"res://{name}.png"
            export_godot_spriteframes(
                project=project,
                sheet_texture_res_path=sheet_tex,
                output_tres_path=godot_tres,
                frame_rects=sheet_res["frame_rects"] if sheet_res else None,
                sheet_size=sheet_res["sheet_size"] if sheet_res else None,
                fps=8.0,
            )
            result["godot_tres"] = str(godot_tres)

    elif img is not None:
        png_path = out_dir / f"{name}.png"
        img.save(png_path)
        result["image_png"] = str(png_path)

    return result


@mcp.tool()
def create_spell_effect(
    spell_type: str = "radiant_sunbolt",
    name: str = "spell_fx",
    category: str = "projectile",  # "projectile", "impact", "aoe_rune", "shield_aura"
    size: int = 32,
    export_gif: bool = True,
    export_sheet: bool = True,
    export_godot: bool = True,
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Generates procedural pixel art magic spells, projectiles, impacts, AoE runes, and auras.
    Implements Saint11 VFX principles: concentric luminance ramps, non-linear timing, negative-space breakup.
    Supported types:
      - Projectiles (category='projectile'): radiant_sunbolt, void_orb, arcane_fireball, frost_lance
      - Impacts & Explosions (category='impact'): radiant_burst, void_implosion, slash_hitspark, fire_explosion
      - AoE Ground Runes (category='aoe_rune'): sanctuary_circle, abyssal_rift
      - Auras & Shields (category='shield_aura'): holy_barrier, shadow_shroud
    Exports .aseprite project, animated GIF, sprite sheet texture & JSON, and Godot 4 SpriteFrames (.tres).
    """
    out_dir = safe_resolve_output_dir(output_dir)

    project = None
    if category == "projectile" or spell_type in ("radiant_sunbolt", "void_orb", "arcane_fireball", "frost_lance"):
        project = build_animated_projectile(spell_type=spell_type, size=size)
    elif category == "impact" or spell_type in ("radiant_burst", "void_implosion", "slash_hitspark", "fire_explosion"):
        project = build_animated_impact(impact_type=spell_type, size=size)
    elif category == "aoe_rune" or spell_type in ("sanctuary_circle", "abyssal_rift"):
        project = build_animated_aoe_rune(rune_type=spell_type, size=size)
    elif category == "shield_aura" or spell_type in ("holy_barrier", "shadow_shroud"):
        project = build_animated_shield_aura(aura_type=spell_type, size=size)
    else:
        # Default to projectile
        project = build_animated_projectile(spell_type=spell_type, size=size)

    ase_path = out_dir / f"{name}.aseprite"
    project.save(ase_path)

    result = {
        "spell_type": spell_type,
        "category": category,
        "size": f"{size}x{size}",
        "aseprite_project": str(ase_path),
        "frame_count": len(project.sprite.frames),
    }

    sheet_res = None
    if export_sheet:
        sheet_png = out_dir / f"{name}_sheet.png"
        sheet_json = out_dir / f"{name}_sheet.json"
        sheet_res = export_sprite_sheet_native(project, sheet_png, sheet_json)
        result["sheet_png"] = str(sheet_png)
        result["sheet_json"] = str(sheet_json)

    if export_gif:
        gif_path = out_dir / f"{name}.gif"
        export_animated_gif(project, gif_path, scale=4)
        result["preview_gif"] = str(gif_path)

    if export_godot:
        godot_tres = out_dir / f"{name}.tres"
        sheet_tex = f"res://{name}_sheet.png" if export_sheet else f"res://{name}.png"
        export_godot_spriteframes(
            project=project,
            sheet_texture_res_path=sheet_tex,
            output_tres_path=godot_tres,
            frame_rects=sheet_res["frame_rects"] if sheet_res else None,
            sheet_size=sheet_res["sheet_size"] if sheet_res else None,
            fps=10.0,
        )
        result["godot_tres"] = str(godot_tres)

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

@mcp.tool()
def generate_character(
    character_id: str = "hero",
    name: Optional[str] = None,
    width: int = 16,
    height: int = 16,
    archetype: Optional[str] = None,
    palette_name: str = "db16",
    art_profile: str = "DefaultGame",
    project_id: str = "default",
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Generates an animated character directly through the ProductionOrchestrator and Learning Layer,
    binding Art Bible guidance, dispatching to native 16x16 or 32x32 generators, and logging experience telemetry.
    """
    out_dir = safe_resolve_output_dir(output_dir)
    return orchestrator.generate_character(
        character_id=character_id,
        name=name,
        size=(width, height),
        archetype=archetype,
        palette_name=palette_name,
        art_profile=art_profile,
        workspace=out_dir,
        project_id=project_id,
    )


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
