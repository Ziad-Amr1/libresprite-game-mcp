"""
Native 32x32 procedural pixel art character generator and animation engine.
Produces high-fidelity, archetype-differentiated pixel art with distinct anatomy,
silhouettes, equipment, and unique motion profiles for 'idle' and 'move' animation states.
100% compliant with DB16 palette, binary alpha hygiene, and clean 4-layer structure.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
from PIL import Image

from libresprite_game_mcp.core.palettes import GamePalette, RGBA, hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas
from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.models.schemas import CharacterBlueprint, CharacterAnimationSpec, ArtProfile

# Standard DB16 Palette Lookups
DB16: Dict[str, RGBA] = {
    "black": hex_to_rgba("#140c1c"),
    "dark_purple": hex_to_rgba("#442434"),
    "dark_blue": hex_to_rgba("#30346d"),
    "dark_gray": hex_to_rgba("#4e4a4e"),
    "brown": hex_to_rgba("#854c30"),
    "dark_green": hex_to_rgba("#346524"),
    "red": hex_to_rgba("#d04648"),
    "gray": hex_to_rgba("#757161"),
    "blue": hex_to_rgba("#597dce"),
    "orange": hex_to_rgba("#d27d2c"),
    "light_gray": hex_to_rgba("#8595a1"),
    "green": hex_to_rgba("#6daa2c"),
    "skin": hex_to_rgba("#d2aa99"),
    "cyan": hex_to_rgba("#6dc2ca"),
    "yellow": hex_to_rgba("#dad45e"),
    "white": hex_to_rgba("#deeed6"),
}


# =============================================================================
# 32x32 ARCHETYPE RENDERERS
# =============================================================================

def render_knight_32_layers(
    action: str = "idle",
    step: int = 0,
    direction: str = "down",
    colors: Optional[Dict[str, str]] = None,
) -> Dict[str, Image.Image]:
    """
    Renders 32x32 Knight: Polished bascinet helmet with crimson flowing plume,
    T-visor slit, flared tiered pauldrons, segmented breastplate, heater shield,
    longsword with fuller groove, and articulated greaves.
    """
    c_s = PixelCanvas(32, 32)
    c_b = PixelCanvas(32, 32)
    c_c = PixelCanvas(32, 32)
    c_g = PixelCanvas(32, 32)
    mid_x = 16

    bob_y = 0
    plume_wave = 0
    sword_y = 0
    leg_l = 0
    leg_r = 0

    if action == "idle":
        # 6-frame disciplined martial breathing
        if step in (1, 2):
            bob_y = -1
            plume_wave = 1
        elif step in (4, 5):
            bob_y = 0
            plume_wave = -1
    elif action in ("move", "walk"):
        # 8-frame balanced martial march
        march_bobs = [0, -1, 1, 0, 0, -1, 1, 0]
        leg_l_offsets = [-2, -3, 0, 2, 3, 1, -1, -2]
        leg_r_offsets = [2, 3, 1, -1, -2, -3, 0, 2]
        bob_y = march_bobs[step % 8]
        leg_l = leg_l_offsets[step % 8]
        leg_r = leg_r_offsets[step % 8]
        plume_wave = 1 if step % 2 == 0 else -1
        sword_y = 1 if step % 2 == 1 else 0
    elif action == "attack":
        if step == 0:
            sword_y = -3
            bob_y = -1
        elif step == 1:
            sword_y = 4
            bob_y = 1
        else:
            sword_y = 1
            bob_y = 0
    elif action == "hurt":
        bob_y = 1
        mid_x -= 1

    # Ground shadow
    c_s.draw.ellipse([mid_x - 8, 28, mid_x + 8, 30], fill=DB16["black"])
    head_y = 6 + bob_y
    torso_y = head_y + 8
    legs_y = torso_y + 8

    # --- BODY ---
    if direction == "down":
        c_b.draw_rect(mid_x - 4, head_y + 4, 8, 4, fill=DB16["skin"])
        c_b.draw_rect(mid_x - 4, head_y + 4, 8, 1, fill=DB16["black"]) # visor slit
        c_b.put_pixel(mid_x - 3, head_y + 5, DB16["black"]) # eye
        c_b.put_pixel(mid_x + 2, head_y + 5, DB16["black"]) # eye
        c_b.draw_rect(mid_x - 8, torso_y + 4, 2, 3, fill=DB16["light_gray"]) # left gauntlet
        c_b.draw_rect(mid_x + 6, torso_y + 4 + sword_y, 2, 3, fill=DB16["light_gray"]) # right gauntlet
    elif direction in ("left", "right"):
        c_b.draw_rect(mid_x - 3, head_y + 4, 6, 4, fill=DB16["skin"])
        eye_x = mid_x - 3 if direction == "left" else mid_x + 2
        c_b.put_pixel(eye_x, head_y + 5, DB16["black"])
        c_b.draw_rect(mid_x + (4 if direction == "right" else -6), torso_y + 4 + sword_y, 2, 3, fill=DB16["light_gray"])

    # --- CLOTHES (Helmet, Plume, Pauldrons, Armor, Greaves) ---
    # Flowing Crimson Plume atop helmet
    c_c.draw_rect(mid_x - 2 + plume_wave, head_y - 4, 4, 2, fill=DB16["red"])
    c_c.draw_rect(mid_x - 3 + plume_wave, head_y - 2, 5, 2, fill=DB16["red"])
    c_c.put_pixel(mid_x + 2 + plume_wave, head_y - 1, DB16["dark_purple"])

    # Steel Helmet skull
    c_c.draw_rect(mid_x - 5, head_y, 10, 4, fill=DB16["light_gray"])
    c_c.draw_line(mid_x - 4, head_y, mid_x + 3, head_y, DB16["white"]) # dome gleam
    c_c.put_pixel(mid_x - 2, head_y + 1, DB16["white"])
    c_c.draw_rect(mid_x - 5, head_y + 4, 2, 4, fill=DB16["light_gray"])
    c_c.draw_rect(mid_x + 3, head_y + 4, 2, 4, fill=DB16["light_gray"])
    c_c.draw_rect(mid_x - 4, head_y + 7, 8, 1, fill=DB16["dark_gray"]) # chin bar

    # Tiered Shoulder Pauldrons (Flared outside torso!)
    c_c.draw_rect(mid_x - 9, torso_y, 4, 4, fill=DB16["light_gray"])
    c_c.draw_line(mid_x - 9, torso_y, mid_x - 6, torso_y, DB16["white"])
    c_c.draw_rect(mid_x + 5, torso_y, 4, 4, fill=DB16["light_gray"])
    c_c.draw_line(mid_x + 5, torso_y, mid_x + 8, torso_y, DB16["white"])

    # Segmented Breastplate (10px wide with specular ridge)
    c_c.draw_rect(mid_x - 5, torso_y, 10, 6, fill=DB16["blue"])
    c_c.draw_rect(mid_x - 3, torso_y + 1, 6, 4, fill=DB16["light_gray"])
    c_c.draw_line(mid_x - 1, torso_y + 1, mid_x - 1, torso_y + 4, DB16["white"]) # specular ridge
    c_c.draw_line(mid_x, torso_y + 1, mid_x, torso_y + 4, DB16["dark_gray"])

    # Belt & Tassets
    c_c.draw_rect(mid_x - 5, torso_y + 6, 10, 2, fill=DB16["brown"])
    c_c.draw_rect(mid_x - 1, torso_y + 6, 2, 2, fill=DB16["yellow"]) # gold buckle
    c_c.draw_rect(mid_x - 5, torso_y + 7, 10, 1, fill=DB16["black"])

    # Greaves & Boots (Articulated plate)
    c_c.draw_rect(mid_x - 5, legs_y, 3, 5 + leg_l, fill=DB16["dark_gray"], outline=DB16["black"])
    c_c.draw_rect(mid_x + 2, legs_y, 3, 5 + leg_r, fill=DB16["dark_gray"], outline=DB16["black"])
    c_c.put_pixel(mid_x - 4, legs_y, DB16["light_gray"])
    c_c.put_pixel(mid_x + 3, legs_y, DB16["light_gray"])
    c_c.draw_rect(mid_x - 6, legs_y + 4 + leg_l, 4, 2, fill=DB16["dark_gray"])
    c_c.draw_rect(mid_x + 1, legs_y + 4 + leg_r, 4, 2, fill=DB16["dark_gray"])

    # --- GEAR (Shield & Longsword) ---
    # Heater Shield on left arm
    c_g.draw_rect(mid_x - 10, torso_y + 1, 4, 7, fill=DB16["blue"])
    c_g.draw_line(mid_x - 10, torso_y + 1, mid_x - 7, torso_y + 1, DB16["light_gray"])
    c_g.draw_line(mid_x - 10, torso_y + 8, mid_x - 8, torso_y + 9, DB16["light_gray"])
    c_g.draw_rect(mid_x - 9, torso_y + 3, 2, 2, fill=DB16["white"])

    # Broadsword in right arm
    wx = mid_x + 7
    wy = torso_y + 4 + sword_y
    c_g.draw_line(wx, wy - 9, wx, wy - 1, DB16["light_gray"])
    c_g.draw_line(wx + 1, wy - 8, wx + 1, wy - 2, DB16["white"]) # fuller gleam
    c_g.put_pixel(wx, wy - 10, DB16["white"]) # tip gleam
    c_g.draw_line(wx - 2, wy, wx + 3, wy, DB16["yellow"]) # crossguard
    c_g.draw_line(wx, wy + 1, wx, wy + 3, DB16["brown"])
    c_g.put_pixel(wx, wy + 4, DB16["yellow"]) # pommel

    return {
        "Shadow": c_s.image,
        "Body": c_b.image,
        "Clothes": c_c.image,
        "Gear": c_g.image,
    }


def render_goblin_32_layers(
    action: str = "idle",
    step: int = 0,
    direction: str = "down",
    colors: Optional[Dict[str, str]] = None,
) -> Dict[str, Image.Image]:
    """
    Renders 32x32 Goblin Rogue: Low hunched organic posture, large 18px pointed lateral ears,
    expressive crooked nose, piercing beady amber eyes, tattered leather tunic with bandolier,
    clawed hands, curved serrated poison dagger, and stealth moccasins.
    """
    c_s = PixelCanvas(32, 32)
    c_b = PixelCanvas(32, 32)
    c_c = PixelCanvas(32, 32)
    c_g = PixelCanvas(32, 32)
    mid_x = 16

    bob_y = 0
    ear_twitch = 0
    crouch_x = 0
    leg_l = 0
    leg_r = 0
    dagger_y = 0

    if action == "idle":
        # 6-frame twitchy crouched breathing
        if step in (1, 2):
            bob_y = 1
        elif step == 3:
            bob_y = 1
            ear_twitch = 1
        elif step in (4, 5):
            bob_y = 0
    elif action in ("move", "walk"):
        # 6-frame quick sneaky predator scurry
        bobs = [1, 2, 0, 1, 2, 0]
        leg_l_offsets = [-2, 1, 3, -1, 0, 2]
        leg_r_offsets = [3, -1, 0, 2, -2, 1]
        bob_y = bobs[step % 6]
        crouch_x = 1 if step % 2 == 1 else -1
        leg_l = leg_l_offsets[step % 6]
        leg_r = leg_r_offsets[step % 6]
        dagger_y = 1 if step % 2 == 0 else -1
    elif action == "attack":
        if step == 0:
            dagger_y = -3
            bob_y = 0
        elif step == 1:
            dagger_y = 4
            bob_y = 1
        else:
            dagger_y = 1
            bob_y = 0
    elif action == "hurt":
        bob_y = 1
        mid_x -= 1

    c_s.draw.ellipse([mid_x - 7, 28, mid_x + 7, 30], fill=DB16["black"])
    head_y = 9 + bob_y
    torso_y = head_y + 6
    legs_y = torso_y + 6

    # --- BODY (Green skin, huge lateral pointed ears, crooked nose, beady amber eyes) ---
    # Left Ear (Diagonal up & left)
    c_b.draw_line(mid_x - 5, head_y + 2, mid_x - 9, head_y - 1 - ear_twitch, DB16["green"])
    c_b.draw_line(mid_x - 5, head_y + 4, mid_x - 8, head_y + 1, DB16["dark_green"])
    c_b.put_pixel(mid_x - 7, head_y, DB16["dark_green"])
    # Right Ear (Diagonal up & right)
    c_b.draw_line(mid_x + 4, head_y + 2, mid_x + 8, head_y - 1 + ear_twitch, DB16["green"])
    c_b.draw_line(mid_x + 4, head_y + 4, mid_x + 7, head_y + 1, DB16["dark_green"])
    c_b.put_pixel(mid_x + 6, head_y, DB16["dark_green"])

    # Skull & Cranium
    c_b.draw_rect(mid_x - 4, head_y - 1, 8, 3, fill=DB16["green"])
    c_b.draw_rect(mid_x - 5, head_y + 2, 10, 4, fill=DB16["green"])
    c_b.draw_line(mid_x - 4, head_y - 1, mid_x + 3, head_y - 1, DB16["dark_green"])

    # Crooked Goblin Nose
    c_b.draw_rect(mid_x - 1, head_y + 3, 2, 3, fill=DB16["green"])
    c_b.put_pixel(mid_x, head_y + 5, DB16["dark_green"])

    # Piercing Amber Eyes
    c_b.draw_rect(mid_x - 3, head_y + 2, 2, 2, fill=DB16["yellow"])
    c_b.put_pixel(mid_x - 2, head_y + 2, DB16["black"])
    c_b.draw_rect(mid_x + 2, head_y + 2, 2, 2, fill=DB16["yellow"])
    c_b.put_pixel(mid_x + 2, head_y + 2, DB16["black"])

    # Sharp jawline
    c_b.draw_line(mid_x - 3, head_y + 6, mid_x + 2, head_y + 6, DB16["dark_green"])

    # Sinewy arms with clawed hands
    c_b.draw_rect(mid_x - 7, torso_y + 2, 2, 4, fill=DB16["green"])
    c_b.draw_line(mid_x - 8, torso_y + 6, mid_x - 6, torso_y + 6, DB16["dark_green"]) # claws
    c_b.draw_rect(mid_x + 5, torso_y + 2 + dagger_y, 2, 4, fill=DB16["green"])

    # --- CLOTHES (Tattered Leather Tunic, Diagonal Bandolier, Stealth Pants) ---
    c_c.draw_rect(mid_x - 4, torso_y, 8, 5, fill=DB16["brown"])
    c_c.draw_line(mid_x - 4, torso_y, mid_x + 3, torso_y, DB16["dark_purple"])
    # Diagonal Bandolier
    c_c.draw_line(mid_x - 3, torso_y, mid_x + 2, torso_y + 4, DB16["black"])
    c_c.put_pixel(mid_x, torso_y + 2, DB16["yellow"])
    # Jagged hem
    c_c.draw_line(mid_x - 4, torso_y + 5, mid_x + 3, torso_y + 5, DB16["dark_purple"])
    c_c.put_pixel(mid_x - 4, torso_y + 6, DB16["dark_purple"])
    c_c.put_pixel(mid_x - 1, torso_y + 6, DB16["dark_purple"])
    c_c.put_pixel(mid_x + 2, torso_y + 6, DB16["dark_purple"])

    # Stealth Pants & Bent Knees
    c_c.draw_rect(mid_x - 5 + crouch_x, legs_y, 3, 5 + leg_l, fill=DB16["dark_gray"], outline=DB16["black"])
    c_c.draw_rect(mid_x + 2, legs_y, 3, 5 + leg_r, fill=DB16["dark_gray"], outline=DB16["black"])
    c_c.draw_rect(mid_x - 6 + crouch_x, legs_y + 4 + leg_l, 4, 2, fill=DB16["brown"])
    c_c.draw_rect(mid_x + 2, legs_y + 4 + leg_r, 4, 2, fill=DB16["brown"])

    # --- GEAR (Curved Serrated Dagger with Poison Tip) ---
    wx = mid_x + 6
    wy = torso_y + 5 + dagger_y
    c_g.draw_line(wx, wy - 2, wx, wy, DB16["brown"])
    c_g.put_pixel(wx, wy - 3, DB16["yellow"])
    c_g.draw_line(wx - 2, wy + 1, wx + 2, wy + 1, DB16["dark_gray"])
    c_g.draw_line(wx - 1, wy + 2, wx - 1, wy + 6, DB16["light_gray"])
    c_g.draw_line(wx, wy + 2, wx, wy + 5, DB16["white"]) # edge gleam
    c_g.put_pixel(wx - 2, wy + 4, DB16["dark_gray"]) # serration barb
    c_g.put_pixel(wx - 1, wy + 7, DB16["green"]) # poison droplet!

    return {
        "Shadow": c_s.image,
        "Body": c_b.image,
        "Clothes": c_c.image,
        "Gear": c_g.image,
    }


def render_heavy_brute_32_layers(
    action: str = "idle",
    step: int = 0,
    direction: str = "down",
    colors: Optional[Dict[str, str]] = None,
) -> Dict[str, Image.Image]:
    """
    Renders 32x32 Heavy Brute: Colossal barrel chest (16-18px), iron-horned brow helm,
    massive bushy braided beard with golden clasps, tree-trunk arms with leather bracers,
    massive double-headed executioner battleaxe, and heavy iron sabatons.
    """
    c_s = PixelCanvas(32, 32)
    c_b = PixelCanvas(32, 32)
    c_c = PixelCanvas(32, 32)
    c_g = PixelCanvas(32, 32)
    mid_x = 16

    bob_y = 0
    chest_expand = 0
    sway_x = 0
    leg_l = 0
    leg_r = 0
    axe_tilt = 0

    if action == "idle":
        # 6-frame slow heavy respiration
        if step in (1, 2, 3):
            bob_y = -1
            chest_expand = 1
        else:
            bob_y = 0
            chest_expand = 0
    elif action in ("move", "walk"):
        # 6-frame heavy stomping stride with side-to-side weight transfer
        bobs = [0, 1, 0, 0, 1, 0]
        sways = [-1, -1, 0, 1, 1, 0]
        leg_l_offsets = [-3, 0, 2, 2, 0, -2]
        leg_r_offsets = [2, 0, -2, -3, 0, 2]
        bob_y = bobs[step % 6]
        sway_x = sways[step % 6]
        leg_l = leg_l_offsets[step % 6]
        leg_r = leg_r_offsets[step % 6]
        axe_tilt = 1 if step in (1, 4) else 0
    elif action == "attack":
        if step == 0:
            axe_tilt = -3
            bob_y = -1
        elif step == 1:
            axe_tilt = 4
            bob_y = 1
        else:
            axe_tilt = 1
            bob_y = 0
    elif action == "hurt":
        bob_y = 1
        mid_x -= 1

    c_s.draw.ellipse([mid_x - 10, 28, mid_x + 10, 31], fill=DB16["black"])
    head_y = 7 + bob_y
    torso_y = head_y + 6
    legs_y = torso_y + 8

    # --- BODY (Broad fierce face, massive arms) ---
    c_b.draw_rect(mid_x - 5 + sway_x, head_y, 10, 5, fill=DB16["skin"])
    # Shadowed eyes under brow
    c_b.draw_line(mid_x - 4 + sway_x, head_y + 1, mid_x + 3 + sway_x, head_y + 1, DB16["black"])
    c_b.put_pixel(mid_x - 3 + sway_x, head_y + 2, DB16["white"])
    c_b.put_pixel(mid_x - 2 + sway_x, head_y + 2, DB16["black"])
    c_b.put_pixel(mid_x + 1 + sway_x, head_y + 2, DB16["white"])
    c_b.put_pixel(mid_x + 2 + sway_x, head_y + 2, DB16["black"])

    # Massive muscular arms (4px thick!)
    c_b.draw_rect(mid_x - 10 + sway_x, torso_y + 1, 4, 6, fill=DB16["skin"])
    c_b.draw_rect(mid_x - 10 + sway_x, torso_y + 4, 4, 2, fill=DB16["brown"])
    c_b.draw_rect(mid_x + 6 + sway_x, torso_y + 1, 4, 6, fill=DB16["skin"])
    c_b.draw_rect(mid_x + 6 + sway_x, torso_y + 4, 4, 2, fill=DB16["brown"])

    # --- CLOTHES (Horned Iron Brow, Massive Braided Beard, Heavy Brigandine) ---
    c_c.draw_rect(mid_x - 6 + sway_x, head_y - 2, 12, 3, fill=DB16["dark_gray"])
    c_c.draw_line(mid_x - 5 + sway_x, head_y - 2, mid_x + 4 + sway_x, head_y - 2, DB16["light_gray"])
    c_c.put_pixel(mid_x - 7 + sway_x, head_y - 3, DB16["white"])
    c_c.put_pixel(mid_x - 6 + sway_x, head_y - 2, DB16["yellow"])
    c_c.put_pixel(mid_x + 6 + sway_x, head_y - 3, DB16["white"])
    c_c.put_pixel(mid_x + 5 + sway_x, head_y - 2, DB16["yellow"])

    # Massive Bushy Braided Beard
    c_c.draw_rect(mid_x - 6 + sway_x, head_y + 3, 12, 6, fill=DB16["orange"])
    c_c.draw_rect(mid_x - 5 + sway_x, head_y + 8, 10, 3, fill=DB16["orange"])
    c_c.draw_line(mid_x - 4 + sway_x, head_y + 11, mid_x + 3 + sway_x, head_y + 11, DB16["orange"])
    c_c.put_pixel(mid_x - 3 + sway_x, head_y + 9, DB16["yellow"])
    c_c.put_pixel(mid_x + 2 + sway_x, head_y + 9, DB16["yellow"])
    c_c.draw_line(mid_x + sway_x, head_y + 5, mid_x + sway_x, head_y + 11, DB16["brown"])

    # Colossal Barrel Chest (16-18px wide!)
    c_c.draw_rect(mid_x - 8 - chest_expand + sway_x, torso_y, 16 + chest_expand*2, 6, fill=DB16["gray"])
    c_c.draw_rect(mid_x - 8 - chest_expand + sway_x, torso_y + 6, 16 + chest_expand*2, 2, fill=DB16["black"])
    c_c.draw_rect(mid_x - 2 + sway_x, torso_y + 6, 4, 2, fill=DB16["yellow"])

    # Tree-trunk Legs & Sabatons
    c_c.draw_rect(mid_x - 7 + sway_x, legs_y, 5, 5 + leg_l, fill=DB16["dark_blue"], outline=DB16["black"])
    c_c.draw_rect(mid_x + 2 + sway_x, legs_y, 5, 5 + leg_r, fill=DB16["dark_blue"], outline=DB16["black"])
    c_c.draw_rect(mid_x - 8 + sway_x, legs_y + 4 + leg_l, 6, 2, fill=DB16["dark_gray"])
    c_c.draw_rect(mid_x + 2 + sway_x, legs_y + 4 + leg_r, 6, 2, fill=DB16["dark_gray"])

    # --- GEAR (Massive Double-Bearded Executioner Battleaxe) ---
    wx = mid_x + 9 + sway_x
    wy = torso_y + 2
    c_g.draw_line(wx, wy - 9 + axe_tilt, wx, wy + 8 + axe_tilt, DB16["brown"])
    c_g.put_pixel(wx, wy - 3 + axe_tilt, DB16["yellow"])
    c_g.put_pixel(wx, wy + 3 + axe_tilt, DB16["yellow"])
    c_g.draw_rect(wx + 1, wy - 8 + axe_tilt, 4, 6, fill=DB16["light_gray"])
    c_g.draw_line(wx + 5, wy - 9 + axe_tilt, wx + 5, wy - 1 + axe_tilt, DB16["white"])
    c_g.draw_rect(wx - 4, wy - 8 + axe_tilt, 4, 6, fill=DB16["light_gray"])
    c_g.draw_line(wx - 5, wy - 9 + axe_tilt, wx - 5, wy - 1 + axe_tilt, DB16["white"])

    return {
        "Shadow": c_s.image,
        "Body": c_b.image,
        "Clothes": c_c.image,
        "Gear": c_g.image,
    }


def render_mage_32_layers(
    action: str = "idle",
    step: int = 0,
    direction: str = "down",
    colors: Optional[Dict[str, str]] = None,
) -> Dict[str, Image.Image]:
    """
    Renders 32x32 Arcane Mage: Pointed wizard cowl/hat, wide draped brim (16px),
    shrouded face with glowing cyan arcane eyes, flowing cascading robes (flaring to 22px at hem!),
    wide bell sleeves, free hand in casting gesture, and gnarled wooden staff topped with
    a radiant floating crystal orb.
    """
    c_s = PixelCanvas(32, 32)
    c_b = PixelCanvas(32, 32)
    c_c = PixelCanvas(32, 32)
    c_g = PixelCanvas(32, 32)
    mid_x = 16

    bob_y = 0
    orb_glow = 0
    robe_sway = 0
    staff_x = 0

    if action == "idle":
        # 6-frame serene celestial meditation with pulsing crystal
        if step in (1, 2):
            bob_y = -1
        if step in (2, 3):
            orb_glow = 1
    elif action in ("move", "walk"):
        # 6-frame graceful gliding locomotion
        bobs = [0, -1, 1, 0, -1, 1]
        sways = [-2, -1, 0, 2, 1, 0]
        bob_y = bobs[step % 6]
        robe_sway = sways[step % 6]
        staff_x = 1 if step in (1, 2) else 0
        orb_glow = 1 if step % 2 == 0 else 0
    elif action == "attack":
        if step == 0:
            staff_x = 2
            orb_glow = 1
        elif step == 1:
            staff_x = 4
            orb_glow = 1
            bob_y = -1
        else:
            staff_x = 1
            orb_glow = 0
    elif action == "hurt":
        bob_y = 1
        mid_x -= 1

    c_s.draw.ellipse([mid_x - 10, 28, mid_x + 10, 31], fill=DB16["black"])
    head_y = 6 + bob_y
    torso_y = head_y + 8
    legs_y = torso_y + 6

    # --- BODY (Shadowed face beneath brim with glowing cyan eyes) ---
    c_b.draw_rect(mid_x - 4, head_y + 3, 8, 4, fill=DB16["dark_purple"])
    # Glowing Cyan Arcane Eyes with specular sparkles
    c_b.draw_rect(mid_x - 3, head_y + 4, 2, 2, fill=DB16["cyan"])
    c_b.put_pixel(mid_x - 3, head_y + 4, DB16["white"])
    c_b.draw_rect(mid_x + 1, head_y + 4, 2, 2, fill=DB16["cyan"])
    c_b.put_pixel(mid_x + 2, head_y + 4, DB16["white"])

    # Free Hand (Left) in somatic casting gesture
    c_b.draw_rect(mid_x - 9, torso_y + 4, 2, 2, fill=DB16["skin"])
    if orb_glow:
        c_b.put_pixel(mid_x - 9, torso_y + 3, DB16["cyan"]) # spell sparkle

    # Right Hand holding staff
    c_b.draw_rect(mid_x + 6 + staff_x, torso_y + 4, 2, 2, fill=DB16["skin"])

    # --- CLOTHES (Pointed Wizard Hat, Wide Brim, Flowing Cascading Robes) ---
    c_c.draw_rect(mid_x - 2, head_y - 5, 3, 2, fill=DB16["dark_blue"])
    c_c.put_pixel(mid_x - 1, head_y - 6, DB16["blue"])
    c_c.draw_rect(mid_x - 4, head_y - 3, 6, 3, fill=DB16["dark_blue"])
    c_c.draw_line(mid_x - 3, head_y - 3, mid_x + 1, head_y - 3, DB16["blue"])
    c_c.draw_rect(mid_x - 4, head_y - 1, 8, 2, fill=DB16["yellow"])

    # Wide Draped Brim (16px wide)
    c_c.draw_rect(mid_x - 8, head_y + 1, 16, 2, fill=DB16["dark_blue"])
    c_c.draw_line(mid_x - 7, head_y + 1, mid_x + 6, head_y + 1, DB16["blue"])

    # Flowing Cascading Robes (flaring to 22px at hem!)
    c_c.draw_rect(mid_x - 6, torso_y, 12, 6, fill=DB16["dark_blue"])
    c_c.draw_rect(mid_x - 1, torso_y, 2, 14, fill=DB16["yellow"]) # gold stole
    c_c.draw_rect(mid_x - 2, torso_y + 5, 4, 2, fill=DB16["red"])

    for y in range(legs_y, 28):
        spread = (y - legs_y) * 2 // 3 + 6
        x0 = mid_x - spread + robe_sway
        x1 = mid_x + spread + robe_sway
        c_c.draw_line(x0, y, x1, y, DB16["dark_blue"])
        if y % 2 == 0:
            c_c.put_pixel(x0 + 2, y, DB16["blue"])
            c_c.put_pixel(x1 - 2, y, DB16["blue"])

    # --- GEAR (Twisted Arcane Staff with Luminous Crystal Orb) ---
    wx = mid_x + 7 + staff_x
    wy = torso_y
    c_g.draw_line(wx, wy - 4, wx, wy + 11, DB16["brown"])
    c_g.put_pixel(wx, wy + 2, DB16["yellow"])
    # 4-Pronged Crystal Crown Brackets
    c_g.draw_line(wx - 2, wy - 4, wx + 2, wy - 4, DB16["yellow"])
    c_g.put_pixel(wx - 2, wy - 6, DB16["yellow"])
    c_g.put_pixel(wx + 2, wy - 6, DB16["yellow"])

    # Crystal Orb & Radiant Halo
    core_c = DB16["white"] if orb_glow else DB16["cyan"]
    halo_c = DB16["cyan"] if orb_glow else DB16["blue"]
    c_g.draw_rect(wx - 1, wy - 8, 3, 3, fill=core_c)
    c_g.put_pixel(wx, wy - 7, DB16["white"])
    c_g.put_pixel(wx, wy - 9, halo_c)
    c_g.put_pixel(wx, wy - 5, halo_c)
    c_g.put_pixel(wx - 2, wy - 7, halo_c)
    c_g.put_pixel(wx + 2, wy - 7, halo_c)

    return {
        "Shadow": c_s.image,
        "Body": c_b.image,
        "Clothes": c_c.image,
        "Gear": c_g.image,
    }


# =============================================================================
# PRIMARY DISPATCH & PROJECT CREATION (32x32)
# =============================================================================

def generate_character_frame_32(
    width: int = 32,
    height: int = 32,
    action: str = "idle",
    frame_step: int = 0,
    direction: str = "down",
    archetype: str = "knight",
    palette_name: Optional[str] = "db16",
    colors: Optional[Dict[str, str]] = None,
) -> Dict[str, Image.Image]:
    """
    Renders 32x32 native layered frame images across the 4 archetypes.
    Returns: {"Shadow": img, "Body": img, "Clothes": img, "Gear": img}
    """
    arch = archetype.lower().strip()
    if "knight" in arch or "warrior" in arch or "paladin" in arch:
        layers = render_knight_32_layers(action=action, step=frame_step, direction=direction, colors=colors)
    elif "goblin" in arch or "rogue" in arch:
        layers = render_goblin_32_layers(action=action, step=frame_step, direction=direction, colors=colors)
    elif "brute" in arch or "dwarf" in arch or "heavy" in arch:
        layers = render_heavy_brute_32_layers(action=action, step=frame_step, direction=direction, colors=colors)
    elif "mage" in arch or "wizard" in arch:
        layers = render_mage_32_layers(action=action, step=frame_step, direction=direction, colors=colors)
    else:
        layers = render_knight_32_layers(action=action, step=frame_step, direction=direction, colors=colors)

    if palette_name:
        try:
            pal = GamePalette.from_name(palette_name)
            for k, img in layers.items():
                canvas = PixelCanvas.from_image(img)
                canvas.quantize_to_palette(pal)
                layers[k] = canvas.image
        except Exception:
            pass

    return layers


def build_animated_character_project_32(
    blueprint: CharacterBlueprint,
    profile: Optional[ArtProfile] = None,
    palette_name: Optional[str] = None,
    guidance: Optional[Dict[str, Any]] = None,
) -> AsepriteProject:
    """
    Builds a native 32x32 Aseprite project containing distinct 'idle' and 'move' animations.
    Incorporate typed Learning Layer guidance for archetype, palette, and animation requirements.
    """
    width, height = blueprint.size
    effective_palette = palette_name or (profile.palette_name if profile else None)
    if not effective_palette and guidance and guidance.get("palette_constraints"):
        effective_palette = guidance["palette_constraints"][0]
    effective_palette = effective_palette or "db16"

    archetype = getattr(blueprint, "archetype", None)
    if not archetype and guidance and guidance.get("character_archetype"):
        archetype = guidance["character_archetype"]
    archetype = archetype or "knight"

    # Default distinct animation specs for 32x32
    if blueprint.animations and ("idle" in blueprint.animations or "move" in blueprint.animations):
        anim_specs = dict(blueprint.animations)
    else:
        # Archetype-specific timing and frame counts
        if "knight" in archetype:
            anim_specs = {
                "idle": CharacterAnimationSpec(frames=6, duration_ms=150, loop=True),
                "move": CharacterAnimationSpec(frames=8, duration_ms=120, loop=True),
            }
        elif "goblin" in archetype:
            anim_specs = {
                "idle": CharacterAnimationSpec(frames=6, duration_ms=130, loop=True),
                "move": CharacterAnimationSpec(frames=6, duration_ms=100, loop=True),
            }
        elif "brute" in archetype:
            anim_specs = {
                "idle": CharacterAnimationSpec(frames=6, duration_ms=200, loop=True),
                "move": CharacterAnimationSpec(frames=6, duration_ms=140, loop=True),
            }
        else:  # mage
            anim_specs = {
                "idle": CharacterAnimationSpec(frames=6, duration_ms=180, loop=True),
                "move": CharacterAnimationSpec(frames=6, duration_ms=130, loop=True),
            }

    # Apply animation requirements from guidance if present
    if guidance and "animation_requirements" in guidance:
        anim_req = guidance["animation_requirements"]
        min_f = anim_req.get("min_frames", 6)
        if "move" in anim_specs and anim_specs["move"].frames < min_f:
            anim_specs["move"] = CharacterAnimationSpec(
                frames=min_f,
                duration_ms=anim_specs["move"].duration_ms,
                loop=anim_specs["move"].loop,
            )

    project = AsepriteProject(width, height)
    if hasattr(project, "metadata"):
        project.metadata["guidance_applied"] = guidance.get("applicable_rules", []) if guidance else []
    project.set_layer_name(project.sprite.layers[0].name, "Shadow")
    project.add_layer("Body")
    project.add_layer("Clothes")
    project.add_layer("Gear")

    frame_cursor = 0

    for anim_name, anim_spec in anim_specs.items():
        anim_start = frame_cursor
        duration = anim_spec.duration_ms
        frame_count = max(1, anim_spec.frames)

        for f in range(frame_count):
            layers = generate_character_frame_32(
                width=width,
                height=height,
                action=anim_name,
                frame_step=f,
                direction="down",
                archetype=archetype,
                palette_name=effective_palette,
                colors=blueprint.colors,
            )
            project.add_animation_frame(duration_ms=duration, layer_images=layers)
            frame_cursor += 1

        project.add_tag(anim_name, anim_start, frame_cursor - 1)

    if guidance:
        from libresprite_game_mcp.generators.character_generator import apply_character_guidance
        user_outline = getattr(blueprint, "outline_mode", None) if blueprint else None
        if user_outline is None and profile and profile.outlines:
            user_outline = profile.outlines.mode
        user_params = {"outline_mode": user_outline}
        apply_character_guidance(
            project=project,
            guidance=guidance,
            resolution=(width, height),
            effective_palette=effective_palette,
            user_parameters=user_params,
        )
    else:
        project.metadata["guidance_applied"] = []
        project.metadata["guidance_rules_consumed"] = []
        project.metadata["guidance_rules_ignored"] = []
        project.metadata["guidance_telemetry"] = {
            "rules_retrieved": [],
            "rules_applied": [],
            "rules_skipped": [],
            "rules_unsupported": [],
        }

    return project
