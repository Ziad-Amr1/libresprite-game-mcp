"""
Deep visual and structural inspection of key pixel art character references.
Inspects pixel layouts, color ramps, head-to-body ratios, eyes, hair, silhouettes, and outlines.
"""

from pathlib import Path
from PIL import Image
import json

try:
    from libresprite_game_mcp.core.aseprite_file import AsepriteProject
except ImportError:
    AsepriteProject = None


def print_ascii_art(img: Image.Image, max_w=32, max_h=32):
    """Renders small pixel art directly to ASCII terminal for visual inspection."""
    img = img.convert("RGBA")
    w, h = img.size
    print(f"--- ASCII Render ({w}x{h}) ---")
    for y in range(min(h, max_h)):
        line = ""
        for x in range(min(w, max_w)):
            r, g, b, a = img.getpixel((x, y))
            if a == 0:
                line += "  "
            else:
                lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
                if lum < 0.2:
                    line += "##"
                elif lum < 0.5:
                    line += "=="
                elif lum < 0.8:
                    line += "++"
                else:
                    line += ".."
        print(line)
    print("----------------------------")


def inspect_key_references():
    ref_root = Path(r"E:\course\03_Programming_Data\game_dev\assets")

    targets = [
        ("Farm RPG 16x16 Idle", ref_root / "Farm RPG FREE 16x16 - Tiny Asset Pack" / "Character" / "Idle.png", 16, 16),
        ("Cute Fantasy Player", ref_root / "Cute_Fantasy_Free" / "Player" / "Player.png", 32, 32),
        ("Cute Fantasy Skeleton", ref_root / "Cute_Fantasy_Free" / "Enemies" / "Skeleton.png", 32, 32),
        ("Sprout Lands Character", ref_root / "Sprout Lands - Sprites - Basic pack" / "Characters" / "Basic Charakter Spritesheet.png", 48, 48),
        ("Sunnyside Human", ref_root / "sunnyside_world_chatacter_anim_human_v1.0.aseprite", None, None),
    ]

    for title, path, frame_w, frame_h in targets:
        print(f"\n=======================================================")
        print(f"REFERENCE: {title}")
        print(f"Path: {path}")
        print(f"=======================================================")
        if not path.exists():
            print("File does not exist!")
            continue

        if path.suffix.lower() in (".ase", ".aseprite") and AsepriteProject:
            proj = AsepriteProject.load(path)
            print(f"Aseprite Project: {proj.width}x{proj.height}, Frames: {len(proj.sprite.frames)}")
            print(f"Layers: {list(proj.layers.keys())}")
            print(f"Tags: {proj.tags}")
            first_frame = proj.get_frame_image(0)
            print_ascii_art(first_frame)
            continue

        with Image.open(path) as full_img:
            w, h = full_img.size
            print(f"Full Image Size: {w}x{h}")
            fw = frame_w or w
            fh = frame_h or h
            
            # Slice first frame (top-left)
            first_frame = full_img.crop((0, 0, min(fw, w), min(fh, h)))
            
            # Count colors & analyze bounding box
            rgba = first_frame.convert("RGBA")
            opaque_coords = []
            colors = set()
            for y in range(first_frame.height):
                for x in range(first_frame.width):
                    c = rgba.getpixel((x, y))
                    if c[3] > 0:
                        colors.add(c)
                        opaque_coords.append((x, y))
            
            if opaque_coords:
                min_x = min(x for x, y in opaque_coords)
                max_x = max(x for x, y in opaque_coords)
                min_y = min(y for x, y in opaque_coords)
                max_y = max(y for x, y in opaque_coords)
                print(f"First Frame Active Region: X:[{min_x}..{max_x}] ({max_x-min_x+1}px), Y:[{min_y}..{max_y}] ({max_y-min_y+1}px)")
                print(f"Unique Colors in Frame: {len(colors)}")
                print(f"Color Hex List: {[f'#{r:02x}{g:02x}{b:02x}' for r, g, b, a in sorted(list(colors), key=lambda c: (c[0]+c[1]+c[2]))]}")

                # Height distribution (head vs body vs legs)
                ys = [y for x, y in opaque_coords]
                total_h = max_y - min_y + 1
                head_end_y = min_y + int(total_h * 0.45)
                torso_end_y = min_y + int(total_h * 0.75)
                head_px = sum(1 for y in ys if y <= head_end_y)
                torso_px = sum(1 for y in ys if head_end_y < y <= torso_end_y)
                legs_px = sum(1 for y in ys if y > torso_end_y)
                print(f"Vertical Pixel Distribution: Head={head_px}px ({round(head_px/len(ys)*100)}%), Torso={torso_px}px ({round(torso_px/len(ys)*100)}%), Legs/Feet={legs_px}px ({round(legs_px/len(ys)*100)}%)")

            print_ascii_art(first_frame)


if __name__ == "__main__":
    inspect_key_references()
