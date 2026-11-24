"""
Generates the experimental character batch in game_assets/experimental/
Exercises the redesigned character generator across distinct archetypes:
1. exp_knight: Armored knight with bascinet helmet, plume, broad pauldrons, gleam broadsword.
2. exp_mage: Arcane mage with pointed cowl hood, flowing flared robes, crystal staff.
3. exp_goblin: Goblin rogue with lateral pointed ears, hunched posture, curved dagger.
4. exp_heavy_brute: Dwarf brute with broad 8px chest, bushy beard, heavy battleaxe.
Validates each asset through AssetValidator (Art QA).
"""

from pathlib import Path
import json
from PIL import Image

from libresprite_game_mcp.models.schemas import (
    ArtProfile,
    CharacterBlueprint,
    CharacterAnimationSpec,
)
from libresprite_game_mcp.server import create_character_from_blueprint, validate_game_asset
from libresprite_game_mcp.core.aseprite_file import AsepriteProject

def generate_experimental_batch():
    output_dir = Path("game_assets/experimental")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating experimental character batch into: {output_dir.resolve()}")

    profile = ArtProfile(
        project_name="ExperimentalCharacters",
        native_resolution=(320, 180),
        palette_name="db16",
    )

    blueprints = [
        CharacterBlueprint(
            character_id="exp_knight",
            name="Armored Knight",
            size=(16, 16),
            proportion="chibi_1_2",
            archetype="knight",
            colors={
                "skin": "#d2aa99",
                "skin_shadow": "#854c30",
                "hair": "#442434",
                "shirt": "#8595a1", # steel armor
                "shirt_shadow": "#4e4a4e",
                "shirt_highlight": "#deeed6",
                "pants": "#4e4a4e",
                "pants_shadow": "#140c1c",
                "outline": "#140c1c",
                "eyes": "#140c1c",
                "weapon": "#8595a1",
                "weapon_hilt": "#d27d2c",
                "accent": "#d04648", # crimson plume
                "belt": "#854c30",
                "buckle": "#dad45e",
            },
            animations={
                "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
                "walk": CharacterAnimationSpec(frames=4, duration_ms=120, loop=True),
                "attack": CharacterAnimationSpec(frames=3, duration_ms=100, loop=False),
                "hurt": CharacterAnimationSpec(frames=2, duration_ms=150, loop=False),
            },
            pivot=(0.5, 0.9),
        ),
        CharacterBlueprint(
            character_id="exp_mage",
            name="Arcane Mage",
            size=(16, 16),
            proportion="chibi_1_2",
            archetype="mage",
            colors={
                "skin": "#d2aa99",
                "skin_shadow": "#854c30",
                "hair": "#442434",
                "shirt": "#30346d", # deep arcane robe
                "shirt_shadow": "#140c1c",
                "shirt_highlight": "#6dc2ca",
                "pants": "#140c1c",
                "pants_shadow": "#140c1c",
                "outline": "#140c1c",
                "eyes": "#6dc2ca", # glowing cyan eyes
                "weapon": "#854c30",
                "weapon_hilt": "#854c30",
                "weapon_glow": "#6dc2ca", # glowing staff crystal
                "accent": "#dad45e", # golden mystic sash
            },
            animations={
                "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
                "walk": CharacterAnimationSpec(frames=4, duration_ms=120, loop=True),
                "attack": CharacterAnimationSpec(frames=3, duration_ms=100, loop=False),
                "hurt": CharacterAnimationSpec(frames=2, duration_ms=150, loop=False),
            },
            pivot=(0.5, 0.9),
        ),
        CharacterBlueprint(
            character_id="exp_goblin",
            name="Goblin Rogue",
            size=(16, 16),
            proportion="chibi_1_2",
            archetype="goblin",
            colors={
                "skin": "#6daa2c", # green skin
                "skin_shadow": "#346524",
                "hair": "#346524",
                "shirt": "#854c30", # leather tunic
                "shirt_shadow": "#442434",
                "pants": "#4e4a4e",
                "pants_shadow": "#140c1c",
                "outline": "#140c1c",
                "eyes": "#dad45e", # amber eyes
                "weapon": "#8595a1",
                "weapon_hilt": "#4e4a4e",
                "belt": "#140c1c",
                "buckle": "#dad45e",
            },
            animations={
                "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
                "walk": CharacterAnimationSpec(frames=4, duration_ms=120, loop=True),
                "attack": CharacterAnimationSpec(frames=3, duration_ms=100, loop=False),
                "hurt": CharacterAnimationSpec(frames=2, duration_ms=150, loop=False),
            },
            pivot=(0.5, 0.9),
        ),
        CharacterBlueprint(
            character_id="exp_heavy_brute",
            name="Dwarf Brute",
            size=(16, 16),
            proportion="heroic_1_3",
            archetype="heavy_brute",
            colors={
                "skin": "#d2aa99",
                "skin_shadow": "#854c30",
                "hair": "#d27d2c", # thick orange-red beard
                "shirt": "#757161", # iron-studded leather
                "shirt_shadow": "#4e4a4e",
                "pants": "#30346d",
                "pants_shadow": "#140c1c",
                "outline": "#140c1c",
                "eyes": "#140c1c",
                "weapon": "#8595a1", # heavy battleaxe
                "weapon_hilt": "#854c30",
                "belt": "#140c1c",
                "buckle": "#dad45e",
            },
            animations={
                "idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True),
                "walk": CharacterAnimationSpec(frames=4, duration_ms=120, loop=True),
                "attack": CharacterAnimationSpec(frames=3, duration_ms=100, loop=False),
                "hurt": CharacterAnimationSpec(frames=2, duration_ms=150, loop=False),
            },
            pivot=(0.5, 0.9),
        ),
    ]

    results = {}

    for bp in blueprints:
        print(f"\n--- Generating {bp.name} ({bp.character_id}) ---")
        export_res = create_character_from_blueprint(
            blueprint=bp.model_dump(),
            profile=profile.model_dump(),
            export_sheet=True,
            export_gif=True,
            export_godot=True,
            output_dir=str(output_dir),
        )

        # Generate a high-contrast 16x16 preview PNG from first frame of Aseprite project
        ase_path = Path(export_res["aseprite_project"])
        proj = AsepriteProject.load(str(ase_path))
        first_frame_img = proj.get_frame_image(0)
        preview_png = output_dir / f"{bp.character_id}_preview.png"
        first_frame_img.save(preview_png)
        export_res["preview_png"] = str(preview_png)

        # Validate with Art QA
        qa_report = validate_game_asset(
            str(ase_path),
            palette_name="db16",
            expected_width=16,
            expected_height=16,
        )
        print(f"  Art QA Passed: {qa_report['passed']}")
        if not qa_report["passed"]:
            print(f"  Critical Errors: {qa_report['critical_errors']}")
        assert qa_report["passed"], f"Asset {bp.character_id} failed Art QA: {qa_report['critical_errors']}"

        results[bp.character_id] = {
            "name": bp.name,
            "export": export_res,
            "qa": qa_report,
        }

    summary_file = output_dir / "experimental_batch_manifest.json"
    summary_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nExperimental batch generated and verified successfully. Manifest saved to {summary_file}")

if __name__ == "__main__":
    generate_experimental_batch()
