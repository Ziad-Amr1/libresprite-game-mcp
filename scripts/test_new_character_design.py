"""
Refined Archetype Renderer Test & Fine-Tuning.
"""

from typing import Dict, Optional, Tuple
from PIL import Image
from libresprite_game_mcp.core.palettes import RGBA, hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas

def adjust_color(color: RGBA, factor: float) -> RGBA:
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
    return (max(0, min(255, nr)), max(0, min(255, ng)), max(0, min(255, nb)), 255)

class TestStyle:
    __test__ = False
    def __init__(self, **kwargs):
        self.skin = hex_to_rgba(kwargs.get("skin", "#d2aa99"))
        self.skin_shadow = hex_to_rgba(kwargs.get("skin_shadow", "#854c30"))
        self.skin_highlight = adjust_color(self.skin, 0.25)
        self.hair = hex_to_rgba(kwargs.get("hair", "#442434"))
        self.hair_shadow = hex_to_rgba(kwargs.get("hair_shadow", "#140c1c"))
        self.hair_highlight = adjust_color(self.hair, 0.3)
        self.shirt = hex_to_rgba(kwargs.get("shirt", "#597dce"))
        self.shirt_shadow = hex_to_rgba(kwargs.get("shirt_shadow", "#30346d"))
        self.shirt_highlight = adjust_color(self.shirt, 0.25)
        self.pants = hex_to_rgba(kwargs.get("pants", "#4e4a4e"))
        self.pants_shadow = hex_to_rgba(kwargs.get("pants_shadow", "#140c1c"))
        self.pants_highlight = adjust_color(self.pants, 0.2)
        self.outline = hex_to_rgba(kwargs.get("outline", "#140c1c"))
        self.eyes = hex_to_rgba(kwargs.get("eyes", "#140c1c"))
        self.weapon = hex_to_rgba(kwargs.get("weapon", "#8595a1"))
        self.weapon_hilt = hex_to_rgba(kwargs.get("weapon_hilt", "#d27d2c"))
        self.weapon_glow = hex_to_rgba(kwargs.get("weapon_glow", "#6dc2ca"))
        self.accent = hex_to_rgba(kwargs.get("accent", "#d04648"))
        self.belt = hex_to_rgba(kwargs.get("belt", "#854c30"))
        self.shoes = hex_to_rgba(kwargs.get("shoes", "#4e4a4e"))

