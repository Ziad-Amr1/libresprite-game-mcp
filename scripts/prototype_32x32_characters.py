"""
Comprehensive 32x32 character prototype tests across all 4 archetypes.
"""

from PIL import Image
from libresprite_game_mcp.core.palettes import GamePalette, hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas

palette = GamePalette.from_name("db16")
DB16 = {
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

def print_ascii_32(img: Image.Image, title: str):
    print(f"\n==================== {title} (32x32) ====================")
    for y in range(img.height):
        row = ""
        for x in range(img.width):
            r, g, b, a = img.getpixel((x, y))
            if a == 0:
                row += "  "
            else:
                lum = (r * 299 + g * 587 + b * 114) // 1000
                if lum < 40:
                    row += "##"
                elif lum < 100:
                    row += "=="
                elif lum < 170:
                    row += "++"
                else:
                    row += ".."
        print(row)

# 1. KNIGHT
def render_knight_32(action="idle", step=0):
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
        if step in (1, 2):
            bob_y = -1
            plume_wave = 1
        elif step in (4, 5):
            bob_y = 0
            plume_wave = -1
    elif action == "move":
        march_bobs = [0, -1, 1, 0, 0, -1, 1, 0]
        leg_l_offsets = [-2, -3, 0, 2, 3, 1, -1, -2]
        leg_r_offsets = [2, 3, 1, -1, -2, -3, 0, 2]
        bob_y = march_bobs[step % 8]
        leg_l = leg_l_offsets[step % 8]
        leg_r = leg_r_offsets[step % 8]
        plume_wave = 1 if step % 2 == 0 else -1
        sword_y = 1 if step % 2 == 1 else 0

    c_s.draw.ellipse([mid_x - 8, 28, mid_x + 8, 30], fill=DB16["black"])
    head_y = 6 + bob_y
    torso_y = head_y + 8
    legs_y = torso_y + 8

    # Body
    c_b.draw_rect(mid_x - 4, head_y + 4, 8, 4, fill=DB16["skin"])
    c_b.draw_rect(mid_x - 4, head_y + 4, 8, 1, fill=DB16["black"])
    c_b.put_pixel(mid_x - 3, head_y + 5, DB16["black"])
    c_b.put_pixel(mid_x + 2, head_y + 5, DB16["black"])
    c_b.draw_rect(mid_x - 8, torso_y + 4, 2, 3, fill=DB16["light_gray"])
    c_b.draw_rect(mid_x + 6, torso_y + 4 + sword_y, 2, 3, fill=DB16["light_gray"])

    # Clothes
    c_c.draw_rect(mid_x - 2 + plume_wave, head_y - 4, 4, 2, fill=DB16["red"])
    c_c.draw_rect(mid_x - 3 + plume_wave, head_y - 2, 5, 2, fill=DB16["red"])
    c_c.put_pixel(mid_x + 2 + plume_wave, head_y - 1, DB16["dark_purple"])

    c_c.draw_rect(mid_x - 5, head_y, 10, 4, fill=DB16["light_gray"])
    c_c.draw_line(mid_x - 4, head_y, mid_x + 3, head_y, DB16["white"])
    c_c.put_pixel(mid_x - 2, head_y + 1, DB16["white"])
    c_c.draw_rect(mid_x - 5, head_y + 4, 2, 4, fill=DB16["light_gray"])
    c_c.draw_rect(mid_x + 3, head_y + 4, 2, 4, fill=DB16["light_gray"])
    c_c.draw_rect(mid_x - 4, head_y + 7, 8, 1, fill=DB16["dark_gray"])

    c_c.draw_rect(mid_x - 9, torso_y, 4, 4, fill=DB16["light_gray"])
    c_c.draw_line(mid_x - 9, torso_y, mid_x - 6, torso_y, DB16["white"])
    c_c.draw_rect(mid_x + 5, torso_y, 4, 4, fill=DB16["light_gray"])
    c_c.draw_line(mid_x + 5, torso_y, mid_x + 8, torso_y, DB16["white"])

    c_c.draw_rect(mid_x - 5, torso_y, 10, 6, fill=DB16["blue"])
    c_c.draw_rect(mid_x - 3, torso_y + 1, 6, 4, fill=DB16["light_gray"])
    c_c.draw_line(mid_x - 1, torso_y + 1, mid_x - 1, torso_y + 4, DB16["white"])
    c_c.draw_line(mid_x, torso_y + 1, mid_x, torso_y + 4, DB16["dark_gray"])

    c_c.draw_rect(mid_x - 5, torso_y + 6, 10, 2, fill=DB16["brown"])
    c_c.draw_rect(mid_x - 1, torso_y + 6, 2, 2, fill=DB16["yellow"])
    c_c.draw_rect(mid_x - 5, torso_y + 7, 10, 1, fill=DB16["black"])

    c_c.draw_rect(mid_x - 5, legs_y, 3, 5 + leg_l, fill=DB16["dark_gray"], outline=DB16["black"])
    c_c.draw_rect(mid_x + 2, legs_y, 3, 5 + leg_r, fill=DB16["dark_gray"], outline=DB16["black"])
    c_c.put_pixel(mid_x - 4, legs_y, DB16["light_gray"])
    c_c.put_pixel(mid_x + 3, legs_y, DB16["light_gray"])
    c_c.draw_rect(mid_x - 6, legs_y + 4 + leg_l, 4, 2, fill=DB16["dark_gray"])
    c_c.draw_rect(mid_x + 1, legs_y + 4 + leg_r, 4, 2, fill=DB16["dark_gray"])

    # Gear
    c_g.draw_rect(mid_x - 10, torso_y + 1, 4, 7, fill=DB16["blue"])
    c_g.draw_line(mid_x - 10, torso_y + 1, mid_x - 7, torso_y + 1, DB16["light_gray"])
    c_g.draw_line(mid_x - 10, torso_y + 8, mid_x - 8, torso_y + 9, DB16["light_gray"])
    c_g.draw_rect(mid_x - 9, torso_y + 3, 2, 2, fill=DB16["white"])

    wx = mid_x + 7
    wy = torso_y + 4 + sword_y
    c_g.draw_line(wx, wy - 9, wx, wy - 1, DB16["light_gray"])
    c_g.draw_line(wx + 1, wy - 8, wx + 1, wy - 2, DB16["white"])
    c_g.put_pixel(wx, wy - 10, DB16["white"])
    c_g.draw_line(wx - 2, wy, wx + 3, wy, DB16["yellow"])
    c_g.draw_line(wx, wy + 1, wx, wy + 3, DB16["brown"])
    c_g.put_pixel(wx, wy + 4, DB16["yellow"])

    comp = Image.alpha_composite(c_s.image, c_b.image)
    comp = Image.alpha_composite(comp, c_c.image)
    comp = Image.alpha_composite(comp, c_g.image)
    return comp

# 2. GOBLIN ROGUE
def render_goblin_32(action="idle", step=0):
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
        if step in (1, 2):
            bob_y = 1
        elif step == 3:
            bob_y = 1
            ear_twitch = 1
        elif step in (4, 5):
            bob_y = 0
    elif action == "move":
        # Quick sneaky scurry
        bobs = [1, 2, 0, 1, 2, 0]
        leg_l_offsets = [-2, 1, 3, -1, 0, 2]
        leg_r_offsets = [3, -1, 0, 2, -2, 1]
        bob_y = bobs[step % 6]
        crouch_x = 1 if step % 2 == 1 else -1
        leg_l = leg_l_offsets[step % 6]
        leg_r = leg_r_offsets[step % 6]
        dagger_y = 1 if step % 2 == 0 else -1

    c_s.draw.ellipse([mid_x - 7, 28, mid_x + 7, 30], fill=DB16["black"])
    head_y = 9 + bob_y
    torso_y = head_y + 6
    legs_y = torso_y + 6

    # --- BODY (Green skin, huge lateral ears, crooked nose, beady amber eyes) ---
    # Pointed Lateral Ears (Extending out to 18px total span!)
    # Left Ear
    c_b.draw_line(mid_x - 5, head_y + 2, mid_x - 9, head_y - 1 - ear_twitch, DB16["green"])
    c_b.draw_line(mid_x - 5, head_y + 4, mid_x - 8, head_y + 1, DB16["dark_green"])
    c_b.put_pixel(mid_x - 7, head_y, DB16["dark_green"]) # inner ear shadow
    # Right Ear
    c_b.draw_line(mid_x + 4, head_y + 2, mid_x + 8, head_y - 1 + ear_twitch, DB16["green"])
    c_b.draw_line(mid_x + 4, head_y + 4, mid_x + 7, head_y + 1, DB16["dark_green"])
    c_b.put_pixel(mid_x + 6, head_y, DB16["dark_green"])

    # Skull & Cranium
    c_b.draw_rect(mid_x - 4, head_y - 1, 8, 3, fill=DB16["green"])
    c_b.draw_rect(mid_x - 5, head_y + 2, 10, 4, fill=DB16["green"])
    # Shading on skull
    c_b.draw_line(mid_x - 4, head_y - 1, mid_x + 3, head_y - 1, DB16["dark_green"])

    # Crooked Goblin Nose (jutting forward)
    c_b.draw_rect(mid_x - 1, head_y + 3, 2, 3, fill=DB16["green"])
    c_b.put_pixel(mid_x, head_y + 5, DB16["dark_green"]) # nose tip shadow

    # Beady Piercing Amber Eyes
    c_b.draw_rect(mid_x - 3, head_y + 2, 2, 2, fill=DB16["yellow"])
    c_b.put_pixel(mid_x - 2, head_y + 2, DB16["black"]) # pupil
    c_b.draw_rect(mid_x + 2, head_y + 2, 2, 2, fill=DB16["yellow"])
    c_b.put_pixel(mid_x + 2, head_y + 2, DB16["black"]) # pupil

    # Sharp jawline
    c_b.draw_line(mid_x - 3, head_y + 6, mid_x + 2, head_y + 6, DB16["dark_green"])

    # Sinewy arms with clawed hands
    c_b.draw_rect(mid_x - 7, torso_y + 2, 2, 4, fill=DB16["green"]) # left arm
    c_b.draw_line(mid_x - 8, torso_y + 6, mid_x - 6, torso_y + 6, DB16["dark_green"]) # claws
    c_b.draw_rect(mid_x + 5, torso_y + 2 + dagger_y, 2, 4, fill=DB16["green"]) # right arm

    # --- CLOTHES (Tattered Leather Tunic, Bandolier, Stealth Pants) ---
    # Tattered Tunic
    c_c.draw_rect(mid_x - 4, torso_y, 8, 5, fill=DB16["brown"])
    c_c.draw_line(mid_x - 4, torso_y, mid_x + 3, torso_y, DB16["dark_purple"]) # collar
    # Diagonal Bandolier
    c_c.draw_line(mid_x - 3, torso_y, mid_x + 2, torso_y + 4, DB16["black"])
    c_c.put_pixel(mid_x, torso_y + 2, DB16["yellow"]) # pouch buckle
    # Jagged hem
    c_c.draw_line(mid_x - 4, torso_y + 5, mid_x + 3, torso_y + 5, DB16["dark_purple"])
    c_c.put_pixel(mid_x - 4, torso_y + 6, DB16["dark_purple"])
    c_c.put_pixel(mid_x - 1, torso_y + 6, DB16["dark_purple"])
    c_c.put_pixel(mid_x + 2, torso_y + 6, DB16["dark_purple"])

    # Stealth Pants & Bent Knees
    c_c.draw_rect(mid_x - 5 + crouch_x, legs_y, 3, 5 + leg_l, fill=DB16["dark_gray"], outline=DB16["black"])
    c_c.draw_rect(mid_x + 2, legs_y, 3, 5 + leg_r, fill=DB16["dark_gray"], outline=DB16["black"])
    # Pointed stealth shoes
    c_c.draw_rect(mid_x - 6 + crouch_x, legs_y + 4 + leg_l, 4, 2, fill=DB16["brown"])
    c_c.draw_rect(mid_x + 2, legs_y + 4 + leg_r, 4, 2, fill=DB16["brown"])

    # --- GEAR (Curved Serrated Dagger in Reverse Grip) ---
    wx = mid_x + 6
    wy = torso_y + 5 + dagger_y
    # Leather grip & brass pommel
    c_g.draw_line(wx, wy - 2, wx, wy, DB16["brown"])
    c_g.put_pixel(wx, wy - 3, DB16["yellow"]) # pommel
    # Curved crossguard
    c_g.draw_line(wx - 2, wy + 1, wx + 2, wy + 1, DB16["dark_gray"])
    # Serrated poison-tipped curved blade
    c_g.draw_line(wx - 1, wy + 2, wx - 1, wy + 6, DB16["light_gray"])
    c_g.draw_line(wx, wy + 2, wx, wy + 5, DB16["white"]) # edge gleam
    c_g.put_pixel(wx - 2, wy + 4, DB16["dark_gray"]) # serration barb
    c_g.put_pixel(wx - 1, wy + 7, DB16["green"]) # poison drop on tip!

    comp = Image.alpha_composite(c_s.image, c_b.image)
    comp = Image.alpha_composite(comp, c_c.image)
    comp = Image.alpha_composite(comp, c_g.image)
    return comp

# 3. HEAVY BRUTE
def render_brute_32(action="idle", step=0):
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
        # Slow deep breathing (chest expands +1px)
        if step in (1, 2, 3):
            bob_y = -1
            chest_expand = 1
        else:
            bob_y = 0
            chest_expand = 0
    elif action == "move":
        # Heavy stomping stride with side-to-side weight transfer
        bobs = [0, 1, 0, 0, 1, 0]
        sways = [-1, -1, 0, 1, 1, 0]
        leg_l_offsets = [-3, 0, 2, 2, 0, -2]
        leg_r_offsets = [2, 0, -2, -3, 0, 2]
        bob_y = bobs[step % 6]
        sway_x = sways[step % 6]
        leg_l = leg_l_offsets[step % 6]
        leg_r = leg_r_offsets[step % 6]
        axe_tilt = 1 if step in (1, 4) else 0

    c_s.draw.ellipse([mid_x - 10, 28, mid_x + 10, 31], fill=DB16["black"])
    head_y = 7 + bob_y
    torso_y = head_y + 6
    legs_y = torso_y + 8

    # --- BODY (Broad fierce face, massive arms) ---
    c_b.draw_rect(mid_x - 5 + sway_x, head_y, 10, 5, fill=DB16["skin"])
    # Fierce shadowed eyes under brow
    c_b.draw_line(mid_x - 4 + sway_x, head_y + 1, mid_x + 3 + sway_x, head_y + 1, DB16["black"])
    c_b.put_pixel(mid_x - 3 + sway_x, head_y + 2, DB16["white"])
    c_b.put_pixel(mid_x - 2 + sway_x, head_y + 2, DB16["black"])
    c_b.put_pixel(mid_x + 1 + sway_x, head_y + 2, DB16["white"])
    c_b.put_pixel(mid_x + 2 + sway_x, head_y + 2, DB16["black"])

    # Massive muscular arms (4px thick!)
    c_b.draw_rect(mid_x - 10 + sway_x, torso_y + 1, 4, 6, fill=DB16["skin"]) # left arm
    c_b.draw_rect(mid_x - 10 + sway_x, torso_y + 4, 4, 2, fill=DB16["brown"]) # bracer
    c_b.draw_rect(mid_x + 6 + sway_x, torso_y + 1, 4, 6, fill=DB16["skin"]) # right arm
    c_b.draw_rect(mid_x + 6 + sway_x, torso_y + 4, 4, 2, fill=DB16["brown"])

    # --- CLOTHES (Horned Iron Brow, Massive Braided Beard, Heavy Brigandine) ---
    # Iron brow helm & low curved horns
    c_c.draw_rect(mid_x - 6 + sway_x, head_y - 2, 12, 3, fill=DB16["dark_gray"])
    c_c.draw_line(mid_x - 5 + sway_x, head_y - 2, mid_x + 4 + sway_x, head_y - 2, DB16["light_gray"])
    # Left Horn
    c_c.put_pixel(mid_x - 7 + sway_x, head_y - 3, DB16["white"])
    c_c.put_pixel(mid_x - 6 + sway_x, head_y - 2, DB16["yellow"])
    # Right Horn
    c_c.put_pixel(mid_x + 6 + sway_x, head_y - 3, DB16["white"])
    c_c.put_pixel(mid_x + 5 + sway_x, head_y - 2, DB16["yellow"])

    # Massive Bushy Braided Beard (cascading from row 10 to row 19!)
    c_c.draw_rect(mid_x - 6 + sway_x, head_y + 3, 12, 6, fill=DB16["orange"])
    c_c.draw_rect(mid_x - 5 + sway_x, head_y + 8, 10, 3, fill=DB16["orange"])
    c_c.draw_line(mid_x - 4 + sway_x, head_y + 11, mid_x + 3 + sway_x, head_y + 11, DB16["orange"])
    # Beard braids & golden clasps
    c_c.put_pixel(mid_x - 3 + sway_x, head_y + 9, DB16["yellow"]) # left clasp
    c_c.put_pixel(mid_x + 2 + sway_x, head_y + 9, DB16["yellow"]) # right clasp
    c_c.draw_line(mid_x + sway_x, head_y + 5, mid_x + sway_x, head_y + 11, DB16["brown"]) # center fork

    # Colossal Barrel Chest (16-18px wide!)
    c_c.draw_rect(mid_x - 8 - chest_expand + sway_x, torso_y, 16 + chest_expand*2, 6, fill=DB16["gray"])
    c_c.draw_rect(mid_x - 8 - chest_expand + sway_x, torso_y + 6, 16 + chest_expand*2, 2, fill=DB16["black"]) # heavy belt
    c_c.draw_rect(mid_x - 2 + sway_x, torso_y + 6, 4, 2, fill=DB16["yellow"]) # massive iron buckle

    # Tree-trunk Legs & Sabatons
    c_c.draw_rect(mid_x - 7 + sway_x, legs_y, 5, 5 + leg_l, fill=DB16["dark_blue"], outline=DB16["black"])
    c_c.draw_rect(mid_x + 2 + sway_x, legs_y, 5, 5 + leg_r, fill=DB16["dark_blue"], outline=DB16["black"])
    c_c.draw_rect(mid_x - 8 + sway_x, legs_y + 4 + leg_l, 6, 2, fill=DB16["dark_gray"])
    c_c.draw_rect(mid_x + 2 + sway_x, legs_y + 4 + leg_r, 6, 2, fill=DB16["dark_gray"])

    # --- GEAR (Massive Double-Bearded Executioner Battleaxe) ---
    wx = mid_x + 9 + sway_x
    wy = torso_y + 2
    # Heavy Ashwood Haft
    c_g.draw_line(wx, wy - 9 + axe_tilt, wx, wy + 8 + axe_tilt, DB16["brown"])
    c_g.put_pixel(wx, wy - 3 + axe_tilt, DB16["yellow"]) # binding ring
    c_g.put_pixel(wx, wy + 3 + axe_tilt, DB16["yellow"])
    # Huge Crescent Axe Blades (Double-Headed!)
    # Right blade
    c_g.draw_rect(wx + 1, wy - 8 + axe_tilt, 4, 6, fill=DB16["light_gray"])
    c_g.draw_line(wx + 5, wy - 9 + axe_tilt, wx + 5, wy - 1 + axe_tilt, DB16["white"]) # sharpened edge
    # Left blade
    c_g.draw_rect(wx - 4, wy - 8 + axe_tilt, 4, 6, fill=DB16["light_gray"])
    c_g.draw_line(wx - 5, wy - 9 + axe_tilt, wx - 5, wy - 1 + axe_tilt, DB16["white"])

    comp = Image.alpha_composite(c_s.image, c_b.image)
    comp = Image.alpha_composite(comp, c_c.image)
    comp = Image.alpha_composite(comp, c_g.image)
    return comp

# 4. MAGE
def render_mage_32(action="idle", step=0):
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
        if step in (1, 2):
            bob_y = -1
        if step in (2, 3):
            orb_glow = 1
    elif action == "move":
        # Graceful gliding locomotion
        bobs = [0, -1, 0, 0, -1, 0]
        sways = [-1, -2, -1, 1, 2, 1]
        bob_y = bobs[step % 6]
        robe_sway = sways[step % 6]
        staff_x = 1 if step in (1, 2) else 0
        orb_glow = 1 if step % 2 == 0 else 0

    c_s.draw.ellipse([mid_x - 10, 28, mid_x + 10, 31], fill=DB16["black"])
    head_y = 6 + bob_y
    torso_y = head_y + 8
    legs_y = torso_y + 6

    # --- BODY (Shadowed face beneath brim with glowing cyan eyes) ---
    c_b.draw_rect(mid_x - 4, head_y + 3, 8, 4, fill=DB16["dark_purple"])
    # Glowing Cyan Arcane Eyes with specular centers!
    c_b.draw_rect(mid_x - 3, head_y + 4, 2, 2, fill=DB16["cyan"])
    c_b.put_pixel(mid_x - 3, head_y + 4, DB16["white"]) # brilliant pupil
    c_b.draw_rect(mid_x + 1, head_y + 4, 2, 2, fill=DB16["cyan"])
    c_b.put_pixel(mid_x + 2, head_y + 4, DB16["white"])
    # Free Hand (Left) in mystic casting gesture
    c_b.draw_rect(mid_x - 9, torso_y + 4, 2, 2, fill=DB16["skin"])
    if orb_glow:
        c_b.put_pixel(mid_x - 9, torso_y + 3, DB16["cyan"]) # somatic particle spark!

    # Right Hand holding staff
    c_b.draw_rect(mid_x + 6 + staff_x, torso_y + 4, 2, 2, fill=DB16["skin"])

    # --- CLOTHES (Pointed Wizard Hat, Wide Brim, Flowing Cascading Robes) ---
    # Pointed Cowl / Hat Peak
    c_c.draw_rect(mid_x - 2, head_y - 5, 3, 2, fill=DB16["dark_blue"])
    c_c.put_pixel(mid_x - 1, head_y - 6, DB16["blue"]) # hat tip
    c_c.draw_rect(mid_x - 4, head_y - 3, 6, 3, fill=DB16["dark_blue"])
    c_c.draw_line(mid_x - 3, head_y - 3, mid_x + 1, head_y - 3, DB16["blue"]) # hat highlight
    c_c.draw_rect(mid_x - 4, head_y - 1, 8, 2, fill=DB16["yellow"]) # golden hat band

    # Wide Draped Brim extending past shoulders (16px wide!)
    c_c.draw_rect(mid_x - 8, head_y + 1, 16, 2, fill=DB16["dark_blue"])
    c_c.draw_line(mid_x - 7, head_y + 1, mid_x + 6, head_y + 1, DB16["blue"])

    # Flowing Cascading Robes (tapering from 12px at chest to 22px at hem!)
    c_c.draw_rect(mid_x - 6, torso_y, 12, 6, fill=DB16["dark_blue"])
    # Elegant mystic stole draped down the front
    c_c.draw_rect(mid_x - 1, torso_y, 2, 14, fill=DB16["yellow"])
    c_c.draw_rect(mid_x - 2, torso_y + 5, 4, 2, fill=DB16["red"]) # sash buckle

    # Flared Skirt & Undulating Hem Folds (widening to 22px!)
    for y in range(legs_y, 28):
        spread = (y - legs_y) * 2 // 3 + 6
        x0 = mid_x - spread + robe_sway
        x1 = mid_x + spread + robe_sway
        c_c.draw_line(x0, y, x1, y, DB16["dark_blue"])
        # Fold highlight lines
        if y % 2 == 0:
            c_c.put_pixel(x0 + 2, y, DB16["blue"])
            c_c.put_pixel(x1 - 2, y, DB16["blue"])

    # --- GEAR (Twisted Gnarled Arcane Staff with Luminous Crystal Orb) ---
    wx = mid_x + 7 + staff_x
    wy = torso_y
    # Gnarled Wooden Haft
    c_g.draw_line(wx, wy - 4, wx, wy + 11, DB16["brown"])
    c_g.put_pixel(wx, wy + 2, DB16["yellow"]) # brass ferrule
    # 4-Pronged Crystal Crown Brackets
    c_g.draw_line(wx - 2, wy - 4, wx + 2, wy - 4, DB16["yellow"])
    c_g.put_pixel(wx - 2, wy - 6, DB16["yellow"])
    c_g.put_pixel(wx + 2, wy - 6, DB16["yellow"])

    # Ethereal Glowing Crystal Orb
    core_c = DB16["white"] if orb_glow else DB16["cyan"]
    halo_c = DB16["cyan"] if orb_glow else DB16["blue"]
    c_g.draw_rect(wx - 1, wy - 8, 3, 3, fill=core_c)
    c_g.put_pixel(wx, wy - 7, DB16["white"]) # specular sparkle
    # Ambient Radiant Halo
    c_g.put_pixel(wx, wy - 9, halo_c)
    c_g.put_pixel(wx, wy - 5, halo_c)
    c_g.put_pixel(wx - 2, wy - 7, halo_c)
    c_g.put_pixel(wx + 2, wy - 7, halo_c)

    comp = Image.alpha_composite(c_s.image, c_b.image)
    comp = Image.alpha_composite(comp, c_c.image)
    comp = Image.alpha_composite(comp, c_g.image)
    return comp

k = render_knight_32()
g = render_goblin_32()
b = render_brute_32()
m = render_mage_32()

print_ascii_32(k, "Knight 32x32")
print_ascii_32(g, "Goblin Rogue 32x32")
print_ascii_32(b, "Heavy Brute 32x32")
print_ascii_32(m, "Arcane Mage 32x32")
