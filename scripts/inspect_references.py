"""
Inspection and analysis script for external Pixel Art reference library.
Scans E:\\course\\03_Programming_Data\\game_dev\\assets, discovers character and enemy sprites,
analyzes image dimensions, color ramps, head-to-body proportions, outline techniques, and pixel clustering.
"""

import os
from pathlib import Path
from PIL import Image

def analyze_image(path: Path):
    try:
        with Image.open(path) as img:
            w, h = img.size
            mode = img.mode
            rgba = img.convert("RGBA")
            colors = set()
            opaque_coords = []
            alpha_values = set()
            for y in range(h):
                for x in range(w):
                    r, g, b, a = rgba.getpixel((x, y))
                    alpha_values.add(a)
                    if a > 0:
                        colors.add((r, g, b, a))
                        opaque_coords.append((x, y))
            
            if not opaque_coords:
                return None

            min_x = min(x for x, y in opaque_coords)
            max_x = max(x for x, y in opaque_coords)
            min_y = min(y for x, y in opaque_coords)
            max_y = max(y for x, y in opaque_coords)
            bound_w = max_x - min_x + 1
            bound_h = max_y - min_y + 1

            # Detect outline colors (dark boundary pixels)
            boundary_colors = set()
            for x, y in opaque_coords:
                # check if on edge of opaque area
                has_transparent_neighbor = False
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < w and 0 <= ny < h) or rgba.getpixel((nx, ny))[3] == 0:
                        has_transparent_neighbor = True
                        break
                if has_transparent_neighbor:
                    boundary_colors.add(rgba.getpixel((x, y)))

            return {
                "path": str(path),
                "width": w,
                "height": h,
                "mode": mode,
                "unique_colors_count": len(colors),
                "bounding_box": (min_x, min_y, bound_w, bound_h),
                "opaque_pixels": len(opaque_coords),
                "fill_density": round(len(opaque_coords) / (bound_w * bound_h), 2) if bound_w * bound_h > 0 else 0,
                "sample_boundary_hex": [f"#{r:02x}{g:02x}{b:02x}" for r, g, b, a in list(boundary_colors)[:4]],
            }
    except Exception as e:
        return {"path": str(path), "error": str(e)}


def scan_reference_library():
    ref_root = Path(r"E:\course\03_Programming_Data\game_dev\assets")
    if not ref_root.exists():
        print(f"Error: {ref_root} does not exist!")
        return

    print(f"Scanning reference library at: {ref_root} ...")
    
    # Priority targets
    targets = [
        # Sprout lands
        ref_root / "Sprout Lands - Sprites - Basic pack" / "Characters",
        # Tiny Swords Knights & Goblins
        ref_root / "Tiny Swords (Update 010)" / "Factions" / "Knights" / "Troops",
        ref_root / "Tiny Swords (Update 010)" / "Factions" / "Goblins" / "Troops",
        # Cute fantasy
        ref_root / "Cute_Fantasy_Free" / "Player",
        ref_root / "Cute_Fantasy_Free" / "Enemies",
        # Farm RPG
        ref_root / "Farm RPG FREE 16x16 - Tiny Asset Pack" / "Character",
        # Female Adventurer
        ref_root / "The Female Adventurer - Free",
        # Adventurer
        ref_root / "FREE_Adventurer 2D Pixel Art" / "Sprites",
    ]

    found_samples = []

    for t in targets:
        if not t.exists():
            continue
        print(f"\nChecking directory: {t.name}")
        for root, dirs, files in os.walk(t):
            for f in files:
                if f.lower().endswith((".png", ".ase", ".aseprite")):
                    full_p = Path(root) / f
                    # filter out macosx hidden files
                    if "__MACOSX" in str(full_p):
                        continue
                    if full_p.suffix.lower() == ".png":
                        res = analyze_image(full_p)
                        if res and "error" not in res:
                            found_samples.append(res)
                            if len(found_samples) % 5 == 0:
                                print(f"  Analyzed {len(found_samples)} sprites... (latest: {full_p.name} [{res['width']}x{res['height']}])")

    print(f"\nTotal character sprites analyzed: {len(found_samples)}")
    return found_samples


if __name__ == "__main__":
    samples = scan_reference_library()
    # Print 15 most interesting diverse samples
    print("\nSample Detailed Analysis:")
    for s in samples[:15]:
        print(f"\nFile: {Path(s['path']).name}")
        print(f"  Parent: {Path(s['path']).parent.name}")
        print(f"  Dimensions: {s['width']}x{s['height']} | Bounding Box: {s['bounding_box']}")
        print(f"  Colors: {s['unique_colors_count']} | Fill Density: {s['fill_density']}")
        print(f"  Sample Boundary Outlines: {s.get('sample_boundary_hex')}")
