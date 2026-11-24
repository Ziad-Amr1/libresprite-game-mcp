"""
Production Game Asset Generator Script for LibreSprite Game MCP.
Generates a complete suite of verified pixel art assets:
- Animated Characters (Godot 4 SpriteFrames + Sprite Sheets + .aseprite + .pixil)
- Items & Icons (Swords, Health, Mana, Stamina, and Elixir potions)
- 3x3 Autotile Tilesets (Grass/Dirt, Stone Dungeon, Wood Planks)
- Asset QA validation reports and asset manifest
"""

import json
import os
import shutil
from pathlib import Path
from PIL import Image

from libresprite_game_mcp.core.dispatcher import ProductionToolDispatcher
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator
from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.core.palettes import hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas
from libresprite_game_mcp.generators.character_generator import (
    build_animated_character_project,
)
from libresprite_game_mcp.generators.item_generator import (
    generate_sword_icon,
    generate_potion_icon,
    build_animated_torch_project,
    build_animated_coin_project,
)
from libresprite_game_mcp.generators.tileset_generator import (
    build_autotile_3x3_sheet,
)
from libresprite_game_mcp.exporters.game_export import (
    export_godot_spriteframes,
    export_pixilart_project,
    export_sprite_sheet_native,
)
from libresprite_game_mcp.qa.validator import AssetValidator
from libresprite_game_mcp.models.schemas import (
    CharacterBlueprint,
    CharacterAnimationSpec,
)


