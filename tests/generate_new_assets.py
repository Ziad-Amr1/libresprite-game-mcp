"""
Generates new game assets using the hardened, blueprint-driven production pipeline.
Demonstrates:
1. Cyberpunk 24x24 Ninja character from CharacterBlueprint + ArtProfile.
2. Animated crystal torch and elixir of life.
3. Automated Art QA validation report generation.
"""

from pathlib import Path
import json

from libresprite_game_mcp.server import (
    create_character_from_blueprint,
    create_game_item,
    validate_game_asset,
)
from libresprite_game_mcp.models.schemas import (
    CharacterBlueprint,
    CharacterAnimationSpec,
    ArtProfile,
)


def generate_new_production_assets():
    out_dir = Path("test_output") / "new_assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== 1. Generating Cyberpunk Ninja (24x24 Blueprint) ===")
    ninja_bp = CharacterBlueprint(
        character_id="cyber_ninja",
        name="Cyber Ninja",
        size=(24, 24),
        proportion="chibi_1_2",
        colors={
            "skin": "#d1f7ff",   # Pale synthwave skin
            "skin_shadow": "#a6cfd5",
            "hair": "#0d0221",
            "shirt": "#05d9e8",  # Cyberpunk cyan
            "shirt_shadow": "#005678",
            "pants": "#0f084b",  # Dark navy
            "pants_shadow": "#01012b",
            "outline": "#0d0221",
            "eyes": "#ff2a6d",   # Neon pink cyber-visor
            "weapon": "#05ffa1", # Neon green plasma blade
            "weapon_hilt": "#ff2a6d",
        },
        views=["down"],
        animations={
            "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
            "run": CharacterAnimationSpec(frames=4, duration_ms=90, loop=True),
            "slash": CharacterAnimationSpec(frames=3, duration_ms=75, loop=False),
            "hurt": CharacterAnimationSpec(frames=2, duration_ms=140, loop=False),
        },
        pivot=(0.5, 0.9),
    )

    cyber_profile = ArtProfile(
        project_name="NeonInfiltration",
        palette_name="cyberpunk",
        native_resolution=(480, 270),
        character_base_size=(24, 24),
    )

    char_result = create_character_from_blueprint(
        blueprint=ninja_bp.model_dump(),
        profile=cyber_profile.model_dump(),
        export_sheet=True,
        export_gif=True,
        export_godot=True,
        output_dir=str(out_dir),
    )
    print("Character generated:", json.dumps(char_result, indent=2))

    print("\n=== 2. Generating Elixir of Life (24x24 Potion) ===")
    elixir = create_game_item(
        item_type="potion",
        name="elixir_of_life",
        size=24,
        potion_variant="elixir",
        output_dir=str(out_dir),
    )
    print("Elixir generated:", elixir)

    print("\n=== 3. Running Automated QA Validation on New Assets ===")
    ninja_qa = validate_game_asset(
        asset_path=char_result["aseprite_project"],
        palette_name="cyberpunk",
        expected_width=24,
        expected_height=24,
        anchor_pivot_x=0.5,
        anchor_pivot_y=0.9,
    )
    print("Cyber Ninja QA Report:")
    print("  Status:", "PASS" if ninja_qa["passed"] else "FAIL")
    print("  Critical Errors:", ninja_qa["critical_errors"])
    print("  Warnings:", ninja_qa["warnings"])
    print("  Checks:", json.dumps(ninja_qa["checks"], indent=2))

    return char_result, elixir, ninja_qa


if __name__ == "__main__":
    generate_new_production_assets()
