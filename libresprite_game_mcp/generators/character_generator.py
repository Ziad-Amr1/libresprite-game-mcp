"""
Procedural pixel art character and animation generator.
Accepts structured CharacterBlueprint and ArtProfile specifications or legacy style parameters.
Produces high-quality, archetype-differentiated pixel art with silhouetted volume,
selective outlining, and proportional cluster shading.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
from PIL import Image

from libresprite_game_mcp.core.palettes import GamePalette, RGBA, hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas
from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.models.schemas import CharacterBlueprint, CharacterAnimationSpec, ArtProfile


def adjust_color(color: RGBA, factor: float, palette: Optional[GamePalette] = None) -> RGBA:
    """Adjusts color brightness while maintaining 100% binary alpha and optional palette snapping."""
    r, g, b, _ = color
    if factor > 0:
        nr = int(r + (255 - r) * factor)
        ng = int(g + (255 - g) * factor)
        nb = int(b + (255 - b) * factor)
    else:
        f = abs(factor)
        nr = int(r * (1.0 - f))
        ng = int(g * (1.0 - f))
        nb = int(b * (1.0 - f))
    adjusted = (max(0, min(255, nr)), max(0, min(255, ng)), max(0, min(255, nb)), 255)
    if palette is not None:
        return palette.find_nearest_color(adjusted)
    return adjusted


class CharacterStyle:
    """Color styling and material ramps for character parts."""

    def __init__(
        self,
        skin: str = "#d2aa99",
        skin_shadow: str = "#854c30",
        hair: str = "#442434",
        shirt: str = "#597dce",
        shirt_shadow: str = "#30346d",
        pants: str = "#4e4a4e",
        pants_shadow: str = "#140c1c",
        outline: str = "#140c1c",
        eyes: str = "#140c1c",
        weapon: str = "#8595a1",
        weapon_hilt: str = "#d27d2c",
        hair_highlight: Optional[str] = None,
        shirt_highlight: Optional[str] = None,
        pants_highlight: Optional[str] = None,
        belt: Optional[str] = None,
        shoes: Optional[str] = None,
        accent: Optional[str] = None,
        weapon_glow: Optional[str] = None,
        weapon_highlight: Optional[str] = None,
        buckle: Optional[str] = None,
    ):
        self.skin = hex_to_rgba(skin)
        self.skin_shadow = hex_to_rgba(skin_shadow)
        self.skin_highlight = hex_to_rgba("#deeed6")

        self.hair = hex_to_rgba(hair)
        self.hair_shadow = hex_to_rgba(pants_shadow)
        self.hair_highlight = hex_to_rgba(hair_highlight) if hair_highlight else hex_to_rgba("#d27d2c")

        self.shirt = hex_to_rgba(shirt)
        self.shirt_shadow = hex_to_rgba(shirt_shadow)
        self.shirt_highlight = hex_to_rgba(shirt_highlight) if shirt_highlight else hex_to_rgba("#6dc2ca")

        self.pants = hex_to_rgba(pants)
        self.pants_shadow = hex_to_rgba(pants_shadow)
        self.pants_highlight = hex_to_rgba(pants_highlight) if pants_highlight else hex_to_rgba("#757161")

        self.outline = hex_to_rgba(outline)
        self.eyes = hex_to_rgba(eyes)
        self.weapon = hex_to_rgba(weapon)
        self.weapon_hilt = hex_to_rgba(weapon_hilt)
        self.weapon_highlight = hex_to_rgba(weapon_highlight) if weapon_highlight else hex_to_rgba("#deeed6")

        self.belt = hex_to_rgba(belt) if belt else hex_to_rgba(skin_shadow)
        self.shoes = hex_to_rgba(shoes) if shoes else hex_to_rgba(pants)
        self.accent = hex_to_rgba(accent) if accent else hex_to_rgba("#d04648")
        self.weapon_glow = hex_to_rgba(weapon_glow) if weapon_glow else hex_to_rgba("#6dc2ca")
        self.buckle = hex_to_rgba(buckle) if buckle else hex_to_rgba("#dad45e")


def resolve_archetype(
    blueprint: Optional[CharacterBlueprint] = None,
    name: Optional[str] = None,
) -> str:
    """Infers the anatomical and equipment archetype for silhouette specialization."""
    if blueprint is not None:
        if getattr(blueprint, "archetype", None):
            return blueprint.archetype.lower().strip()
        target = f"{blueprint.character_id} {blueprint.name}".lower()
    elif name is not None:
        target = name.lower()
    else:
        return "hero"

    if any(k in target for k in ["knight", "warrior", "paladin", "soldier", "guard"]):
        return "knight"
    if any(k in target for k in ["mage", "wizard", "sorcerer", "cleric", "priest", "witch"]):
        return "mage"
    if any(k in target for k in ["goblin", "rogue", "orc", "thief", "assassin", "monster", "imp"]):
        return "goblin"
    if any(k in target for k in ["brute", "dwarf", "barbarian", "heavy", "golem", "giant"]):
        return "heavy_brute"
    return "hero"


def legacy_args_to_blueprint(
    name: str = "hero",
    width: int = 16,
    height: int = 16,
    shirt_color: str = "#597dce",
    pants_color: str = "#4e4a4e",
    hair_color: str = "#442434",
    skin_color: str = "#d2aa99",
) -> CharacterBlueprint:
    """Adapts legacy flat tool arguments into a typed CharacterBlueprint specification."""
    archetype = resolve_archetype(name=name)
    return CharacterBlueprint(
        character_id=name.lower().replace(" ", "_"),
        name=name,
        size=(width, height),
        proportion="chibi_1_2",
        archetype=archetype,
        colors={
            "skin": skin_color,
            "skin_shadow": "#854c30",
            "hair": hair_color,
            "shirt": shirt_color,
            "shirt_shadow": "#30346d",
            "pants": pants_color,
            "pants_shadow": "#140c1c",
            "outline": "#140c1c",
            "eyes": "#140c1c",
            "weapon": "#8595a1",
            "weapon_hilt": "#d27d2c",
            "accent": "#d04648",
            "weapon_glow": "#6dc2ca",
        },
        views=["down"],
        animations={
            "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
            "walk": CharacterAnimationSpec(frames=4, duration_ms=120, loop=True),
            "attack": CharacterAnimationSpec(frames=3, duration_ms=100, loop=False),
            "hurt": CharacterAnimationSpec(frames=2, duration_ms=150, loop=False),
        },
        pivot=(0.5, 0.9),
    )


def blueprint_to_style(blueprint: CharacterBlueprint) -> CharacterStyle:
    """Extracts CharacterStyle colors from blueprint colors dictionary with sensible fallbacks."""
    colors = blueprint.colors
    return CharacterStyle(
        skin=colors.get("skin", "#d2aa99"),
        skin_shadow=colors.get("skin_shadow", "#854c30"),
        hair=colors.get("hair", "#442434"),
        shirt=colors.get("shirt", colors.get("primary_clothing", "#597dce")),
        shirt_shadow=colors.get("shirt_shadow", "#30346d"),
        pants=colors.get("pants", colors.get("secondary_clothing", "#4e4a4e")),
        pants_shadow=colors.get("pants_shadow", "#140c1c"),
        outline=colors.get("outline", "#140c1c"),
        eyes=colors.get("eyes", "#140c1c"),
        weapon=colors.get("weapon", colors.get("gear", "#8595a1")),
        weapon_hilt=colors.get("weapon_hilt", "#d27d2c"),
        accent=colors.get("accent", "#d04648"),
        weapon_glow=colors.get("weapon_glow", "#6dc2ca"),
        weapon_highlight=colors.get("weapon_highlight", "#deeed6"),
        buckle=colors.get("buckle", "#dad45e"),
    )


# =============================================================================
# ARCHETYPE RENDERERS
# =============================================================================

def _render_knight(
    c_shadow: PixelCanvas,
    c_body: PixelCanvas,
    c_clothes: PixelCanvas,
    c_gear: PixelCanvas,
    scale: int,
    mid_x: int,
    w: int,
    h: int,
    style: CharacterStyle,
    action: str,
    step: int,
    direction: str,
    bob_y: int,
    leg_l: int,
    leg_r: int,
    thrust: int,
) -> None:
    head_y = (3 + bob_y) * scale
    torso_y = head_y + 4 * scale
    legs_y = torso_y + 4 * scale

    # 1. Body (Face opening & Hands)
    if direction == "down":
        for y in range(head_y + 2 * scale, head_y + 4 * scale):
            for x in range(mid_x - 2 * scale, mid_x + 2 * scale):
                c_body.put_pixel(x, y, style.skin)
        c_body.put_pixel(mid_x - 2 * scale, head_y + 2 * scale, style.eyes)
        c_body.put_pixel(mid_x + 1 * scale, head_y + 2 * scale, style.eyes)
        c_body.draw_rect(mid_x - 4 * scale, torso_y + 2 * scale, 1 * scale, 2 * scale, fill=style.skin)
        c_body.draw_rect(mid_x + 3 * scale, torso_y + 2 * scale, 1 * scale, 2 * scale, fill=style.skin)
    elif direction in ("left", "right"):
        facing_mult = -1 if direction == "left" else 1
        for y in range(head_y + 2 * scale, head_y + 4 * scale):
            for x in range(mid_x - 2 * scale, mid_x + 2 * scale):
                c_body.put_pixel(x, y, style.skin)
        eye_x = mid_x - 2 * scale if direction == "left" else mid_x + 1 * scale
        c_body.put_pixel(eye_x, head_y + 2 * scale, style.eyes)
        c_body.draw_rect(mid_x + facing_mult * 3 * scale, torso_y + 2 * scale, 1 * scale, 2 * scale, fill=style.skin)

    # 2. Clothes (Helmet, Plume, Pauldrons, Breastplate, Greaves)
    # Plume atop helmet
    c_clothes.draw_rect(mid_x - 1 * scale, head_y - 2 * scale, 2 * scale, 1 * scale, fill=style.accent)
    c_clothes.put_pixel(mid_x - 1 * scale, head_y - 1 * scale, style.accent)

    # Helmet skull
    c_clothes.draw_rect(mid_x - 2 * scale, head_y - 1 * scale, 4 * scale, 1 * scale, fill=style.weapon)
    c_clothes.put_pixel(mid_x - 1 * scale, head_y - 1 * scale, style.weapon_highlight)
    c_clothes.draw_rect(mid_x - 3 * scale, head_y, 6 * scale, 2 * scale, fill=style.weapon)
    c_clothes.put_pixel(mid_x - 2 * scale, head_y, style.weapon_highlight)

    if direction == "down":
        c_clothes.draw_rect(mid_x - 3 * scale, head_y + 2 * scale, 1 * scale, 2 * scale, fill=style.weapon)
        c_clothes.draw_rect(mid_x + 2 * scale, head_y + 2 * scale, 1 * scale, 2 * scale, fill=style.weapon)
        c_clothes.draw_rect(mid_x - 2 * scale, head_y + 4 * scale, 4 * scale, 1 * scale, fill=style.outline)
    elif direction == "up":
        c_clothes.draw_rect(mid_x - 3 * scale, head_y + 2 * scale, 6 * scale, 3 * scale, fill=style.weapon)

    # Pauldrons (Shoulders extended 1px wider than torso)
    c_clothes.draw_rect(mid_x - 4 * scale, torso_y, 1 * scale, 2 * scale, fill=style.weapon)
    c_clothes.draw_rect(mid_x + 3 * scale, torso_y, 1 * scale, 2 * scale, fill=style.weapon)

    # Breastplate
    c_clothes.draw_rect(mid_x - 3 * scale, torso_y, 6 * scale, 3 * scale, fill=style.shirt)
    c_clothes.put_pixel(mid_x - 2 * scale, torso_y, style.shirt_highlight)
    c_clothes.put_pixel(mid_x - 1 * scale, torso_y, style.shirt_highlight)
    c_clothes.put_pixel(mid_x - 2 * scale, torso_y + 1 * scale, style.shirt_highlight)

    # Belt / Tassets
    c_clothes.draw_rect(mid_x - 3 * scale, torso_y + 3 * scale, 6 * scale, 1 * scale, fill=style.belt)
    c_clothes.put_pixel(mid_x - 1 * scale, torso_y + 3 * scale, style.buckle)

    # Greaves / Legs
    c_clothes.draw_rect(mid_x - 3 * scale, legs_y, 2 * scale, (3 + leg_l) * scale, fill=style.pants, outline=style.pants_shadow)
    c_clothes.draw_rect(mid_x + 1 * scale, legs_y, 2 * scale, (3 + leg_r) * scale, fill=style.pants, outline=style.pants_shadow)

    # 3. Gear (Broadsword with Gleam and Crossguard)
    if direction in ("down", "right"):
        wx = mid_x + (4 + thrust) * scale
        wy = torso_y + 1 * scale
        c_gear.draw_line(wx, wy - 3 * scale, wx, wy + 2 * scale, style.weapon)
        c_gear.put_pixel(wx, wy - 3 * scale, style.weapon_highlight)
        c_gear.draw_line(wx - 1 * scale, wy, wx + 1 * scale, wy, style.weapon_hilt)
        c_gear.put_pixel(wx, wy + 3 * scale, style.weapon_hilt)
    elif direction == "left":
        wx = mid_x - (5 + thrust) * scale
        wy = torso_y + 1 * scale
        c_gear.draw_line(wx, wy - 3 * scale, wx, wy + 2 * scale, style.weapon)
        c_gear.draw_line(wx - 1 * scale, wy, wx + 1 * scale, wy, style.weapon_hilt)


def _render_mage(
    c_shadow: PixelCanvas,
    c_body: PixelCanvas,
    c_clothes: PixelCanvas,
    c_gear: PixelCanvas,
    scale: int,
    mid_x: int,
    w: int,
    h: int,
    style: CharacterStyle,
    action: str,
    step: int,
    direction: str,
    bob_y: int,
    leg_l: int,
    leg_r: int,
    thrust: int,
) -> None:
    head_y = (3 + bob_y) * scale
    torso_y = head_y + 4 * scale
    legs_y = torso_y + 3 * scale

    # 1. Body (Glowing Arcane Eyes under Hood)
    if direction != "up":
        for y in range(head_y + 1 * scale, head_y + 4 * scale):
            for x in range(mid_x - 2 * scale, mid_x + 2 * scale):
                c_body.put_pixel(x, y, style.skin_shadow)
        c_body.put_pixel(mid_x - 2 * scale, head_y + 2 * scale, style.weapon_glow)
        c_body.put_pixel(mid_x + 1 * scale, head_y + 2 * scale, style.weapon_glow)
        c_body.put_pixel(mid_x + 4 * scale, torso_y + 2 * scale, style.skin)

    # 2. Clothes (Pointed Cowl / Hood & Flared Robes)
    # Pointed Cowl tip
    c_clothes.put_pixel(mid_x - 1 * scale, head_y - 2 * scale, style.shirt)
    c_clothes.put_pixel(mid_x, head_y - 2 * scale, style.shirt_highlight)
    c_clothes.draw_rect(mid_x - 2 * scale, head_y - 1 * scale, 4 * scale, 1 * scale, fill=style.shirt)
    c_clothes.put_pixel(mid_x - 1 * scale, head_y - 1 * scale, style.shirt_highlight)

    # Hood Brow & Overhang (8px wide)
    c_clothes.draw_rect(mid_x - 4 * scale, head_y, 8 * scale, 1 * scale, fill=style.shirt)
    c_clothes.draw_rect(mid_x - 4 * scale, head_y + 1 * scale, 1 * scale, 2 * scale, fill=style.shirt_shadow)
    c_clothes.draw_rect(mid_x + 3 * scale, head_y + 1 * scale, 1 * scale, 2 * scale, fill=style.shirt_shadow)

    if direction == "up":
        c_clothes.draw_rect(mid_x - 3 * scale, head_y + 1 * scale, 6 * scale, 3 * scale, fill=style.shirt)

    # Flared Wizard Robe (Tapering from 6px at chest to 10px at hem)
    c_clothes.draw_rect(mid_x - 3 * scale, torso_y, 6 * scale, 3 * scale, fill=style.shirt)
    # Central mystic sash
    for y in range(torso_y, min(h - 2 * scale, legs_y + 4 * scale)):
        c_clothes.put_pixel(mid_x - 1 * scale, y, style.accent)
        c_clothes.put_pixel(mid_x, y, style.accent)

    # Flared Hemline
    for y in range(legs_y, min(h - 2 * scale, legs_y + 4 * scale)):
        w_offset = ((y - legs_y) // 2 + 1) * scale
        for x in range(mid_x - 3 * scale - w_offset, mid_x + 3 * scale + w_offset):
            if c_clothes.get_pixel(x, y)[3] == 0:
                c_clothes.put_pixel(x, y, style.shirt if x % 2 == 0 else style.shirt_shadow)

    # 3. Gear (Mystic Staff with Glowing Crystal Orb)
    wx = mid_x + (4 + thrust) * scale
    wy = torso_y
    c_gear.draw_line(wx, wy - 1 * scale, wx, wy + 5 * scale, style.weapon_hilt)
    c_gear.put_pixel(wx, wy - 3 * scale, style.weapon_glow)
    c_gear.put_pixel(wx - 1 * scale, wy - 2 * scale, style.weapon_glow)
    c_gear.put_pixel(wx, wy - 2 * scale, style.weapon_highlight)
    c_gear.put_pixel(wx + 1 * scale, wy - 2 * scale, style.weapon_glow)
    c_gear.put_pixel(wx, wy - 1 * scale, style.weapon_hilt)

    if action == "attack" and step == 1:
        c_gear.put_pixel(wx + 1 * scale, wy - 3 * scale, style.weapon_glow)
        c_gear.put_pixel(wx + 2 * scale, wy - 2 * scale, style.weapon_glow)


def _render_goblin(
    c_shadow: PixelCanvas,
    c_body: PixelCanvas,
    c_clothes: PixelCanvas,
    c_gear: PixelCanvas,
    scale: int,
    mid_x: int,
    w: int,
    h: int,
    style: CharacterStyle,
    action: str,
    step: int,
    direction: str,
    bob_y: int,
    leg_l: int,
    leg_r: int,
    thrust: int,
) -> None:
    head_y = (4 + bob_y) * scale
    torso_y = head_y + 3 * scale
    legs_y = torso_y + 4 * scale

    # 1. Body (Green Skin, Lateral Pointed Ears, Beady Eyes)
    # Pointed Ears extending out laterally
    c_body.put_pixel(mid_x - 5 * scale, head_y + 1 * scale, style.skin)
    c_body.put_pixel(mid_x - 4 * scale, head_y + 2 * scale, style.skin_shadow)
    c_body.put_pixel(mid_x + 4 * scale, head_y + 1 * scale, style.skin)
    c_body.put_pixel(mid_x + 3 * scale, head_y + 2 * scale, style.skin_shadow)

    # Goblin Skull
    c_body.draw_rect(mid_x - 3 * scale, head_y, 6 * scale, 3 * scale, fill=style.skin)
    c_body.put_pixel(mid_x - 1 * scale, head_y + 3 * scale, style.skin_shadow)
    c_body.put_pixel(mid_x, head_y + 3 * scale, style.skin_shadow)

    if direction != "up":
        c_body.put_pixel(mid_x - 2 * scale, head_y + 1 * scale, style.buckle)
        c_body.put_pixel(mid_x + 1 * scale, head_y + 1 * scale, style.buckle)

    # Skinny arms
    c_body.draw_rect(mid_x - 4 * scale, torso_y + 2 * scale, 1 * scale, 2 * scale, fill=style.skin)
    c_body.draw_rect(mid_x + 3 * scale, torso_y + 2 * scale, 1 * scale, 2 * scale, fill=style.skin)

    # 2. Clothes (Ragged Tunic, Diagonal Bandolier, Stealth Pants)
    c_clothes.draw_rect(mid_x - 3 * scale, torso_y, 6 * scale, 3 * scale, fill=style.shirt)
    # Diagonal Bandolier
    c_clothes.put_pixel(mid_x - 2 * scale, torso_y, style.belt)
    c_clothes.put_pixel(mid_x - 1 * scale, torso_y + 1 * scale, style.belt)
    c_clothes.put_pixel(mid_x, torso_y + 2 * scale, style.belt)

    # Jagged hemline
    c_clothes.put_pixel(mid_x - 3 * scale, torso_y + 3 * scale, style.shirt_shadow)
    c_clothes.put_pixel(mid_x - 1 * scale, torso_y + 3 * scale, style.shirt_shadow)
    c_clothes.put_pixel(mid_x + 1 * scale, torso_y + 3 * scale, style.shirt_shadow)

    # Crouching legs
    c_clothes.draw_rect(mid_x - 3 * scale, legs_y, 2 * scale, (3 + leg_l) * scale, fill=style.pants, outline=style.pants_shadow)
    c_clothes.draw_rect(mid_x + 1 * scale, legs_y, 2 * scale, (3 + leg_r) * scale, fill=style.pants, outline=style.pants_shadow)

    # 3. Gear (Serrated Curved Dagger)
    wx = mid_x + (4 + thrust) * scale
    wy = torso_y + 2 * scale
    c_gear.put_pixel(wx, wy - 2 * scale, style.weapon)
    c_gear.put_pixel(wx - 1 * scale, wy - 1 * scale, style.weapon)
    c_gear.put_pixel(wx, wy, style.weapon_hilt)
    c_gear.put_pixel(wx + 1 * scale, wy, style.weapon_hilt)


def _render_heavy_brute(
    c_shadow: PixelCanvas,
    c_body: PixelCanvas,
    c_clothes: PixelCanvas,
    c_gear: PixelCanvas,
    scale: int,
    mid_x: int,
    w: int,
    h: int,
    style: CharacterStyle,
    action: str,
    step: int,
    direction: str,
    bob_y: int,
    leg_l: int,
    leg_r: int,
    thrust: int,
) -> None:
    head_y = (3 + bob_y) * scale
    torso_y = head_y + 4 * scale
    legs_y = torso_y + 4 * scale

    # 1. Body (Broad Face & Bushy Beard)
    c_body.draw_rect(mid_x - 3 * scale, head_y, 6 * scale, 4 * scale, fill=style.skin)
    if direction != "up":
        c_body.put_pixel(mid_x - 2 * scale, head_y + 1 * scale, style.eyes)
        c_body.put_pixel(mid_x + 1 * scale, head_y + 1 * scale, style.eyes)

    # Thick bushy beard cascading over upper chest
    c_clothes.draw_rect(mid_x - 3 * scale, head_y + 2 * scale, 6 * scale, 3 * scale, fill=style.hair)
    c_clothes.put_pixel(mid_x - 1 * scale, head_y + 5 * scale, style.hair)
    c_clothes.put_pixel(mid_x, head_y + 5 * scale, style.hair)

    # 2. Clothes (Iron Brow Cap, Broad 8px Torso, Heavy Studded Belt)
    c_clothes.draw_rect(mid_x - 3 * scale, head_y - 1 * scale, 6 * scale, 2 * scale, fill=style.weapon)
    c_clothes.put_pixel(mid_x - 1 * scale, head_y - 1 * scale, style.weapon_highlight)

    # Broad 8px Torso
    c_clothes.draw_rect(mid_x - 4 * scale, torso_y, 8 * scale, 4 * scale, fill=style.shirt)
    c_clothes.draw_rect(mid_x - 4 * scale, torso_y + 3 * scale, 8 * scale, 1 * scale, fill=style.belt)
    c_clothes.put_pixel(mid_x - 1 * scale, torso_y + 3 * scale, style.buckle)

    # Short Stocky Legs
    c_clothes.draw_rect(mid_x - 4 * scale, legs_y, 3 * scale, (2 + leg_l) * scale, fill=style.pants, outline=style.pants_shadow)
    c_clothes.draw_rect(mid_x + 1 * scale, legs_y, 3 * scale, (2 + leg_r) * scale, fill=style.pants, outline=style.pants_shadow)

    # 3. Gear (Heavy Battleaxe)
    wx = mid_x + (5 + thrust) * scale
    wy = torso_y + 1 * scale
    c_gear.draw_line(wx, wy - 3 * scale, wx, wy + 4 * scale, style.weapon_hilt)
    c_gear.draw_rect(wx - 2 * scale, wy - 2 * scale, 2 * scale, 2 * scale, fill=style.weapon)
    c_gear.draw_rect(wx + 1 * scale, wy - 2 * scale, 2 * scale, 2 * scale, fill=style.weapon)


def _render_hero(
    c_shadow: PixelCanvas,
    c_body: PixelCanvas,
    c_clothes: PixelCanvas,
    c_gear: PixelCanvas,
    scale: int,
    mid_x: int,
    w: int,
    h: int,
    style: CharacterStyle,
    action: str,
    step: int,
    direction: str,
    bob_y: int,
    leg_l: int,
    leg_r: int,
    thrust: int,
) -> None:
    head_y = (3 + bob_y) * scale
    torso_y = head_y + 4 * scale
    legs_y = torso_y + 4 * scale

    # 1. Body (Head, Face, Hands)
    c_body.draw_rect(mid_x - 3 * scale, head_y, 6 * scale, 4 * scale, fill=style.skin)
    c_body.draw_rect(mid_x - 2 * scale, head_y + 4 * scale, 4 * scale, 1 * scale, fill=style.skin_shadow)

    if direction == "down":
        c_body.put_pixel(mid_x - 2 * scale, head_y + 2 * scale, style.eyes)
        c_body.put_pixel(mid_x + 1 * scale, head_y + 2 * scale, style.eyes)
        c_body.draw_rect(mid_x - 4 * scale, torso_y + 1 * scale, 1 * scale, 3 * scale, fill=style.skin)
        c_body.draw_rect(mid_x + 3 * scale, torso_y + 1 * scale, 1 * scale, 3 * scale, fill=style.skin)
    elif direction in ("left", "right"):
        eye_x = mid_x - 2 * scale if direction == "left" else mid_x + 1 * scale
        c_body.put_pixel(eye_x, head_y + 2 * scale, style.eyes)
        arm_x = mid_x - 3 * scale if direction == "left" else mid_x + 2 * scale
        c_body.draw_rect(arm_x, torso_y + 1 * scale, 1 * scale, 3 * scale, fill=style.skin)

    # 2. Clothes (Volumetric Hair, Tunic, Belt, Boots)
    # Hair volume past skull perimeter
    c_clothes.draw_rect(mid_x - 3 * scale, head_y - 1 * scale, 6 * scale, 2 * scale, fill=style.hair)
    c_clothes.put_pixel(mid_x - 2 * scale, head_y - 1 * scale, style.hair_highlight)
    c_clothes.draw_rect(mid_x - 4 * scale, head_y, 1 * scale, 3 * scale, fill=style.hair)
    c_clothes.draw_rect(mid_x + 3 * scale, head_y, 1 * scale, 3 * scale, fill=style.hair)

    if direction == "up":
        c_clothes.draw_rect(mid_x - 3 * scale, head_y + 1 * scale, 6 * scale, 4 * scale, fill=style.hair)

    # Tunic & Collar
    c_clothes.draw_rect(mid_x - 3 * scale, torso_y, 6 * scale, 3 * scale, fill=style.shirt)
    c_clothes.put_pixel(mid_x - 2 * scale, torso_y, style.shirt_highlight)
    # Belt
    c_clothes.draw_rect(mid_x - 3 * scale, torso_y + 3 * scale, 6 * scale, 1 * scale, fill=style.belt)
    c_clothes.put_pixel(mid_x - 1 * scale, torso_y + 3 * scale, style.buckle)

    # Pants & Boots
    c_clothes.draw_rect(mid_x - 3 * scale, legs_y, 2 * scale, (3 + leg_l) * scale, fill=style.pants, outline=style.pants_shadow)
    c_clothes.draw_rect(mid_x + 1 * scale, legs_y, 2 * scale, (3 + leg_r) * scale, fill=style.pants, outline=style.pants_shadow)

    # 3. Gear (Adventurer Sword)
    if direction in ("down", "right"):
        wx = mid_x + (4 + thrust) * scale
        wy = torso_y + 1 * scale
        c_gear.draw_line(wx, wy - 3 * scale, wx, wy + 2 * scale, style.weapon)
        c_gear.draw_line(wx - 1 * scale, wy, wx + 1 * scale, wy, style.weapon_hilt)


# =============================================================================
# PRIMARY FRAME & PROJECT GENERATION
# =============================================================================

def generate_character_frame(
    width: int = 16,
    height: int = 16,
    style: Optional[CharacterStyle] = None,
    action: str = "idle",
    frame_step: int = 0,
    direction: str = "down",
    archetype: Optional[str] = None,
    blueprint: Optional[CharacterBlueprint] = None,
    palette_name: Optional[str] = None,
) -> Dict[str, Image.Image]:
    """
    Renders layered frame images for a character across specialized anatomical archetypes.
    Returns dict: {"Shadow": img, "Body": img, "Clothes": img, "Gear": img}
    """
    if style is None:
        style = CharacterStyle()

    scale = max(1, width // 16)
    mid_x = width // 2

    canvas_shadow = PixelCanvas(width, height)
    canvas_body = PixelCanvas(width, height)
    canvas_clothes = PixelCanvas(width, height)
    canvas_gear = PixelCanvas(width, height)

    bob_y = 0
    leg_l_offset = 0
    leg_r_offset = 0
    weapon_thrust = 0

    if action == "idle":
        bob_y = 1 if frame_step % 2 == 1 else 0
    elif action == "walk":
        step = frame_step % 4
        if step == 0:
            leg_l_offset = -1
            leg_r_offset = 1
            bob_y = 1
        elif step == 1:
            bob_y = 0
        elif step == 2:
            leg_l_offset = 1
            leg_r_offset = -1
            bob_y = 1
        elif step == 3:
            bob_y = 0
    elif action == "attack":
        step = frame_step % 3
        if step == 0:
            weapon_thrust = -1
            bob_y = 0
        elif step == 1:
            weapon_thrust = 2
            bob_y = 1
        elif step == 2:
            weapon_thrust = 1
            bob_y = 0
    elif action == "hurt":
        bob_y = 1
        mid_x -= 1 * scale

    # Ground shadow (100% binary alpha)
    shadow_y = height - 2 * scale
    shadow_rx = 5 * scale if archetype == "mage" else 4 * scale
    canvas_shadow.draw.ellipse(
        [mid_x - shadow_rx, shadow_y, mid_x + shadow_rx - 1 * scale, shadow_y + 1 * scale],
        fill=style.outline
    )

    # Determine archetype
    resolved_arch = archetype or (blueprint.archetype if blueprint else None) or resolve_archetype(blueprint)

    # Dispatch to specialized archetype renderer
    if resolved_arch == "knight":
        _render_knight(
            canvas_shadow, canvas_body, canvas_clothes, canvas_gear,
            scale, mid_x, width, height, style, action, frame_step, direction,
            bob_y, leg_l_offset, leg_r_offset, weapon_thrust
        )
    elif resolved_arch == "mage":
        _render_mage(
            canvas_shadow, canvas_body, canvas_clothes, canvas_gear,
            scale, mid_x, width, height, style, action, frame_step, direction,
            bob_y, leg_l_offset, leg_r_offset, weapon_thrust
        )
    elif resolved_arch == "goblin":
        _render_goblin(
            canvas_shadow, canvas_body, canvas_clothes, canvas_gear,
            scale, mid_x, width, height, style, action, frame_step, direction,
            bob_y, leg_l_offset, leg_r_offset, weapon_thrust
        )
    elif resolved_arch == "heavy_brute":
        _render_heavy_brute(
            canvas_shadow, canvas_body, canvas_clothes, canvas_gear,
            scale, mid_x, width, height, style, action, frame_step, direction,
            bob_y, leg_l_offset, leg_r_offset, weapon_thrust
        )
    else:
        _render_hero(
            canvas_shadow, canvas_body, canvas_clothes, canvas_gear,
            scale, mid_x, width, height, style, action, frame_step, direction,
            bob_y, leg_l_offset, leg_r_offset, weapon_thrust
        )

    # Palette quantization if palette_name provided
    if palette_name:
        try:
            pal = GamePalette.from_name(palette_name)
            canvas_shadow.quantize_to_palette(pal)
            canvas_body.quantize_to_palette(pal)
            canvas_clothes.quantize_to_palette(pal)
            canvas_gear.quantize_to_palette(pal)
        except Exception:
            pass

    return {
        "Shadow": canvas_shadow.image,
        "Body": canvas_body.image,
        "Clothes": canvas_clothes.image,
        "Gear": canvas_gear.image,
    }


def build_animated_character_project(
    width: int = 16,
    height: int = 16,
    style: Optional[CharacterStyle] = None,
    palette_name: Optional[str] = None,
    blueprint: Optional[CharacterBlueprint] = None,
    profile: Optional[ArtProfile] = None,
) -> AsepriteProject:
    """
    Builds an Aseprite project containing animations defined by CharacterBlueprint.
    Falls back gracefully to standard animations if legacy parameters are provided.
    """
    effective_palette = palette_name or (profile.palette_name if profile else "db16")

    if blueprint is not None:
        width, height = blueprint.size
        style = blueprint_to_style(blueprint)
        archetype = resolve_archetype(blueprint)
        animations_dict = blueprint.animations if blueprint.animations else {
            "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
            "walk": CharacterAnimationSpec(frames=4, duration_ms=120, loop=True),
        }
    else:
        style = style or CharacterStyle()
        archetype = resolve_archetype(name=None)
        animations_dict = {
            "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
            "walk": CharacterAnimationSpec(frames=4, duration_ms=120, loop=True),
            "attack": CharacterAnimationSpec(frames=3, duration_ms=100, loop=False),
            "hurt": CharacterAnimationSpec(frames=2, duration_ms=150, loop=False),
        }

    project = AsepriteProject(width, height)
    project.set_layer_name(project.sprite.layers[0].name, "Shadow")
    project.add_layer("Body")
    project.add_layer("Clothes")
    project.add_layer("Gear")

    frame_cursor = 0

    for anim_name, anim_spec in animations_dict.items():
        anim_start = frame_cursor
        duration = anim_spec.duration_ms
        frame_count = max(1, anim_spec.frames)

        for f in range(frame_count):
            layers = generate_character_frame(
                width, height, style,
                action=anim_name, frame_step=f,
                archetype=archetype, blueprint=blueprint,
                palette_name=effective_palette,
            )
            project.add_animation_frame(duration_ms=duration, layer_images=layers)
            frame_cursor += 1

        project.add_tag(anim_name, anim_start, frame_cursor - 1)

    return project
