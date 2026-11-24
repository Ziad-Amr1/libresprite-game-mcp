"""
Comprehensive verification test suite for LibreSprite Game MCP.
"""

from pathlib import Path
import json

from libresprite_game_mcp.server import (
    get_libresprite_status,
    list_game_palettes,
    create_character_sprite,
    create_autotile_tileset,
    create_game_item,
    export_asset_sprite_sheet,
)


def run_tests():
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)

    print("=== 1. Checking LibreSprite Status ===")
    status = get_libresprite_status()
    print("Status:", json.dumps(status, indent=2))
    assert status["is_installed"], "LibreSprite should be detected as installed!"

    print("\n=== 2. Listing Game Palettes ===")
    palettes = list_game_palettes()
    print("Available palettes:", list(palettes["available_palettes"].keys()))
    assert "pico-8" in palettes["available_palettes"]
    assert "db16" in palettes["available_palettes"]

    print("\n=== 3. Generating Animated Character (Knight) ===")
    char_res = create_character_sprite(
        name="knight",
        width=16,
        height=16,
        shirt_color="#5b6ee1",
        pants_color="#222034",
        skin_color="#d2aa99",
        export_sheet=True,
        export_gif=True,
        export_godot=True,
        output_dir=str(test_dir),
    )
    print("Character result:", json.dumps(char_res, indent=2))
    assert Path(char_res["aseprite_project"]).exists()
    assert Path(char_res["sheet_png"]).exists()
    assert Path(char_res["preview_gif"]).exists()
    assert Path(char_res["godot_spriteframes"]).exists()

    print("\n=== 4. Generating Autotile 3x3 Tileset (Grass & Dungeon) ===")
    tile_res = create_autotile_tileset(
        name="dungeon_walls",
        tile_size=16,
        theme="stone_dungeon",
        output_dir=str(test_dir),
    )
    print("Tileset result:", json.dumps(tile_res, indent=2))
    assert Path(tile_res["sheet_png"]).exists()
    assert Path(tile_res["metadata_json"]).exists()

    print("\n=== 5. Generating Game Items & Animated Props ===")
    sword = create_game_item("sword", "iron_blade", size=16, output_dir=str(test_dir))
    potion = create_game_item("potion", "mana_flask", size=16, potion_variant="mana", output_dir=str(test_dir))
    torch = create_game_item("torch", "dungeon_torch", size=16, export_gif=True, output_dir=str(test_dir))
    coin = create_game_item("coin", "gold_coin", size=16, export_gif=True, output_dir=str(test_dir))

    print("Sword:", sword)
    print("Potion:", potion)
    print("Torch:", torch)
    print("Coin:", coin)

    assert Path(sword["image_png"]).exists()
    assert Path(potion["image_png"]).exists()
    assert Path(torch["aseprite_project"]).exists()
    assert Path(torch["preview_gif"]).exists()
    assert Path(coin["aseprite_project"]).exists()
    assert Path(coin["preview_gif"]).exists()

    print("\n=== 6. Packing Torch Animation into Packed Texture Atlas ===")
    pack_res = export_asset_sprite_sheet(
        input_aseprite_file=torch["aseprite_project"],
        sheet_type="packed",
        border_padding=2,
        shape_padding=2,
    )
    print("Pack result:", pack_res)
    assert Path(pack_res["sheet_path"]).exists()

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    run_tests()