def render_knight_layers(w: int, h: int, style: TestStyle, action: str = "idle", step: int = 0, direction: str = "down"):
    scale = max(1, w // 16)
    mid_x = w // 2
    c_shadow = PixelCanvas(w, h)
    c_body = PixelCanvas(w, h)
    c_clothes = PixelCanvas(w, h)
    c_gear = PixelCanvas(w, h)

    bob_y = 1 if (action == "idle" and step % 2 == 1) else (1 if (action == "walk" and step % 2 == 0) else 0)
    leg_l = -1 if (action == "walk" and step == 0) else (1 if (action == "walk" and step == 2) else 0)
    leg_r = 1 if (action == "walk" and step == 0) else (-1 if (action == "walk" and step == 2) else 0)
    thrust = 2 if (action == "attack" and step == 1) else (1 if (action == "attack" and step == 2) else 0)

    # Shadow
    c_shadow.draw.ellipse([mid_x - 4*scale, 14*scale, mid_x + 3*scale, 15*scale], fill=style.outline)

    head_y = (3 + bob_y) * scale
    torso_y = head_y + 4 * scale
    legs_y = torso_y + 4 * scale

    # 1. Body: Face opening & Hands
    # Face skin opening inside helmet
    for y in range(head_y + 2, head_y + 4):
        for x in range(mid_x - 2, mid_x + 2):
            c_body.put_pixel(x, y, style.skin)
    # Eyes
    c_body.put_pixel(mid_x - 2, head_y + 2, style.eyes)
    c_body.put_pixel(mid_x + 1, head_y + 2, style.eyes)
    # Hands
    c_body.draw_rect(mid_x - 4, torso_y + 2, 1, 2, fill=style.skin)
    c_body.draw_rect(mid_x + 3, torso_y + 2, 1, 2, fill=style.skin)

    # 2. Clothes: Helmet, Plume, Pauldrons, Armor, Greaves
    # Plume on helmet top
    c_clothes.put_pixel(mid_x - 1, head_y - 2, style.accent)
    c_clothes.put_pixel(mid_x, head_y - 2, style.accent)
    c_clothes.put_pixel(mid_x - 1, head_y - 1, style.accent)

    # Helmet skull (steel with highlight)
    for x in range(mid_x - 2, mid_x + 2):
        c_clothes.put_pixel(x, head_y - 1, style.weapon)
    c_clothes.put_pixel(mid_x - 1, head_y - 1, adjust_color(style.weapon, 0.35))
    # Helmet visor brow
    for x in range(mid_x - 3, mid_x + 3):
        c_clothes.put_pixel(x, head_y, style.weapon)
        c_clothes.put_pixel(x, head_y + 1, style.weapon)
    c_clothes.put_pixel(mid_x - 2, head_y, adjust_color(style.weapon, 0.3))
    # Cheek guards
    c_clothes.put_pixel(mid_x - 3, head_y + 2, style.weapon)
    c_clothes.put_pixel(mid_x - 3, head_y + 3, style.weapon)
    c_clothes.put_pixel(mid_x + 2, head_y + 2, style.weapon)
    c_clothes.put_pixel(mid_x + 2, head_y + 3, style.weapon)
    # Chin rim
    for x in range(mid_x - 2, mid_x + 2):
        c_clothes.put_pixel(x, head_y + 4, style.outline)

    # Pauldrons (Shoulders wider than torso!)
    c_clothes.put_pixel(mid_x - 4, torso_y, adjust_color(style.weapon, 0.2))
    c_clothes.put_pixel(mid_x - 4, torso_y + 1, style.weapon)
    c_clothes.put_pixel(mid_x + 3, torso_y, adjust_color(style.weapon, 0.2))
    c_clothes.put_pixel(mid_x + 3, torso_y + 1, style.weapon)

    # Breastplate
    for y in range(torso_y, torso_y + 3):
        for x in range(mid_x - 3, mid_x + 3):
            c_clothes.put_pixel(x, y, style.shirt)
    # Plate highlight
    c_clothes.put_pixel(mid_x - 2, torso_y, style.shirt_highlight)
    c_clothes.put_pixel(mid_x - 1, torso_y, style.shirt_highlight)
    c_clothes.put_pixel(mid_x - 2, torso_y + 1, style.shirt_highlight)
    # Belt / Tassets
    for x in range(mid_x - 3, mid_x + 3):
        c_clothes.put_pixel(x, torso_y + 3, style.belt)
    c_clothes.put_pixel(mid_x - 1, torso_y + 3, style.weapon_hilt)

    # Greaves / Legs
    # Left leg
    c_clothes.draw_rect(mid_x - 3, legs_y, 2, 3 + leg_l, fill=style.pants, outline=style.pants_shadow)
    # Right leg
    c_clothes.draw_rect(mid_x + 1, legs_y, 2, 3 + leg_r, fill=style.pants, outline=style.pants_shadow)

    # 3. Gear: Broadsword
    wx = mid_x + 4 + thrust
    wy = torso_y + 1
    # Blade
    c_gear.draw_line(wx, wy - 3, wx, wy + 2, style.weapon)
    c_gear.put_pixel(wx, wy - 3, adjust_color(style.weapon, 0.4)) # tip gleam
    # Crossguard & Hilt
    c_gear.draw_line(wx - 1, wy, wx + 1, wy, style.weapon_hilt)
    c_gear.put_pixel(wx, wy + 3, style.weapon_hilt) # pommel

    composite = Image.alpha_composite(c_shadow.image, c_body.image)
    composite = Image.alpha_composite(composite, c_clothes.image)
    composite = Image.alpha_composite(composite, c_gear.image)
    return composite

def render_mage_layers(w: int, h: int, style: TestStyle, action: str = "idle", step: int = 0, direction: str = "down"):
    scale = max(1, w // 16)
    mid_x = w // 2
    c_shadow = PixelCanvas(w, h)
    c_body = PixelCanvas(w, h)
    c_clothes = PixelCanvas(w, h)
    c_gear = PixelCanvas(w, h)

    bob_y = 1 if (action == "idle" and step % 2 == 1) else (1 if (action == "walk" and step % 2 == 0) else 0)
    thrust = 2 if (action == "attack" and step == 1) else 0

    c_shadow.draw.ellipse([mid_x - 5*scale, 14*scale, mid_x + 4*scale, 15*scale], fill=style.outline)

    head_y = (3 + bob_y) * scale
    torso_y = head_y + 4 * scale
    legs_y = torso_y + 3 * scale

    # 1. Body: Glowing Arcane Eyes & Shaded Face
    for y in range(head_y + 1, head_y + 4):
        for x in range(mid_x - 2, mid_x + 2):
            c_body.put_pixel(x, y, style.skin_shadow)
    # Arcane Eyes
    c_body.put_pixel(mid_x - 2, head_y + 2, style.weapon_glow)
    c_body.put_pixel(mid_x + 1, head_y + 2, style.weapon_glow)
    # Hand
    c_body.put_pixel(mid_x + 4, torso_y + 2, style.skin)

    # 2. Clothes: Pointed Wizard Cowl / Hood & Flared Robe
    # Pointed Cowl tip
    c_clothes.put_pixel(mid_x - 1, head_y - 2, style.shirt)
    c_clothes.put_pixel(mid_x, head_y - 2, style.shirt_highlight)
    # Hood Crown
    for x in range(mid_x - 2, mid_x + 2):
        c_clothes.put_pixel(x, head_y - 1, style.shirt)
    c_clothes.put_pixel(mid_x - 1, head_y - 1, style.shirt_highlight)
    # Hood Brow & Overhang (8px wide!)
    for x in range(mid_x - 4, mid_x + 4):
        c_clothes.put_pixel(x, head_y, style.shirt)
    c_clothes.put_pixel(mid_x - 4, head_y + 1, style.shirt)
    c_clothes.put_pixel(mid_x + 3, head_y + 1, style.shirt)
    c_clothes.put_pixel(mid_x - 4, head_y + 2, style.shirt_shadow)
    c_clothes.put_pixel(mid_x + 3, head_y + 2, style.shirt_shadow)

    # Flared Wizard Robe: Chest (6px), Waist (7px), Hem (9-10px)
    for y in range(torso_y, torso_y + 3):
        for x in range(mid_x - 3, mid_x + 3):
            c_clothes.put_pixel(x, y, style.shirt)
    # Mystic central sash
    for y in range(torso_y, legs_y + 4):
        c_clothes.put_pixel(mid_x - 1, y, style.accent)
        c_clothes.put_pixel(mid_x, y, style.accent)

    # Flared hemline
    for y in range(legs_y, legs_y + 4):
        w_offset = (y - legs_y) // 2 + 1
        for x in range(mid_x - 3 - w_offset, mid_x + 3 + w_offset):
            if c_clothes.get_pixel(x, y)[3] == 0:
                c_clothes.put_pixel(x, y, style.shirt if x % 2 == 0 else style.shirt_shadow)

    # 3. Gear: Mystic Staff with Glowing Crystal Orb
    wx = mid_x + 4 + thrust
    wy = torso_y
    # Staff pole
    c_gear.draw_line(wx, wy - 1, wx, wy + 5, style.weapon_hilt)
    # Glowing Orb cluster
    c_gear.put_pixel(wx, wy - 3, style.weapon_glow)
    c_gear.put_pixel(wx - 1, wy - 2, style.weapon_glow)
    c_gear.put_pixel(wx, wy - 2, (255, 255, 255, 255)) # brilliant core
    c_gear.put_pixel(wx + 1, wy - 2, style.weapon_glow)
    c_gear.put_pixel(wx, wy - 1, style.weapon_hilt) # bracket

    composite = Image.alpha_composite(c_shadow.image, c_body.image)
    composite = Image.alpha_composite(composite, c_clothes.image)
    composite = Image.alpha_composite(composite, c_gear.image)
    return composite

def render_goblin_layers(w: int, h: int, style: TestStyle, action: str = "idle", step: int = 0, direction: str = "down"):
    scale = max(1, w // 16)
    mid_x = w // 2
    c_shadow = PixelCanvas(w, h)
    c_body = PixelCanvas(w, h)
    c_clothes = PixelCanvas(w, h)
    c_gear = PixelCanvas(w, h)

    bob_y = 1 if (action == "idle" and step % 2 == 1) else (1 if (action == "walk" and step % 2 == 0) else 0)
    c_shadow.draw.ellipse([mid_x - 4*scale, 14*scale, mid_x + 3*scale, 15*scale], fill=style.outline)

    # Goblin has hunched posture (1px lower)
    head_y = (4 + bob_y) * scale
    torso_y = head_y + 3 * scale
    legs_y = torso_y + 4 * scale

    # 1. Body: Green Skin, Lateral Pointed Ears, Beady Eyes
    # Pointed Ears extending out!
    c_body.put_pixel(mid_x - 5, head_y + 1, style.skin)
    c_body.put_pixel(mid_x - 4, head_y + 2, style.skin_shadow)
    c_body.put_pixel(mid_x + 4, head_y + 1, style.skin)
    c_body.put_pixel(mid_x + 3, head_y + 2, style.skin_shadow)

    # Goblin Skull
    for y in range(head_y, head_y + 3):
        for x in range(mid_x - 3, mid_x + 3):
            c_body.put_pixel(x, y, style.skin)
    # Tapered chin
    c_body.put_pixel(mid_x - 1, head_y + 3, style.skin_shadow)
    c_body.put_pixel(mid_x, head_y + 3, style.skin_shadow)

    # Beady amber eyes
    c_body.put_pixel(mid_x - 2, head_y + 1, style.accent)
    c_body.put_pixel(mid_x + 1, head_y + 1, style.accent)

    # Skinny arms
    c_body.put_pixel(mid_x - 4, torso_y + 2, style.skin)
    c_body.put_pixel(mid_x - 4, torso_y + 3, style.skin)
    c_body.put_pixel(mid_x + 3, torso_y + 2, style.skin)
    c_body.put_pixel(mid_x + 3, torso_y + 3, style.skin)

    # 2. Clothes: Ragged Tunic & Bandolier
    for y in range(torso_y, torso_y + 3):
        for x in range(mid_x - 3, mid_x + 3):
            c_clothes.put_pixel(x, y, style.shirt)
    # Diagonal Bandolier
    c_clothes.put_pixel(mid_x - 2, torso_y, style.belt)
    c_clothes.put_pixel(mid_x - 1, torso_y + 1, style.belt)
    c_clothes.put_pixel(mid_x, torso_y + 2, style.belt)
    # Jagged hemline
    c_clothes.put_pixel(mid_x - 3, torso_y + 3, style.shirt_shadow)
    c_clothes.put_pixel(mid_x - 1, torso_y + 3, style.shirt_shadow)
    c_clothes.put_pixel(mid_x + 1, torso_y + 3, style.shirt_shadow)

    # Crouching legs
    c_clothes.draw_rect(mid_x - 3, legs_y, 2, 3, fill=style.pants, outline=style.pants_shadow)
    c_clothes.draw_rect(mid_x + 1, legs_y, 2, 3, fill=style.pants, outline=style.pants_shadow)

    # 3. Gear: Curved Serrated Dagger
    wx = mid_x + 4
    wy = torso_y + 2
    c_gear.put_pixel(wx, wy - 2, style.weapon)
    c_gear.put_pixel(wx - 1, wy - 1, style.weapon)
    c_gear.put_pixel(wx, wy, style.weapon_hilt)
    c_gear.put_pixel(wx + 1, wy, style.weapon_hilt)

    composite = Image.alpha_composite(c_shadow.image, c_body.image)
    composite = Image.alpha_composite(composite, c_clothes.image)
    composite = Image.alpha_composite(composite, c_gear.image)
    return composite

def ascii_render(img: Image.Image, name: str):
    print(f"\n==================== {name} (16x16) ====================")
    for y in range(img.height):
        row = ""
        for x in range(img.width):
            r, g, b, a = img.getpixel((x, y))
            if a == 0:
                row += "  "
            else:
                lum = (r * 299 + g * 587 + b * 114) // 1000
                if lum < 50:
                    row += "##"
                elif lum < 120:
                    row += "=="
                elif lum < 190:
                    row += "++"
                else:
                    row += ".."
        print(row)

knight_style = TestStyle(
    skin="#d2aa99", skin_shadow="#854c30",
    hair="#442434", shirt="#8595a1", shirt_shadow="#4e4a4e",
    pants="#4e4a4e", pants_shadow="#140c1c",
    outline="#140c1c", eyes="#140c1c",
    weapon="#deeed6", weapon_hilt="#d27d2c", accent="#d04648"
)
k_img = render_knight_layers(16, 16, knight_style)
ascii_render(k_img, "Knight")

mage_style = TestStyle(
    skin="#d2aa99", skin_shadow="#854c30",
    hair="#442434", shirt="#30346d", shirt_shadow="#140c1c",
    pants="#140c1c", pants_shadow="#140c1c",
    outline="#140c1c", eyes="#6dc2ca",
    weapon="#854c30", weapon_hilt="#854c30", weapon_glow="#6dc2ca", accent="#dad45e"
)
m_img = render_mage_layers(16, 16, mage_style)
ascii_render(m_img, "Mage")

goblin_style = TestStyle(
    skin="#6daa2c", skin_shadow="#346524",
    hair="#346524", shirt="#854c30", shirt_shadow="#442434",
    pants="#30346d", pants_shadow="#140c1c",
    outline="#140c1c", eyes="#dad45e",
    weapon="#8595a1", weapon_hilt="#4e4a4e", accent="#dad45e"
)
g_img = render_goblin_layers(16, 16, goblin_style)
ascii_render(g_img, "Goblin")
