"""
Procedural pixel art character and animation generator.
Generates multi-layered, multi-frame animated sprites (Idle, Walk, Attack, Hurt)
with customizable palettes, dimensions, and game engine tags.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from PIL import Image

from libresprite_game_mcp.core.palettes import GamePalette, RGBA, hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas
from libresprite_game_mcp.core.aseprite_file import AsepriteProject


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

    # Determine canvas scale factor (base is 16x16)
    scale = max(1, width // 16)
    mid_x = width // 2

    canvas_shadow = PixelCanvas(width, height)
    canvas_body = PixelCanvas(width, height)
    canvas_clothes = PixelCanvas(width, height)
    canvas_gear = PixelCanvas(width, height)

    # Bobbing and leg positions based on action and frame_step
    bob_y = 0
    leg_l_offset = 0
    leg_r_offset = 0
    arm_l_angle = 0
    arm_r_angle = 0
    weapon_thrust = 0

    if action == "idle":
        # 2-frame subtle breathing bob
        bob_y = 1 if frame_step % 2 == 1 else 0
    elif action == "walk":
        # 4-frame walking cycle
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
        # 3-frame attack
        step = frame_step % 3
        if step == 0:
            weapon_thrust = -1  # windup
            bob_y = 0
        elif step == 1:
            weapon_thrust = 3   # slash/thrust forward
            bob_y = 1
        elif step == 2:
            weapon_thrust = 1   # recovery
            bob_y = 0
    elif action == "hurt":
        bob_y = 1
        # Knockback offset
        mid_x -= 1

    # Ground shadow (under feet)
    shadow_y = height - 2 * scale
    canvas_shadow.draw.ellipse(
        [mid_x - 4 * scale, shadow_y, mid_x + 3 * scale, shadow_y + 1 * scale],
        fill=(0, 0, 0, 110)
    )

    # Coordinates
    head_y = (3 + bob_y) * scale
    head_r = 3 * scale

    torso_y = head_y + 4 * scale
    torso_h = 4 * scale

    legs_y = torso_y + torso_h
    legs_h = 3 * scale

    # 1. Legs (Body & Pants)
    # Left leg
    canvas_clothes.draw_rect(
        mid_x - 3 * scale, legs_y, 2 * scale, (legs_h + leg_l_offset) * scale,
        fill=style.pants, outline=style.pants_shadow
    )
    # Right leg
    canvas_clothes.draw_rect(
        mid_x + 1 * scale, legs_y, 2 * scale, (legs_h + leg_r_offset) * scale,
        fill=style.pants, outline=style.pants_shadow
    )

    # 2. Torso / Shirt
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

    # 5. Hair (Top and sides)
    canvas_clothes.draw_rect(
        mid_x - 3 * scale, head_y - 1 * scale, 6 * scale, 2 * scale,
        fill=style.hair
    )

    # 6. Face / Eyes (depending on direction)
    if direction == "down":
        # Two eyes looking forward
        canvas_body.put_pixel(mid_x - 2 * scale, head_y + 2 * scale, style.eyes)
        canvas_body.put_pixel(mid_x + 1 * scale, head_y + 2 * scale, style.eyes)
    elif direction == "left":
        canvas_body.put_pixel(mid_x - 2 * scale, head_y + 2 * scale, style.eyes)
    elif direction == "right":
        canvas_body.put_pixel(mid_x + 1 * scale, head_y + 2 * scale, style.eyes)
    # If up, back of head (hair covers)
    elif direction == "up":
        canvas_clothes.draw_rect(
            mid_x - 3 * scale, head_y, 6 * scale, 3 * scale,
            fill=style.hair
        )

    # 7. Weapon / Gear
    if direction in ("down", "right"):
        wx = mid_x + (4 + weapon_thrust) * scale
        wy = torso_y + 1 * scale
        # Blade
        canvas_gear.draw_line(wx, wy - 3 * scale, wx, wy + 2 * scale, style.weapon)
        # Hilt
        canvas_gear.draw_line(wx - 1 * scale, wy, wx + 1 * scale, wy, style.weapon_hilt)

    # Return composited layer images
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
) -> AsepriteProject:
    """
    Builds a full Aseprite project containing Idle, Walk, Attack, and Hurt animations
    with standard frame durations and animation tags.
    """
    project = AsepriteProject(width, height)
    style = style or CharacterStyle()

    # Pre-configure layers
    project.set_layer_name(project.sprite.layers[0].name, "Shadow")
    project.add_layer("Body")
    project.add_layer("Clothes")
    project.add_layer("Gear")

    frame_cursor = 0

    # 1. Idle Animation (2 frames, 300ms each)
    idle_start = frame_cursor
    for f in range(2):
        layers = generate_character_frame(width, height, style, "idle", f)
        project.add_animation_frame(duration_ms=300, layer_images=layers)
        frame_cursor += 1
    project.add_tag("idle", idle_start, frame_cursor - 1)

    # 2. Walk Animation (4 frames, 120ms each)
    walk_start = frame_cursor
    for f in range(4):
        layers = generate_character_frame(width, height, style, "walk", f)
        project.add_animation_frame(duration_ms=120, layer_images=layers)
        frame_cursor += 1
    project.add_tag("walk", walk_start, frame_cursor - 1)

    # 3. Attack Animation (3 frames, 100ms each)
    attack_start = frame_cursor
    for f in range(3):
        layers = generate_character_frame(width, height, style, "attack", f)
        project.add_animation_frame(duration_ms=100, layer_images=layers)
        frame_cursor += 1
    project.add_tag("attack", attack_start, frame_cursor - 1)

    # 4. Hurt Animation (2 frames, 150ms each)
    hurt_start = frame_cursor
    for f in range(2):
        layers = generate_character_frame(width, height, style, "hurt", f)
        project.add_animation_frame(duration_ms=150, layer_images=layers)
        frame_cursor += 1
    project.add_tag("hurt", hurt_start, frame_cursor - 1)

    return project
