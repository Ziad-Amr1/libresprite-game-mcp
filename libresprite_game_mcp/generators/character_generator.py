"""
Procedural pixel art character and animation generator.
Accepts structured CharacterBlueprint and ArtProfile specifications or legacy style parameters.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
from PIL import Image

from libresprite_game_mcp.core.palettes import GamePalette, RGBA, hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas
from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.models.schemas import CharacterBlueprint, CharacterAnimationSpec, ArtProfile


class CharacterStyle:
    """Color styling for character parts."""

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
    ):
        self.skin = hex_to_rgba(skin)
        self.skin_shadow = hex_to_rgba(skin_shadow)
        self.hair = hex_to_rgba(hair)
        self.shirt = hex_to_rgba(shirt)
        self.shirt_shadow = hex_to_rgba(shirt_shadow)
        self.pants = hex_to_rgba(pants)
        self.pants_shadow = hex_to_rgba(pants_shadow)
        self.outline = hex_to_rgba(outline)
        self.eyes = hex_to_rgba(eyes)
        self.weapon = hex_to_rgba(weapon)
        self.weapon_hilt = hex_to_rgba(weapon_hilt)


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
    return CharacterBlueprint(
        character_id=name.lower().replace(" ", "_"),
        name=name,
        size=(width, height),
        proportion="chibi_1_2",
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
    )


def generate_character_frame(
    width: int = 16,
    height: int = 16,
    style: Optional[CharacterStyle] = None,
    action: str = "idle",
    frame_step: int = 0,
    direction: str = "down",
) -> Dict[str, Image.Image]:
    """
    Renders layered frame images for a character:
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
            leg_l_offset = 0
            leg_r_offset = 0
            bob_y = 0
        elif step == 2:
            leg_l_offset = 1
            leg_r_offset = -1
            bob_y = 1
        elif step == 3:
            leg_l_offset = 0
            leg_r_offset = 0
            bob_y = 0
    elif action == "attack":
        step = frame_step % 3
        if step == 0:
            weapon_thrust = -1
            bob_y = 0
        elif step == 1:
            weapon_thrust = 3
            bob_y = 1
        elif step == 2:
            weapon_thrust = 1
            bob_y = 0
    elif action == "hurt":
        bob_y = 1
        mid_x -= 1

    # Ground shadow (under feet) - uses 100% opaque palette outline/shadow color to preserve binary alpha
    shadow_color = style.outline
    shadow_y = height - 2 * scale
    canvas_shadow.draw.ellipse(
        [mid_x - 4 * scale, shadow_y, mid_x + 3 * scale, shadow_y + 1 * scale],
        fill=shadow_color
    )

    # Proportions (Chibi 1:2 humanoid)
    head_y = (3 + bob_y) * scale
    torso_y = head_y + 4 * scale
    torso_h = 4 * scale
    legs_y = torso_y + torso_h
    legs_h = 3 * scale

    # 1. Legs (Pants)
    canvas_clothes.draw_rect(
        mid_x - 3 * scale, legs_y, 2 * scale, (legs_h + leg_l_offset) * scale,
        fill=style.pants, outline=style.pants_shadow
    )
    canvas_clothes.draw_rect(
        mid_x + 1 * scale, legs_y, 2 * scale, (legs_h + leg_r_offset) * scale,
        fill=style.pants, outline=style.pants_shadow
    )

    # 2. Torso (Shirt)
    canvas_clothes.draw_rect(
        mid_x - 3 * scale, torso_y, 6 * scale, torso_h,
        fill=style.shirt, outline=style.shirt_shadow
    )

    # 3. Arms / Hands
    canvas_body.draw_rect(
        mid_x - 4 * scale, torso_y + 1 * scale, 1 * scale, 3 * scale,
        fill=style.skin, outline=style.skin_shadow
    )
    canvas_body.draw_rect(
        mid_x + 3 * scale, torso_y + 1 * scale, 1 * scale, 3 * scale,
        fill=style.skin, outline=style.skin_shadow
    )

    # 4. Head (Skin)
    canvas_body.draw_rect(
        mid_x - 3 * scale, head_y, 6 * scale, 5 * scale,
        fill=style.skin, outline=style.outline
    )

    # 5. Hair
    canvas_clothes.draw_rect(
        mid_x - 3 * scale, head_y - 1 * scale, 6 * scale, 2 * scale,
        fill=style.hair
    )

    # 6. Face / Eyes
    if direction == "down":
        canvas_body.put_pixel(mid_x - 2 * scale, head_y + 2 * scale, style.eyes)
        canvas_body.put_pixel(mid_x + 1 * scale, head_y + 2 * scale, style.eyes)
    elif direction == "left":
        canvas_body.put_pixel(mid_x - 2 * scale, head_y + 2 * scale, style.eyes)
    elif direction == "right":
        canvas_body.put_pixel(mid_x + 1 * scale, head_y + 2 * scale, style.eyes)
    elif direction == "up":
        canvas_clothes.draw_rect(
            mid_x - 3 * scale, head_y, 6 * scale, 3 * scale,
            fill=style.hair
        )

    # 7. Weapon / Gear
    if direction in ("down", "right"):
        wx = mid_x + (4 + weapon_thrust) * scale
        wy = torso_y + 1 * scale
        canvas_gear.draw_line(wx, wy - 3 * scale, wx, wy + 2 * scale, style.weapon)
        canvas_gear.draw_line(wx - 1 * scale, wy, wx + 1 * scale, wy, style.weapon_hilt)

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
    
    Documented Limitations:
    - Supported Blueprint Fields: 'size', 'colors', 'animations' (tags, frame counts, duration_ms), 'pivot'.
    - Partially Supported / Phase 2: 'views' (currently defaults to front 'down' facing in 1.x foundation).
    - Hardcoded Proportions: Currently rigged for 'chibi_1_2' proportion template.
    """
    if blueprint is not None:
        width, height = blueprint.size
        style = blueprint_to_style(blueprint)
        animations_dict = blueprint.animations if blueprint.animations else {
            "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
            "walk": CharacterAnimationSpec(frames=4, duration_ms=120, loop=True),
        }
    else:
        style = style or CharacterStyle()
        # Default legacy animations
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
            layers = generate_character_frame(width, height, style, action=anim_name, frame_step=f)
            project.add_animation_frame(duration_ms=duration, layer_images=layers)
            frame_cursor += 1

        project.add_tag(anim_name, anim_start, frame_cursor - 1)

    return project