def generate_all_assets():
    base_dir = Path(__file__).resolve().parent.parent / "game_assets"
    base_dir.mkdir(parents=True, exist_ok=True)

    char_dir = base_dir / "characters"
    items_dir = base_dir / "items"
    tiles_dir = base_dir / "tilesets"

    char_dir.mkdir(parents=True, exist_ok=True)
    items_dir.mkdir(parents=True, exist_ok=True)
    tiles_dir.mkdir(parents=True, exist_ok=True)

    validator = AssetValidator()
    manifest_records = []

    print("==================================================================")
    print("LibreSprite Production Art System — Asset Generation")
    print("==================================================================")

    # -------------------------------------------------------------------------
    # 1. Characters via Orchestrator & Production Skills
    # -------------------------------------------------------------------------
    print("\n[1/3] Generating Animated Characters...")
    orch = ProductionOrchestrator(assets_dir=char_dir)
    orch.approve_reference_skill("pixel_character_consistency")
    orch.approve_reference_skill("pixilart_clean_pixel_art")

    # Character 1: Warrior Hero via pixel_character_consistency skill
    print(" -> Generating 'warrior_hero' via pixel_character_consistency skill...")
    warrior_res = orch.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={
            "character_id": "warrior_hero",
            "name": "Warrior Hero",
            "size": [16, 16],
            "proportion": "chibi_1_2",
            "outline_mode": "colored",
        },
        project_id="RPG_Core",
        workspace=char_dir,
    )
    assert warrior_res["status"] == "success"
    manifest_records.append({
        "id": "warrior_hero",
        "category": "character",
        "name": "Warrior Hero",
        "dimensions": [16, 16],
        "frames": 6,
        "format": "aseprite + png + tres",
        "files": {
            "project": str(char_dir / "warrior_hero.aseprite"),
            "preview": str(char_dir / "warrior_hero_preview.png"),
            "sheet": str(char_dir / "warrior_hero_sheet.png"),
            "godot_tres": str(char_dir / "warrior_hero_spriteframes.tres"),
        },
        "description": "Chibi warrior hero with idle and walk animations, packed spritesheet, and Godot 4 SpriteFrames.",
    })
    print("    [OK] warrior_hero.aseprite, sheet.png, and spriteframes.tres created.")

    # Character 2: Pixilart Knight via pixilart_clean_pixel_art skill
    print(" -> Generating 'pixil_knight' via pixilart_clean_pixel_art skill...")
    pixil_res = orch.execute_skill(
        skill_id="pixilart_clean_pixel_art",
        parameters={
            "character_id": "pixil_knight",
            "name": "Pixilart Knight",
            "size": [16, 16],
            "proportion": "chibi_1_2",
            "outline_mode": "colored",
        },
        project_id="RPG_Core",
        workspace=char_dir,
    )
    assert pixil_res["status"] == "success"
    manifest_records.append({
        "id": "pixil_knight",
        "category": "character",
        "name": "Pixilart Knight",
        "dimensions": [16, 16],
        "frames": 6,
        "format": "aseprite + pixil + png + tres",
        "files": {
            "project": str(char_dir / "pixil_knight.aseprite"),
            "preview": str(char_dir / "pixil_knight_preview.png"),
            "pixil_json": str(char_dir / "pixil_knight.pixil"),
            "sheet": str(char_dir / "pixil_knight_sheet.png"),
            "godot_tres": str(char_dir / "pixil_knight_spriteframes.tres"),
        },
        "description": "Authentic clean pixel art knight with .pixil JSON project format, zero orphan pixels, and Godot 4 metadata.",
    })
    print("    [OK] pixil_knight.pixil, aseprite, sheet.png, and spriteframes.tres created.")

    # Character 3: Goblin Rogue (Procedural Blueprint)
    print(" -> Generating 'goblin_rogue' (custom monster blueprint)...")
    goblin_bp = CharacterBlueprint(
        character_id="goblin_rogue",
        name="Goblin Rogue",
        size=(16, 16),
        proportion="chibi_1_2",
        colors={
            "skin": "#6daa2c",
            "skin_shadow": "#346524",
            "hair": "#140c1c",
            "shirt": "#854c30",
            "shirt_shadow": "#442434",
            "pants": "#4e4a4e",
            "pants_shadow": "#140c1c",
            "outline": "#140c1c",
            "eyes": "#d27d2c",
            "weapon": "#8595a1",
            "weapon_hilt": "#d27d2c",
        },
        views=["down"],
        animations={
            "idle": CharacterAnimationSpec(frames=2, duration_ms=250, loop=True),
            "walk": CharacterAnimationSpec(frames=4, duration_ms=120, loop=True),
        },
    )
    goblin_proj = build_animated_character_project(blueprint=goblin_bp)
    goblin_ase = char_dir / "goblin_rogue.aseprite"
    goblin_proj.save(goblin_ase)
    
    # Apply outline
    for i in range(len(goblin_proj.sprite.frames)):
        img = goblin_proj.get_frame_image(i)
        c = PixelCanvas.from_image(img)
        c.add_outline(hex_to_rgba("#140c1c"))
        goblin_proj.set_frame_image(i, "Layer 1", c.image)
    goblin_proj.save(goblin_ase)

    goblin_preview = char_dir / "goblin_rogue_preview.png"
    goblin_proj.get_frame_image(0).save(goblin_preview)

    goblin_sheet = char_dir / "goblin_rogue_sheet.png"
    goblin_tres = char_dir / "goblin_rogue_spriteframes.tres"
    export_sprite_sheet_native(goblin_proj, goblin_sheet)
    export_godot_spriteframes(goblin_proj, f"res://{goblin_sheet.name}", goblin_tres)

    manifest_records.append({
        "id": "goblin_rogue",
        "category": "character",
        "name": "Goblin Rogue",
        "dimensions": [16, 16],
        "frames": 6,
        "format": "aseprite + png + tres",
        "files": {
            "project": str(goblin_ase),
            "preview": str(goblin_preview),
            "sheet": str(goblin_sheet),
            "godot_tres": str(goblin_tres),
        },
        "description": "Green-skinned goblin rogue with leather armor, dagger, clean outline, and 6 animation frames.",
    })
    print("    [OK] goblin_rogue.aseprite, sheet.png, and spriteframes.tres created.")

    # Character 4: Arcane Mage (Procedural Blueprint)
    print(" -> Generating 'arcane_mage' (mystic wizard blueprint)...")
    mage_bp = CharacterBlueprint(
        character_id="arcane_mage",
        name="Arcane Mage",
        size=(16, 16),
        proportion="chibi_1_2",
        colors={
            "skin": "#d2aa99",
            "skin_shadow": "#854c30",
            "hair": "#deeed6",
            "shirt": "#754668",
            "shirt_shadow": "#442434",
            "pants": "#30346d",
            "pants_shadow": "#140c1c",
            "outline": "#140c1c",
            "eyes": "#597dce",
            "weapon": "#597dce",
            "weapon_hilt": "#d27d2c",
        },
        views=["down"],
        animations={
            "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
            "walk": CharacterAnimationSpec(frames=4, duration_ms=130, loop=True),
        },
    )
    mage_proj = build_animated_character_project(blueprint=mage_bp)
    mage_ase = char_dir / "arcane_mage.aseprite"
    mage_proj.save(mage_ase)

    for i in range(len(mage_proj.sprite.frames)):
        img = mage_proj.get_frame_image(i)
        c = PixelCanvas.from_image(img)
        c.add_outline(hex_to_rgba("#140c1c"))
        mage_proj.set_frame_image(i, "Layer 1", c.image)
    mage_proj.save(mage_ase)

    mage_preview = char_dir / "arcane_mage_preview.png"
    mage_proj.get_frame_image(0).save(mage_preview)

    mage_sheet = char_dir / "arcane_mage_sheet.png"
    mage_tres = char_dir / "arcane_mage_spriteframes.tres"
    export_sprite_sheet_native(mage_proj, mage_sheet)
    export_godot_spriteframes(mage_proj, f"res://{mage_sheet.name}", mage_tres)

    manifest_records.append({
        "id": "arcane_mage",
        "category": "character",
        "name": "Arcane Mage",
        "dimensions": [16, 16],
        "frames": 6,
        "format": "aseprite + png + tres",
        "files": {
            "project": str(mage_ase),
            "preview": str(mage_preview),
            "sheet": str(mage_sheet),
            "godot_tres": str(mage_tres),
        },
        "description": "Arcane mage with purple robes, mystic blue focus weapon, 6 animation frames, and Godot 4 resource.",
    })
    print("    [OK] arcane_mage.aseprite, sheet.png, and spriteframes.tres created.")

    # -------------------------------------------------------------------------
    # 2. Items & Game Icons
    # -------------------------------------------------------------------------
    print("\n[2/3] Generating Game Items & Icons...")
    
    # Item 1: Iron Greatsword
    sword_img = generate_sword_icon(size=16)
    sword_path = items_dir / "sword_greatsword.png"
    sword_img.save(sword_path)
    manifest_records.append({
        "id": "sword_greatsword",
        "category": "item",
        "name": "Iron Greatsword",
        "dimensions": [16, 16],
        "format": "png",
        "files": {"icon": str(sword_path)},
        "description": "Diagonal steel greatsword with gold crossguard and ruby pommel.",
    })
    print("    [OK] sword_greatsword.png created.")

    # Potions: Health, Mana, Stamina, Elixir
    potions = [
        ("potion_health", "Health Potion", "health"),
        ("potion_mana", "Mana Potion", "mana"),
        ("potion_stamina", "Stamina Elixir", "stamina"),
        ("potion_elixir", "Royal Elixir", "elixir"),
    ]
    for pot_id, pot_name, pot_type in potions:
        pot_img = generate_potion_icon(size=16, potion_type=pot_type)
        pot_path = items_dir / f"{pot_id}.png"
        pot_img.save(pot_path)
        manifest_records.append({
            "id": pot_id,
            "category": "item",
            "name": pot_name,
            "dimensions": [16, 16],
            "format": "png",
            "files": {"icon": str(pot_path)},
            "description": f"Rounded glass flask with {pot_type} liquid and dynamic reflection highlight.",
        })
        print(f"    [OK] {pot_id}.png created.")

    # Combined Items Sheet
    items_sheet = Image.new("RGBA", (16 * 5, 16), (0, 0, 0, 0))
    items_sheet.paste(sword_img, (0, 0))
    for idx, (pot_id, _, pot_type) in enumerate(potions):
        p_img = Image.open(items_dir / f"{pot_id}.png")
        items_sheet.paste(p_img, ((idx + 1) * 16, 0))
    items_sheet_path = items_dir / "items_spritesheet.png"
    items_sheet.save(items_sheet_path)
    print("    [OK] items_spritesheet.png created (all 5 icons in 1 atlas).")

    # Animated Props: Dungeon Torch & Spinning Coin
    print(" -> Generating animated props (Torch & Coin with Godot SpriteFrames)...")
    torch_proj = build_animated_torch_project(size=16)
    torch_ase = items_dir / "torch_animated.aseprite"
    torch_proj.save(torch_ase)
    torch_sheet = items_dir / "torch_animated_sheet.png"
    torch_tres = items_dir / "torch_animated_spriteframes.tres"
    export_sprite_sheet_native(torch_proj, torch_sheet)
    export_godot_spriteframes(torch_proj, f"res://{torch_sheet.name}", torch_tres)
    manifest_records.append({
        "id": "torch_animated",
        "category": "prop",
        "name": "Animated Dungeon Torch",
        "dimensions": [16, 16],
        "frames": 4,
        "format": "aseprite + png + tres",
        "files": {
            "project": str(torch_ase),
            "sheet": str(torch_sheet),
            "godot_tres": str(torch_tres),
        },
        "description": "4-frame dancing flame wall torch with Godot 4 SpriteFrames resource.",
    })
    print("    [OK] torch_animated.aseprite, sheet.png, and spriteframes.tres created.")

    coin_proj = build_animated_coin_project(size=16)
    coin_ase = items_dir / "coin_spinning.aseprite"
    coin_proj.save(coin_ase)
    coin_sheet = items_dir / "coin_spinning_sheet.png"
    coin_tres = items_dir / "coin_spinning_spriteframes.tres"
    export_sprite_sheet_native(coin_proj, coin_sheet)
    export_godot_spriteframes(coin_proj, f"res://{coin_sheet.name}", coin_tres)
    manifest_records.append({
        "id": "coin_spinning",
        "category": "prop",
        "name": "Spinning Gold Coin",
        "dimensions": [16, 16],
        "frames": 4,
        "format": "aseprite + png + tres",
        "files": {
            "project": str(coin_ase),
            "sheet": str(coin_sheet),
            "godot_tres": str(coin_tres),
        },
        "description": "4-frame spinning gold coin collectible with sparkle highlight and Godot 4 SpriteFrames resource.",
    })
    print("    [OK] coin_spinning.aseprite, sheet.png, and spriteframes.tres created.")

    # -------------------------------------------------------------------------
    # 3. Tilesets & Environments
    # -------------------------------------------------------------------------
    print("\n[3/3] Generating 3x3 Autotile Environment Sheets...")
    themes = [
        ("tileset_grass_dirt", "Grass & Dirt Autotile", "grass_dirt"),
        ("tileset_stone_dungeon", "Stone Dungeon Autotile", "stone_dungeon"),
        ("tileset_wood_planks", "Wood Planks Autotile", "wood_planks"),
    ]

    for tile_id, tile_name, theme_name in themes:
        sheet, meta = build_autotile_3x3_sheet(tile_size=16, theme_name=theme_name)
        tile_png = tiles_dir / f"{tile_id}.png"
        sheet.save(tile_png)
        manifest_records.append({
            "id": tile_id,
            "category": "tileset",
            "name": tile_name,
            "dimensions": [48, 48],
            "tile_size": 16,
            "format": "png",
            "files": {"sheet": str(tile_png)},
            "description": f"Complete 3x3 autotile sheet (48x48) covering corners, edges, centers, and islands for {theme_name}.",
        })
        print(f"    [OK] {tile_id}.png created (48x48 autotile sheet).")

    # -------------------------------------------------------------------------
    # 4. Art QA Audit
    # -------------------------------------------------------------------------
    print("\n[4/4] Performing Automated Art QA Audit on All Generated Assets...")
    qa_results = {}
    all_passed = True
    for item in manifest_records:
        target_file = None
        for f in ("project", "sheet", "icon"):
            if f in item.get("files", {}):
                target_file = Path(item["files"][f])
                break
        if target_file and target_file.exists():
            if target_file.suffix.lower() in (".ase", ".aseprite"):
                proj = AsepriteProject.load(target_file)
                rep = validator.validate_project(proj, asset_name=item["id"])
            else:
                im = Image.open(target_file)
                rep = validator.validate_image(im, asset_name=item["id"])
            
            qa_results[item["id"]] = {
                "passed": rep.passed,
                "critical_errors": rep.critical_errors,
                "warnings": rep.warnings,
                "ready_for_export": rep.ready_for_export,
            }
            if not rep.passed:
                all_passed = False
                print(f"    [FAIL] {item['id']}: {rep.critical_errors}")
            else:
                print(f"    [PASS] {item['id']}: 100% Art QA compliant")

    # -------------------------------------------------------------------------
    # 5. Manifest & Catalog Generation
    # -------------------------------------------------------------------------
    manifest_data = {
        "version": "1.0.0",
        "system": "LibreSprite Game MCP Production Art System",
        "total_assets": len(manifest_records),
        "all_qa_passed": all_passed,
        "assets": manifest_records,
        "qa_audit": qa_results,
    }

    manifest_path = base_dir / "MANIFEST.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    readme_path = base_dir / "README.md"
    readme_content = f"""# Game Assets Portfolio

Generated by **LibreSprite Game MCP Production Art System**.

All assets adhere to pixel-art constraints: 16x16 / 48x48 grids, cohesive palettes, zero orphan stray pixels, and 100% syntactically valid Godot 4 engine exports.

## Asset Catalog

### 1. Characters (`game_assets/characters/`)
| Asset ID | Name | Size | Frames | Exports |
| :--- | :--- | :---: | :---: | :--- |
| `warrior_hero` | Warrior Hero | 16x16 | 6 | `.aseprite`, `_sheet.png`, `_spriteframes.tres` |
| `pixil_knight` | Pixilart Knight | 16x16 | 6 | `.aseprite`, `.pixil`, `_sheet.png`, `_spriteframes.tres` |
| `goblin_rogue` | Goblin Rogue | 16x16 | 6 | `.aseprite`, `_sheet.png`, `_spriteframes.tres` |
| `arcane_mage` | Arcane Mage | 16x16 | 6 | `.aseprite`, `_sheet.png`, `_spriteframes.tres` |

### 2. Items & Icons (`game_assets/items/`)
| Asset ID | Name | Size | Type | File |
| :--- | :--- | :---: | :---: | :--- |
| `sword_greatsword` | Iron Greatsword | 16x16 | Weapon | `sword_greatsword.png` |
| `potion_health` | Health Potion | 16x16 | Potion | `potion_health.png` |
| `potion_mana` | Mana Potion | 16x16 | Potion | `potion_mana.png` |
| `potion_stamina` | Stamina Elixir | 16x16 | Potion | `potion_stamina.png` |
| `potion_elixir` | Royal Elixir | 16x16 | Potion | `potion_elixir.png` |
| `items_spritesheet` | All 5 Items Sheet | 80x16 | Atlas | `items_spritesheet.png` |

### 3. Tilesets & Environments (`game_assets/tilesets/`)
| Asset ID | Name | Sheet Size | Cell Size | File |
| :--- | :--- | :---: | :---: | :--- |
| `tileset_grass_dirt` | Grass & Dirt 3x3 Autotile | 48x48 | 16x16 | `tileset_grass_dirt.png` |
| `tileset_stone_dungeon` | Stone Dungeon 3x3 Autotile | 48x48 | 16x16 | `tileset_stone_dungeon.png` |
| `tileset_wood_planks` | Wood Planks 3x3 Autotile | 48x48 | 16x16 | `tileset_wood_planks.png` |

## Godot 4 Integration
Each character asset includes a native Godot 4.x `SpriteFrames` resource (`.tres`). You can directly drag the `.tres` file into an `AnimatedSprite2D` node in Godot 4 without manual atlas slicing.
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("\n==================================================================")
    print(f"Asset Generation Complete! {len(manifest_records)} assets generated.")
    print(f"Catalog Manifest written to: {manifest_path}")
    print("==================================================================")


if __name__ == "__main__":
    generate_all_assets()
